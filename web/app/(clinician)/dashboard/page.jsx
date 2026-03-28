import { TriageBoard } from "@/components/dashboard/triage-board";
import { TrendPlaceholder } from "@/components/charts/trend-placeholder";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const metadata = {
  title: "Dashboard",
  description: "Clinician workspace overview",
};

export default function DashboardPage() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1 max-w-2xl text-sm leading-relaxed">
          Start with triage: new biosignal data, patients who may need a call,
          and upcoming review milestones. Deeper analytics will layer in as
          integrations go live.
        </p>
      </div>

      <TriageBoard />

      <div>
        <h2 className="text-muted-foreground mb-4 text-xs font-medium uppercase tracking-wide">
          Workspace activity
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Panel activity (sample)</CardTitle>
              <CardDescription>
                Illustrative trend — not tied to live patient data yet.
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[220px] pt-0">
              <TrendPlaceholder />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Coverage snapshot</CardTitle>
              <CardDescription>
                Upload cadence and data gaps across your panel will appear here.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-muted-foreground text-sm">
              Connect ingestion pipelines to see patients with stale or missing
              wearable syncs.
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
