"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  findCodeByString,
  isCodeRedeemable,
  markCodeRedeemed,
  writePatientSession,
} from "@/lib/demo-access-storage";
import { getDemoPatient } from "@/lib/demo-patients";
import { ROUTES } from "@/lib/routes";

export function RedeemAccessForm() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    if (!consent) {
      setError("Please confirm you understand how your data will be used.");
      return;
    }
    setPending(true);
    const entry = findCodeByString(code);
    if (!entry) {
      setError("That code was not found. Check with your care team or ask for a new code.");
      setPending(false);
      return;
    }
    if (!entry.patientId) {
      setError(
        "This code is outdated (not tied to a patient chart). Ask your clinician for a new code."
      );
      setPending(false);
      return;
    }
    if (!isCodeRedeemable(entry)) {
      setError("This code is no longer valid (used, expired, or revoked).");
      setPending(false);
      return;
    }
    markCodeRedeemed(entry.id);
    const roster = getDemoPatient(entry.patientId);
    writePatientSession({
      codeId: entry.id,
      patientId: entry.patientId,
      displayName: roster?.displayName ?? "Patient",
      redeemedAt: new Date().toISOString(),
    });
    router.push(ROUTES.patientDashboard);
    router.refresh();
    setPending(false);
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="text-base">Enter your access code</CardTitle>
        <CardDescription>
          Your clinician issued this code for your chart only. It works once per
          browser session in this demo—no access to other patients.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <label htmlFor="access-code" className="text-sm font-medium">
              Access code
            </label>
            <Input
              id="access-code"
              placeholder="SC-XXXX-XXXX"
              className="font-mono uppercase"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <label className="flex cursor-pointer gap-3 text-sm leading-snug">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="border-input text-primary mt-0.5 size-4 shrink-0 rounded"
            />
            <span className="text-muted-foreground">
              I understand that biosignal summaries from my wearable are{" "}
              <strong className="text-foreground">informational</strong> and
              meant to support conversations with my clinician—not a diagnosis
              or treatment instruction.
            </span>
          </label>
          {error && (
            <p className="text-destructive text-sm" role="alert">
              {error}
            </p>
          )}
        </CardContent>
        <CardFooter>
          <Button type="submit" className="w-full" disabled={pending}>
            {pending ? "Checking…" : "Continue"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
