/**
 * Demo-only: file uploads + stub "AI" inferences in localStorage.
 * Production: POST files to your API; run model server-side; persist in DB.
 */

import { getDemoPatient } from "@/lib/demo-patients";

export const UPLOADS_STORAGE_KEY = "signalcare_demo_uploads";
export const INFERENCES_STORAGE_KEY = "signalcare_demo_ai_inferences";

export const DATA_CHANGED_EVENT = "signalcare-data-changed";

function safeParse(json, fallback) {
  try {
    const v = JSON.parse(json);
    return Array.isArray(v) ? v : fallback;
  } catch {
    return fallback;
  }
}

export function broadcastDataChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(DATA_CHANGED_EVENT));
}

/** For useSyncExternalStore when reading demo localStorage in React. */
export function subscribeToDemoData(onStoreChange) {
  if (typeof window === "undefined") return () => {};
  const handler = () => onStoreChange();
  window.addEventListener(DATA_CHANGED_EVENT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(DATA_CHANGED_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}

function readRaw(key) {
  if (typeof window === "undefined") return [];
  return safeParse(window.localStorage.getItem(key) ?? "[]", []);
}

function writeRaw(key, rows) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(rows));
}

export function readUploads() {
  return readRaw(UPLOADS_STORAGE_KEY);
}

export function readInferences() {
  return readRaw(INFERENCES_STORAGE_KEY);
}

/**
 * Stub inference — REPLACE with your model pipeline:
 * 1. Parse uploaded file (Apple Health export, etc.) into features.
 * 2. Call your model (batch or API) with those features + patient context.
 * 3. Map model JSON to these fields: summaryLine, hrvVsPriorWeek, restingHrVsPrior,
 *    sleepNote, stressRecoveryNote; set modelRunId / modelStatus from your job.
 * 4. Persist upload + inference server-side; drop localStorage in production.
 *
 * @param {{ uploadId: string, patientId: string, fileName: string }} ctx
 */
function buildStubInference(ctx) {
  const seed = ctx.fileName.length + ctx.patientId.length;
  const variants = [
    {
      summaryLine:
        "Overnight HRV slightly above prior 7-day average; no sustained dip.",
      hrvVsPriorWeek: "+4% vs prior week (stub)",
      restingHrVsPrior: "−1 bpm vs prior week (stub)",
      sleepNote: "Sleep duration within typical range (stub).",
      stressRecoveryNote:
        "Daytime recovery minutes modestly improved (stub).",
    },
    {
      summaryLine:
        "HRV flat vs baseline; resting HR unchanged—stable physiology window.",
      hrvVsPriorWeek: "±0% vs prior week (stub)",
      restingHrVsPrior: "+0 bpm vs prior week (stub)",
      sleepNote: "Mid-sleep wake episodes unchanged (stub).",
      stressRecoveryNote: "Afternoon stress load similar to prior week (stub).",
    },
    {
      summaryLine:
        "HRV down vs prior week; suggest clinical correlation (not diagnostic).",
      hrvVsPriorWeek: "−8% vs prior week (stub)",
      restingHrVsPrior: "+3 bpm vs prior week (stub)",
      sleepNote: "Later bedtimes 2/7 nights (stub).",
      stressRecoveryNote: "Recovery minutes lower Mon–Wed (stub).",
    },
  ];
  const pick = variants[seed % variants.length];
  return {
    id: crypto.randomUUID(),
    uploadId: ctx.uploadId,
    patientId: ctx.patientId,
    fileName: ctx.fileName,
    createdAt: new Date().toISOString(),
    modelRunId: "stub-heuristic-v0",
    modelStatus: "stub",
    ...pick,
  };
}

/**
 * Record a patient file upload and attach a placeholder inference row.
 */
export function recordUploadWithStubInference({ patientId, fileName, sizeBytes }) {
  const uploadId = crypto.randomUUID();
  const upload = {
    id: uploadId,
    patientId,
    fileName,
    sizeBytes: sizeBytes ?? null,
    uploadedAt: new Date().toISOString(),
    reviewedAt: null,
    source: "patient_portal",
  };
  const uploads = readUploads();
  writeRaw(UPLOADS_STORAGE_KEY, [upload, ...uploads]);

  const inference = buildStubInference({ uploadId, patientId, fileName });
  const inferences = readInferences();
  writeRaw(INFERENCES_STORAGE_KEY, [inference, ...inferences]);

  broadcastDataChanged();
  return { upload, inference };
}

export function markUploadReviewed(uploadId) {
  const uploads = readUploads().map((u) =>
    u.id === uploadId ? { ...u, reviewedAt: new Date().toISOString() } : u
  );
  writeRaw(UPLOADS_STORAGE_KEY, uploads);
  broadcastDataChanged();
}

export function getPendingUploadsForTriage() {
  return readUploads().filter((u) => !u.reviewedAt);
}

export function getUploadsForPatient(patientId) {
  return readUploads().filter((u) => u.patientId === patientId);
}

export function getInferencesForPatient(patientId) {
  return readInferences().filter((i) => i.patientId === patientId);
}

export function getInferenceByUploadId(uploadId) {
  return readInferences().find((i) => i.uploadId === uploadId) ?? null;
}

export function countPendingUploadsForPatient(patientId) {
  return getPendingUploadsForTriage().filter((u) => u.patientId === patientId)
    .length;
}

export function formatUploadedAgo(iso) {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diff = Date.now() - t;
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

/** Map pending uploads to triage row shape for the dashboard. */
export function getNewUploadTriageRows() {
  return getPendingUploadsForTriage().map((u) => {
    const p = getDemoPatient(u.patientId);
    return {
      id: u.id,
      patientId: u.patientId,
      patientLabel: p?.displayName ?? u.patientId,
      detail: u.fileName,
      at: formatUploadedAgo(u.uploadedAt),
    };
  });
}
