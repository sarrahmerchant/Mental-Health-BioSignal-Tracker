import Link from "next/link";
import { Upload, PhoneOutgoing, CalendarClock, ChevronRight } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getTriageSnapshot } from "@/lib/triage-snapshot";
import { ROUTES } from "@/lib/routes";

function CountBadge({ count }) {
  return (
    <span className="bg-muted text-muted-foreground inline-flex min-w-8 items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums">
      {count}
    </span>
  );
}

function EmptyQueue({ children }) {
  return (
    <p className="text-muted-foreground border-border/80 bg-muted/20 rounded-lg border border-dashed px-3 py-6 text-center text-sm leading-relaxed">
      {children}
    </p>
  );
}

function QueueRow({ href, primary, secondary, meta }) {
  return (
    <Link
      href={href}
      className="hover:bg-muted/60 flex items-start gap-3 rounded-lg border border-transparent px-2 py-2.5 transition-colors"
    >
      <div className="min-w-0 flex-1">
        <p className="text-foreground text-sm font-medium">{primary}</p>
        <p className="text-muted-foreground mt-0.5 text-xs">{secondary}</p>
      </div>
      {meta && (
        <span className="text-muted-foreground shrink-0 text-xs tabular-nums">
          {meta}
        </span>
      )}
      <ChevronRight className="text-muted-foreground mt-0.5 size-4 shrink-0 opacity-60" />
    </Link>
  );
}

export function TriageBoard() {
  const { newUploads, callAlerts, reviewMilestones } = getTriageSnapshot();
  const totalAttention =
    newUploads.length + callAlerts.length + reviewMilestones.length;

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            Triage · Today
          </h2>
          <p className="text-muted-foreground max-w-xl text-sm">
            Prioritize patients who need a look, a call, or a scheduled review.
            Queues will fill automatically when uploads and milestones are
            connected.
          </p>
        </div>
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <span className="font-medium text-foreground tabular-nums">
            {totalAttention}
          </span>
          <span>open item{totalAttention === 1 ? "" : "s"} today</span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-l-primary/80 border-l-4 shadow-none">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="bg-primary/10 text-primary flex size-9 items-center justify-center rounded-lg">
                  <Upload className="size-4" aria-hidden />
                </span>
                <div>
                  <CardTitle className="text-base">New data uploads</CardTitle>
                  <CardDescription>
                    Wearable syncs and file imports awaiting review
                  </CardDescription>
                </div>
              </div>
              <CountBadge count={newUploads.length} />
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {newUploads.length === 0 ? (
              <EmptyQueue>
                No new uploads since your last review. When patients share Apple
                Health / Watch data, they will appear here first.
              </EmptyQueue>
            ) : (
              <ul className="divide-border -mx-2 divide-y">
                {newUploads.map((row) => (
                  <li key={row.id}>
                    <QueueRow
                      href={ROUTES.patient(row.id)}
                      primary={row.patientLabel}
                      secondary={row.detail}
                      meta={row.at}
                    />
                  </li>
                ))}
              </ul>
            )}
            <Link
              href={ROUTES.patients}
              className="text-primary mt-3 inline-flex items-center gap-1 text-sm font-medium hover:underline"
            >
              All patients
              <ChevronRight className="size-4" />
            </Link>
          </CardContent>
        </Card>

        <Card className="border-l-amber-500/80 border-l-4 shadow-none">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="flex size-9 items-center justify-center rounded-lg bg-amber-500/15 text-amber-700 dark:text-amber-400">
                  <PhoneOutgoing className="size-4" aria-hidden />
                </span>
                <div>
                  <CardTitle className="text-base">Call / follow-up</CardTitle>
                  <CardDescription>
                    Flags, missed check-ins, or risk signals worth a call
                  </CardDescription>
                </div>
              </div>
              <CountBadge count={callAlerts.length} />
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {callAlerts.length === 0 ? (
              <EmptyQueue>
                No patients flagged for outreach right now. Rules for alerts
                (e.g. data gaps, symptom scores) will surface here.
              </EmptyQueue>
            ) : (
              <ul className="divide-border -mx-2 divide-y">
                {callAlerts.map((row) => (
                  <li key={row.id}>
                    <QueueRow
                      href={ROUTES.patient(row.id)}
                      primary={row.patientLabel}
                      secondary={row.detail}
                      meta={row.severity}
                    />
                  </li>
                ))}
              </ul>
            )}
            <Link
              href={ROUTES.patients}
              className="text-primary mt-3 inline-flex items-center gap-1 text-sm font-medium hover:underline"
            >
              Patient directory
              <ChevronRight className="size-4" />
            </Link>
          </CardContent>
        </Card>

        <Card className="border-l-violet-500/80 border-l-4 shadow-none">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="flex size-9 items-center justify-center rounded-lg bg-violet-500/15 text-violet-700 dark:text-violet-400">
                  <CalendarClock className="size-4" aria-hidden />
                </span>
                <div>
                  <CardTitle className="text-base">Review milestones</CardTitle>
                  <CardDescription>
                    Visits, titration checks, or protocol windows due soon
                  </CardDescription>
                </div>
              </div>
              <CountBadge count={reviewMilestones.length} />
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {reviewMilestones.length === 0 ? (
              <EmptyQueue>
                No reviews due in the current window. Link your scheduling or
                care-plan milestones to populate this column.
              </EmptyQueue>
            ) : (
              <ul className="divide-border -mx-2 divide-y">
                {reviewMilestones.map((row) => (
                  <li key={row.id}>
                    <QueueRow
                      href={ROUTES.patient(row.id)}
                      primary={row.patientLabel}
                      secondary={row.detail}
                      meta={row.dueIn}
                    />
                  </li>
                ))}
              </ul>
            )}
            <Link
              href={ROUTES.patients}
              className="text-primary mt-3 inline-flex items-center gap-1 text-sm font-medium hover:underline"
            >
              Open calendar (soon)
              <ChevronRight className="size-4" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
