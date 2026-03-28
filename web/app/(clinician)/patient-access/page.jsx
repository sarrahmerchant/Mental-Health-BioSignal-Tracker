import { AccessCodesManager } from "@/components/patient-access/access-codes-manager";

export const metadata = {
  title: "Patient access",
  description: "Access codes and patient portal invitations",
};

export default function PatientAccessPage() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Patient access</h1>
        <p className="text-muted-foreground mt-1 max-w-2xl text-sm leading-relaxed">
          Create one-time codes so patients can open the{" "}
          <strong className="text-foreground font-medium">patient portal</strong>{" "}
          to upload Apple Health / Watch data and view longitudinal summaries
          with you—not as a diagnosis, but as objective context alongside visits.
        </p>
      </div>
      <AccessCodesManager />
    </div>
  );
}
