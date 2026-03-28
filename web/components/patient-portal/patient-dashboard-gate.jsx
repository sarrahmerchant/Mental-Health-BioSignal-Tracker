"use client";

import dynamic from "next/dynamic";

const PatientDashboardView = dynamic(
  () =>
    import("@/components/patient-portal/patient-dashboard-view").then(
      (m) => m.PatientDashboardView
    ),
  {
    ssr: false,
    loading: () => (
      <div className="text-muted-foreground flex flex-1 items-center justify-center p-8 text-sm">
        Loading…
      </div>
    ),
  }
);

export function PatientDashboardGate() {
  return <PatientDashboardView />;
}
