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

export function AccessCodesManager() {
  const [codes, setCodes] = useState([]);
  const [label, setLabel] = useState("");
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
    const days = Number(validityDays) || 14;
    const entry = createAccessCodeEntry({
      patientLabel: label,
      validityDays: days,
    });
    setLastCreated(entry);
    setCopied(false);
    refresh();
    setLabel("");
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
            Generates a one-time patient link code stored in{" "}
            <span className="font-mono">localStorage</span> for this browser
            only—replace with a secure API in production.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleGenerate} className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
            <div className="grid min-w-[200px] flex-1 gap-2">
              <label htmlFor="patient-label" className="text-sm font-medium">
                Patient label
              </label>
              <Input
                id="patient-label"
                placeholder="e.g. Initials or internal ID"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
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
            <Button type="submit" className="gap-1.5 sm:shrink-0">
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
                Patient opens{" "}
                <span className="text-foreground font-medium">
                  {typeof window !== "undefined" ? window.location.origin : ""}
                  {ROUTES.patientPortal}
                </span>{" "}
                and enters this code once. Each code works for a single
                redemption.
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
                    <th className="px-3 py-2">Label</th>
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
                        <td className="px-3 py-2">{c.patientLabel}</td>
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
