/**
 * Browser-only demo storage for access codes (clinician) and patient session.
 * Replace with API + httpOnly cookies in production.
 */

export const DEMO_CODES_KEY = "signalcare_demo_access_codes";
export const PATIENT_SESSION_KEY = "signalcare_patient_session";

const CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

function randomSegment(length) {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  let out = "";
  for (let i = 0; i < length; i += 1) {
    out += CODE_CHARS[bytes[i] % CODE_CHARS.length];
  }
  return out;
}

export function generateAccessCodeString() {
  return `SC-${randomSegment(4)}-${randomSegment(4)}`;
}

function safeParse(json, fallback) {
  try {
    const v = JSON.parse(json);
    return Array.isArray(v) ? v : fallback;
  } catch {
    return fallback;
  }
}

export function readCodes() {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(DEMO_CODES_KEY);
  return safeParse(raw ?? "[]", []);
}

export function writeCodes(codes) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DEMO_CODES_KEY, JSON.stringify(codes));
}

export function createAccessCodeEntry({ patientLabel, validityDays }) {
  const now = Date.now();
  const expiresAt = new Date(
    now + Math.max(1, validityDays) * 24 * 60 * 60 * 1000
  ).toISOString();
  const entry = {
    id: crypto.randomUUID(),
    code: generateAccessCodeString(),
    patientLabel: patientLabel?.trim() || "Patient",
    createdAt: new Date(now).toISOString(),
    expiresAt,
    revoked: false,
    redeemedAt: null,
  };
  const codes = readCodes();
  writeCodes([entry, ...codes]);
  return entry;
}

export function revokeAccessCode(id) {
  const codes = readCodes();
  writeCodes(
    codes.map((c) => (c.id === id ? { ...c, revoked: true } : c))
  );
}

export function findCodeByString(raw) {
  const normalized = raw.trim().toUpperCase().replace(/\s+/g, "");
  const codes = readCodes();
  return codes.find((c) => c.code === normalized) ?? null;
}

export function isCodeRedeemable(entry) {
  if (!entry || entry.revoked) return false;
  if (entry.redeemedAt) return false;
  return Date.now() < new Date(entry.expiresAt).getTime();
}

export function markCodeRedeemed(id) {
  const codes = readCodes();
  writeCodes(
    codes.map((c) => (c.id === id ? { ...c, redeemedAt: new Date().toISOString() } : c))
  );
}

export function readPatientSession() {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(PATIENT_SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function writePatientSession(session) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(PATIENT_SESSION_KEY, JSON.stringify(session));
}

export function clearPatientSession() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(PATIENT_SESSION_KEY);
}

/** Returns true if session is still valid against current code list. */
export function validatePatientSession() {
  const session = readPatientSession();
  if (!session?.codeId) return false;
  const codes = readCodes();
  const entry = codes.find((c) => c.id === session.codeId);
  if (!entry || entry.revoked) return false;
  if (!entry.redeemedAt) return false;
  if (Date.now() >= new Date(entry.expiresAt).getTime()) return false;
  return true;
}
