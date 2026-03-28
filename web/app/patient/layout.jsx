import { PatientHeader } from "@/components/patient-portal/patient-header";

export const metadata = {
  title: "Patient",
  description: "Patient portal — access code and wearable summaries",
};

export default function PatientLayout({ children }) {
  return (
    <div className="bg-muted/20 flex min-h-full flex-col">
      <PatientHeader />
      <main className="flex flex-1 flex-col">{children}</main>
    </div>
  );
}
