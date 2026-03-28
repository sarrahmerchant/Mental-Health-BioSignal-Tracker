import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export async function generateMetadata({ params }) {
  const { patientId } = await params;
  return {
    title: `Patient ${patientId}`,
    description: "Patient detail",
  };
}

export default async function PatientDetailPage({ params }) {
  const { patientId } = await params;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Patient detail</h1>
        <p className="text-muted-foreground mt-1 font-mono text-sm">{patientId}</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Record</CardTitle>
          <CardDescription>
            Demographics, care plan, and biosignals will render in this area.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm">
          Placeholder — connect APIs and components when ready.
        </CardContent>
      </Card>
    </div>
  );
}
