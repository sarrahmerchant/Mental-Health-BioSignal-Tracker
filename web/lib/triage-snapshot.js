/**
 * Clinician triage queue snapshot. Replace with API / DB when wired.
 * @returns {{
 *   newUploads: Array<{ id: string, patientLabel: string, detail: string, at: string }>,
 *   callAlerts: Array<{ id: string, patientLabel: string, detail: string, severity: string }>,
 *   reviewMilestones: Array<{ id: string, patientLabel: string, detail: string, dueIn: string }>,
 * }}
 */
export function getTriageSnapshot() {
  return {
    newUploads: [],
    callAlerts: [],
    reviewMilestones: [],
  };
}
