"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy, Plus, Ban } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  createAccessCodeEntry,
  readCodes,
  revokeAccessCode,
  writeCodes,
} from "@/lib/demo-access-storage";
import { DEMO_PATIENTS, getDemoPatient } from "@/lib/demo-patients";
import { ROUTES } from "@/lib/routes";

function formatExpiry(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function patientNameForCodeRow(c) {
  if (c.patientId) {
    return getDemoPatient(c.patientId)?.displayName ?? c.patientId;
  }
  if (c.patientLabel) return c.patientLabel;
  return "—";
}

export function AccessCodesManager() {
  const [codes, setCodes] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState(
    () => DEMO_PATIENTS[0]?.id ?? ""
  );
  const [validityDays, setValidityDays] = useState("14");
  const [lastCreated, setLastCreated] = useState(null);
  const [copied, setCopied] = useState(false);

  const refresh = useCallback(() => {
    setCodes(readCodes());
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleGenerate = (e) => {
    e.preventDefault();
    if (!selectedPatientId) return;
    const days = Number(validityDays) || 14;
    const entry = createAccessCodeEntry({
      patientId: selectedPatientId,
      validityDays: days,
    });
    setLastCreated(entry);
    setCopied(false);
    refresh();
  };

  const handleCopy = async (code) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const handleRevoke = (id) => {
    revokeAccessCode(id);
    refresh();
  };

  const handlePurgeDemo = () => {
    if (typeof window === "undefined") return;
    if (
      !window.confirm(
        "Remove all demo access codes from this browser? This cannot be undone."
      )
    ) {
      return;
    }
    writeCodes([]);
    refresh();
    setLastCreated(null);
  };

  return (
    <div className="flex flex-col gap-8">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create access code</CardTitle>
          <CardDescription>
            Each code is tied to one patient on the demo roster. Redeeming it
            opens only that person&apos;s portal. Stored in{" "}
            <span className="font-mono">localStorage</span> for this browser
            only—replace with a secure API in production.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleGenerate} className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
            <div className="grid min-w-[220px] flex-1 gap-2">
              <label htmlFor="access-code-patient" className="text-sm font-medium">
                Patient
              </label>
              <select
                id="access-code-patient"
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="border-input bg-background h-9 w-full rounded-lg border px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                required
              >
                {DEMO_PATIENTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.displayName}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid w-full gap-2 sm:w-40">
              <label htmlFor="valid-days" className="text-sm font-medium">
                Valid (days)
              </label>
              <Input
                id="valid-days"
                type="number"
                min={1}
                max={365}
                value={validityDays}
                onChange={(e) => setValidityDays(e.target.value)}
              />
            </div>
            <Button
              type="submit"
              className="gap-1.5 sm:shrink-0"
              disabled={!selectedPatientId}
            >
              <Plus className="size-4" />
              Generate code
            </Button>
          </form>

          {lastCreated && (
            <div className="bg-muted/50 space-y-2 rounded-lg border p-4">
              <p className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
                New code (share securely)
              </p>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <code className="font-mono text-lg font-semibold tracking-wider">
                  {lastCreated.code}
                </code>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => handleCopy(lastCreated.code)}
                >
                  <Copy className="size-3.5" />
                  {copied ? "Copied" : "Copy"}
                </Button>
              </div>
              <p className="text-muted-foreground text-xs">
                For{" "}
                <span className="text-foreground font-medium">
                  {getDemoPatient(lastCreated.patientId)?.displayName ??
                    lastCreated.patientId}
                </span>
                . They open{" "}
                <span className="text-foreground font-medium">
                  {typeof window !== "undefined" ? window.location.origin : ""}
                  {ROUTES.patientPortal}
                </span>{" "}
                and enter this code once. Each code works for a single redemption.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="text-base">Active &amp; past codes</CardTitle>
            <CardDescription>
              Revoke a code to block new sessions; existing browser sessions
              remain until sign-out (demo limitation).
            </CardDescription>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={handlePurgeDemo}>
            Clear all (demo)
          </Button>
        </CardHeader>
        <CardContent>
          {codes.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No codes yet. Generate one above.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-muted/50 border-b text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Code</th>
                    <th className="px-3 py-2">Patient</th>
                    <th className="px-3 py-2">Expires</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 w-28" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {codes.map((c) => {
                    // Status badge needs wall time; acceptable for interactive demo UI.
                    /* eslint-disable-next-line react-hooks/purity -- expiry vs "now" */
                    const expired = Date.now() >= new Date(c.expiresAt).getTime();
                    let status = "Active";
                    if (c.revoked) status = "Revoked";
                    else if (c.redeemedAt) status = "Redeemed";
                    else if (expired) status = "Expired";
                    return (
                      <tr key={c.id} className="hover:bg-muted/30">
                        <td className="px-3 py-2 font-mono text-xs">{c.code}</td>
                        <td className="px-3 py-2">
                          <span>{patientNameForCodeRow(c)}</span>
                          {!c.patientId && (
                            <span className="text-muted-foreground ml-1 text-xs">
                              (legacy—cannot redeem)
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground">
                          {formatExpiry(c.expiresAt)}
                        </td>
                        <td className="px-3 py-2">{status}</td>
                        <td className="px-3 py-2">
                          {!c.revoked && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive gap-1"
                              onClick={() => handleRevoke(c.id)}
                            >
                              <Ban className="size-3.5" />
                              Revoke
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
