import { RedeemAccessForm } from "@/components/patient-portal/redeem-access-form";

export const metadata = {
  title: "Sign in with code",
  description: "Redeem your clinician access code",
};

export default function PatientPortalPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 px-4 py-12">
      <div className="max-w-lg space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">
          Patient portal
        </h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          Use the access code from your care team to open your personal space
          for Apple Watch / Health uploads and trends. This demo stores codes in
          your browser only—production will use a secure server.
        </p>
      </div>
      <RedeemAccessForm />
    </div>
  );
}
