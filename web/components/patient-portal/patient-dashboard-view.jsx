"use client";

import { useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { Activity, Heart, Moon, Upload, History, CheckCircle2 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DEMO_PATIENTS } from "@/lib/demo-patients";
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
  const [patientRecordId, setPatientRecordId] = useState(
    () => DEMO_PATIENTS[0]?.id ?? ""
  );
  const [toast, setToast] = useState(null);
  const fileRef = useRef(null);

  const uploadsJson = useSyncExternalStore(
    subscribeToDemoData,
    () => JSON.stringify(getUploadsForPatient(patientRecordId)),
    () => "[]"
  );
  const uploads = useMemo(() => JSON.parse(uploadsJson), [uploadsJson]);

  useLayoutEffect(() => {
    if (!session) {
      router.replace(ROUTES.patientPortal);
    }
  }, [session, router]);

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !patientRecordId) {
      setToast("Choose a demo profile and a file.");
      return;
    }
    recordUploadWithStubInference({
      patientId: patientRecordId,
      fileName: file.name,
      sizeBytes: file.size,
    });
    setToast(`Uploaded “${file.name}”. Your clinician will see it on their dashboard.`);
    setTimeout(() => setToast(null), 5000);
  };

  if (!session) {
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
          Welcome back{session.patientLabel ? `, ${session.patientLabel}` : ""}.
          Upload Apple Health / Watch exports for your clinician to review.
        </p>
      </div>

      {toast && (
        <div className="bg-primary/10 text-foreground flex items-start gap-2 rounded-lg border border-primary/20 px-4 py-3 text-sm">
          <CheckCircle2 className="text-primary mt-0.5 size-4 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Upload className="size-4" />
              Upload data
            </CardTitle>
            <CardDescription>
              Demo: pick the clinic record that matches you, then choose any file
              (e.g. Health export .zip). Files are not parsed yet—only logged for
              triage.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label htmlFor="demo-patient-record" className="text-sm font-medium">
                Clinic profile (demo)
              </label>
              <select
                id="demo-patient-record"
                value={patientRecordId}
                onChange={(e) => setPatientRecordId(e.target.value)}
                className="border-input bg-background h-9 w-full rounded-lg border px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                {DEMO_PATIENTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.displayName}
                  </option>
                ))}
              </select>
            </div>
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
              Past uploads
            </CardTitle>
            <CardDescription>
              Uploads for the selected clinic profile in this browser.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {uploads.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                No files yet for this profile.
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
