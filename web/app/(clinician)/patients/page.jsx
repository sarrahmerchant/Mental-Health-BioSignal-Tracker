import { PlaceholderPatientLink } from "@/components/patients/placeholder-patient-link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

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
          <p className="text-muted-foreground mt-1 text-sm">
            Your panel will list enrolled patients here.
          </p>
        </div>
        <Button variant="outline" disabled>
          Add patient
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Directory</CardTitle>
          <CardDescription>Empty state — no list data yet.</CardDescription>
        </CardHeader>
        <CardContent className="text-muted-foreground flex flex-col gap-4 text-sm">
          <p>To preview navigation, open a placeholder detail view:</p>
          <PlaceholderPatientLink />
        </CardContent>
      </Card>
    </div>
  );
}
