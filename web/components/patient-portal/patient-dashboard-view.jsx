"use client";

import { useLayoutEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, Heart, Moon, Upload, History } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  readPatientSession,
  validatePatientSession,
} from "@/lib/demo-access-storage";
import { ROUTES } from "@/lib/routes";

export function PatientDashboardView() {
  const router = useRouter();
  const [session] = useState(() =>
    validatePatientSession() ? readPatientSession() : null
  );

  useLayoutEffect(() => {
    if (!session) {
      router.replace(ROUTES.patientPortal);
    }
  }, [session, router]);

  if (!session) {
    return (
      <div className="text-muted-foreground flex flex-1 items-center justify-center p-8 text-sm">
        Redirecting…
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Your dashboard</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Welcome back{session.patientLabel ? `, ${session.patientLabel}` : ""}.
          Upload Apple Health / Watch exports and review trends to discuss with
          your clinician.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Upload className="size-4" />
              Upload data
            </CardTitle>
            <CardDescription>
              Export from Apple Health on your iPhone and upload the file here
              (wire-up coming next).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" disabled className="w-full sm:w-auto">
              Choose file
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="size-4" />
              Past uploads
            </CardTitle>
            <CardDescription>
              You will see each upload with date and status once ingestion is
              connected.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-muted-foreground text-sm">
            No uploads yet.
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="text-muted-foreground mb-3 text-xs font-medium uppercase tracking-wide">
          Summaries (placeholder)
        </h2>
        <p className="text-muted-foreground mb-4 max-w-2xl text-sm">
          These metrics are illustrative. When data is available, we will show
          HRV averages, weekly trends, resting heart rate, sleep consistency,
          and a transparent &quot;recovery&quot; view derived from HRV—not a
          medical score.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricPlaceholder
            icon={Heart}
            title="HRV average"
            detail="Rolling 7-day (demo)"
          />
          <MetricPlaceholder
            icon={Activity}
            title="Weekly trend"
            detail="Vs prior week"
          />
          <MetricPlaceholder
            icon={Moon}
            title="Sleep consistency"
            detail="Timing stability"
          />
          <MetricPlaceholder
            icon={Activity}
            title="Stress / recovery"
            detail="From HRV + rest"
          />
        </div>
      </div>
    </div>
  );
}

function MetricPlaceholder({ icon: Icon, title, detail }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Icon className="text-muted-foreground size-4" />
          {title}
        </CardTitle>
        <CardDescription className="text-xs">{detail}</CardDescription>
      </CardHeader>
      <CardContent className="text-muted-foreground text-2xl font-semibold tabular-nums">
        —
      </CardContent>
    </Card>
  );
}
