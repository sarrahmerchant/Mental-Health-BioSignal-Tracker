/**
 * Hardcoded panel for demo / until EHR sync exists.
 * Replace with API-backed roster.
 */
export const DEMO_PATIENTS = [
  {
    id: "demo-pat-001",
    displayName: "Jordan A.",
    initials: "JA",
    nextReview: "2026-04-15",
  },
  {
    id: "demo-pat-002",
    displayName: "Morgan B.",
    initials: "MB",
    nextReview: "2026-04-22",
  },
  {
    id: "demo-pat-003",
    displayName: "Riley C.",
    initials: "RC",
    nextReview: "2026-05-01",
  },
];

export function getDemoPatient(patientId) {
  return DEMO_PATIENTS.find((p) => p.id === patientId) ?? null;
}
