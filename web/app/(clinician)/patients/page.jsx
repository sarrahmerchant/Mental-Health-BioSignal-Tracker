import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PatientsDirectory } from "@/components/patients/patients-directory";

export const metadata = {
  title: "Patients",
  description: "Patient list",
};

export default function PatientsPage() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Patients</h1>
          <p className="text-muted-foreground mt-1 max-w-xl text-sm">
            Demo roster—replace <code className="text-foreground bg-muted rounded px-1 text-xs">lib/demo-patients.js</code> with your EHR or API. Badges show pending file uploads (same browser{" "}
            <code className="text-foreground bg-muted rounded px-1 text-xs">localStorage</code>).
          </p>
        </div>
        <Button variant="outline" disabled>
          Add patient
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Directory</CardTitle>
          <CardDescription>
            Open a chart to see uploads and stub model output for that patient.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PatientsDirectory />
        </CardContent>
      </Card>
    </div>
  );
}
