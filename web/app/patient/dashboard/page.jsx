import { PatientDashboardGate } from "@/components/patient-portal/patient-dashboard-gate";

export const metadata = {
  title: "Your dashboard",
  description: "Uploads and biosignal summaries",
};

export default function PatientDashboardPage() {
  return <PatientDashboardGate />;
}
