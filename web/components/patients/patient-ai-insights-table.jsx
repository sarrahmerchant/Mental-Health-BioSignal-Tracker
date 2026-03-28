"use client";

import { useMemo, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import {
  getInferencesForPatient,
  markUploadReviewed,
  subscribeToDemoData,
} from "@/lib/demo-uploads-storage";

function formatWhen(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function PatientAiInsightsTable({ patientId }) {
  const rowsJson = useSyncExternalStore(
    subscribeToDemoData,
    () => JSON.stringify(getInferencesForPatient(patientId)),
    () => "[]"
  );
  const rows = useMemo(() => JSON.parse(rowsJson), [rowsJson]);

  const handleReviewed = (uploadId) => {
    markUploadReviewed(uploadId);
  };

  if (rows.length === 0) {
    return (
      <p className="text-muted-foreground border-border/80 bg-muted/20 rounded-lg border border-dashed px-4 py-8 text-center text-sm">
        No model runs yet for this patient. After a file upload from the patient
        portal, a stub inference row appears here. Replace stub output with your
        model response in{" "}
        <code className="text-foreground bg-muted rounded px-1 py-0.5 text-xs">
          lib/demo-uploads-storage.js
        </code>{" "}
        →{" "}
        <code className="text-foreground bg-muted rounded px-1 py-0.5 text-xs">
          buildStubInference
        </code>
        .
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-muted/50 border-b text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2">When</th>
            <th className="px-3 py-2">File</th>
            <th className="px-3 py-2">Model</th>
            <th className="px-3 py-2">Summary</th>
            <th className="px-3 py-2">HRV</th>
            <th className="px-3 py-2">RHR</th>
            <th className="px-3 py-2">Sleep</th>
            <th className="px-3 py-2">Stress / recovery</th>
            <th className="px-3 py-2 w-28">Triage</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((r) => (
            <tr key={r.id} className="hover:bg-muted/30">
              <td className="text-muted-foreground px-3 py-2 whitespace-nowrap">
                {formatWhen(r.createdAt)}
              </td>
              <td className="max-w-[140px] truncate px-3 py-2 font-mono text-xs">
                {r.fileName}
              </td>
              <td className="px-3 py-2">
                <span className="text-xs font-medium">{r.modelRunId}</span>
                <span className="text-muted-foreground block text-xs">
                  {r.modelStatus}
                </span>
              </td>
              <td className="text-muted-foreground max-w-[220px] px-3 py-2 text-xs leading-snug">
                {r.summaryLine}
              </td>
              <td className="text-muted-foreground px-3 py-2 text-xs">
                {r.hrvVsPriorWeek}
              </td>
              <td className="text-muted-foreground px-3 py-2 text-xs">
                {r.restingHrVsPrior}
              </td>
              <td className="text-muted-foreground max-w-[160px] px-3 py-2 text-xs">
                {r.sleepNote}
              </td>
              <td className="text-muted-foreground max-w-[180px] px-3 py-2 text-xs">
                {r.stressRecoveryNote}
              </td>
              <td className="px-3 py-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => handleReviewed(r.uploadId)}
                >
                  Mark reviewed
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
