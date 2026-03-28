import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PatientAiInsightsTable } from "@/components/patients/patient-ai-insights-table";
import { getDemoPatient } from "@/lib/demo-patients";

export async function generateMetadata({ params }) {
  const { patientId } = await params;
  const p = getDemoPatient(patientId);
  return {
    title: p ? p.displayName : `Patient ${patientId}`,
    description: "Patient detail",
  };
}

export default async function PatientDetailPage({ params }) {
  const { patientId } = await params;
  const patient = getDemoPatient(patientId);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {patient ? patient.displayName : "Patient chart"}
        </h1>
        <p className="text-muted-foreground mt-1 font-mono text-sm">
          {patientId}
        </p>
        {!patient && (
          <p className="text-muted-foreground mt-2 text-sm">
            Unknown demo id. Use{" "}
            <code className="bg-muted rounded px-1 text-xs">demo-pat-001</code>{" "}
            …{" "}
            <code className="bg-muted rounded px-1 text-xs">003</code> from the
            directory.
          </p>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Record</CardTitle>
          <CardDescription>
            Demographics and care plan (wire to API later).
            {patient && (
              <span className="mt-1 block">
                Next review (demo): {patient.nextReview}
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm">
          Placeholder — connect APIs when ready.
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            AI insights (per upload)
          </h2>
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm">
            Each patient upload from the portal creates a row here. Values are{" "}
            <strong className="text-foreground">hardcoded stubs</strong> in{" "}
            <code className="bg-muted rounded px-1 text-xs">
              buildStubInference
            </code>{" "}
            until you pipe real model output into the same shape.
          </p>
        </div>
        <PatientAiInsightsTable patientId={patientId} />
      </section>
    </div>
  );
}
