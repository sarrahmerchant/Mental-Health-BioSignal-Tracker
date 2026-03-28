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
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Overview of your workspace. Data integrations will appear here.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Activity (placeholder)</CardTitle>
            <CardDescription>
              Sample chart — Recharts is installed; not clinical data.
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[220px] pt-0">
            <TrendPlaceholder />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Today</CardTitle>
            <CardDescription>
              Summary cards and alerts will mount here in a later milestone.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-muted-foreground text-sm">
            No metrics yet.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
