export const ROUTES = {
  home: "/",
  dashboard: "/dashboard",
  patients: "/patients",
  patient: (patientId) => `/patients/${patientId}`,
  patientAccess: "/patient-access",
  /** Patient portal (access code redemption + dashboard) */
  patientPortal: "/patient",
  patientDashboard: "/patient/dashboard",
};
