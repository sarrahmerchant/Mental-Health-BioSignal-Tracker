"use client";

import { useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  Heart,
  Moon,
  Upload,
  History,
  CheckCircle2,
  UserRound,
  Shield,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getDemoPatient } from "@/lib/demo-patients";
import {
  formatUploadedAgo,
  getUploadsForPatient,
  recordUploadWithStubInference,
  subscribeToDemoData,
} from "@/lib/demo-uploads-storage";
import {
  readPatientSession,
  validatePatientSession,
} from "@/lib/demo-access-storage";
import { ROUTES } from "@/lib/routes";

export function PatientDashboardView() {
  const router = useRouter();
  const [session] = useState(() =>
    validatePatientSession() ? readPatientSession() : null
  );
  const [toast, setToast] = useState(null);
  const fileRef = useRef(null);

  const patientId = session?.patientId ?? "";
  const rosterPatient = patientId ? getDemoPatient(patientId) : null;
  const displayName =
    session?.displayName ?? rosterPatient?.displayName ?? "Patient";

  const uploadsJson = useSyncExternalStore(
    subscribeToDemoData,
    () => JSON.stringify(getUploadsForPatient(patientId)),
    () => "[]"
  );
  const uploads = useMemo(() => JSON.parse(uploadsJson), [uploadsJson]);

  useLayoutEffect(() => {
    if (!session || !session.patientId) {
      router.replace(ROUTES.patientPortal);
    }
  }, [session, router]);

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !patientId) {
      setToast("Something went wrong. Please sign in again with your code.");
      return;
    }
    recordUploadWithStubInference({
      patientId,
      fileName: file.name,
      sizeBytes: file.size,
    });
    setToast(`Uploaded “${file.name}”. Your clinician will see it on their dashboard.`);
    setTimeout(() => setToast(null), 5000);
  };

  if (!session || !session.patientId) {
    return (
      <div className="text-muted-foreground flex flex-1 items-center justify-center p-8 text-sm">
        Redirecting…
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Your dashboard</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Signed in as <span className="text-foreground font-medium">{displayName}</span>.
          Uploads are tied only to your chart—other patients are never visible here.
        </p>
      </div>

      {toast && (
        <div className="bg-primary/10 text-foreground flex items-start gap-2 rounded-lg border border-primary/20 px-4 py-3 text-sm">
          <CheckCircle2 className="text-primary mt-0.5 size-4 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-l-primary/60 border-l-4 lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserRound className="size-4" />
              Your chart (this code only)
            </CardTitle>
            <CardDescription>
              Information scoped to the access code your clinician gave you.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wide">
                Name on chart
              </p>
              <p className="font-medium">{displayName}</p>
            </div>
            {rosterPatient && (
              <>
                <div>
                  <p className="text-muted-foreground text-xs uppercase tracking-wide">
                    Next review target (demo)
                  </p>
                  <p>{rosterPatient.nextReview}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs uppercase tracking-wide">
                    Record ID (demo)
                  </p>
                  <p className="font-mono text-xs">{patientId}</p>
                </div>
              </>
            )}
            {!rosterPatient && (
              <p className="text-muted-foreground text-xs">
                This patient id is not on the demo roster—clinician view may still
                list uploads under <span className="font-mono">{patientId}</span>.
              </p>
            )}
            <div className="text-muted-foreground flex gap-2 border-t pt-3 text-xs leading-snug">
              <Shield className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              <span>
                You cannot switch to another patient or see their data from this
                session. Production should enforce the same on the server.
              </span>
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Upload className="size-4" />
                Upload data
              </CardTitle>
              <CardDescription>
                Apple Health / Watch exports (e.g. .zip). Files are stored for demo
                triage only—not clinically parsed yet.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <input
                ref={fileRef}
                type="file"
                className="sr-only"
                accept=".zip,.xml,.csv,.json,application/zip,text/xml,text/csv,application/json,*/*"
                onChange={handleFile}
              />
              <Button
                type="button"
                className="w-full sm:w-auto"
                onClick={() => fileRef.current?.click()}
              >
                Choose file
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <History className="size-4" />
                Your upload history
              </CardTitle>
              <CardDescription>
                Only uploads sent from this portal for your chart in this browser.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {uploads.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No files yet. Upload an export to share with your care team.
                </p>
              ) : (
                <ul className="divide-border divide-y text-sm">
                  {uploads.map((u) => (
                    <li
                      key={u.id}
                      className="flex flex-col gap-0.5 py-2 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <span className="font-mono text-xs">{u.fileName}</span>
                      <span className="text-muted-foreground text-xs">
                        {formatUploadedAgo(u.uploadedAt)}
                        {u.reviewedAt && " · Reviewed by clinic"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div>
        <h2 className="text-muted-foreground mb-3 text-xs font-medium uppercase tracking-wide">
          Summaries (placeholder)
        </h2>
        <p className="text-muted-foreground mb-4 max-w-2xl text-sm">
          After ingestion and your model run, personal summaries can mirror what
          clinicians see in the AI insights table—not a diagnosis.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricPlaceholder
            icon={Heart}
            title="HRV average"
            detail="Rolling 7-day (demo)"
          />
          <MetricPlaceholder
            icon={Activity}
            title="Weekly trend"
            detail="Vs prior week"
          />
          <MetricPlaceholder
            icon={Moon}
            title="Sleep consistency"
            detail="Timing stability"
          />
          <MetricPlaceholder
            icon={Activity}
            title="Stress / recovery"
            detail="From HRV + rest"
          />
        </div>
      </div>
    </div>
  );
}

function MetricPlaceholder({ icon: Icon, title, detail }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Icon className="text-muted-foreground size-4" />
          {title}
        </CardTitle>
        <CardDescription className="text-xs">{detail}</CardDescription>
      </CardHeader>
      <CardContent className="text-muted-foreground text-2xl font-semibold tabular-nums">
        —
      </CardContent>
    </Card>
  );
}
