"use client";

import { useMemo, useSyncExternalStore } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { DEMO_PATIENTS } from "@/lib/demo-patients";
import {
  countPendingUploadsForPatient,
  subscribeToDemoData,
} from "@/lib/demo-uploads-storage";
import { ROUTES } from "@/lib/routes";

function getPendingCountsJson() {
  const map = {};
  for (const p of DEMO_PATIENTS) {
    map[p.id] = countPendingUploadsForPatient(p.id);
  }
  return JSON.stringify(map);
}

export function PatientsDirectory() {
  const pendingJson = useSyncExternalStore(
    subscribeToDemoData,
    getPendingCountsJson,
    () => JSON.stringify(Object.fromEntries(DEMO_PATIENTS.map((p) => [p.id, 0])))
  );
  const pending = useMemo(() => JSON.parse(pendingJson), [pendingJson]);

  return (
    <div className="flex flex-col gap-3">
      {DEMO_PATIENTS.map((p) => {
        const n = pending[p.id] ?? 0;
        return (
          <Link
            key={p.id}
            href={ROUTES.patient(p.id)}
            className="hover:bg-muted/50 flex items-center justify-between gap-4 rounded-xl border bg-card px-4 py-3 transition-colors"
          >
            <div className="flex min-w-0 items-center gap-3">
              <span className="bg-muted flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold">
                {p.initials}
              </span>
              <div className="min-w-0">
                <p className="font-medium">{p.displayName}</p>
                <p className="text-muted-foreground text-xs">
                  Next review (demo): {p.nextReview}
                </p>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {n > 0 && (
                <span className="bg-primary/15 text-primary rounded-full px-2 py-0.5 text-xs font-semibold">
                  {n} new upload{n === 1 ? "" : "s"}
                </span>
              )}
              <ChevronRight className="text-muted-foreground size-4" />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
