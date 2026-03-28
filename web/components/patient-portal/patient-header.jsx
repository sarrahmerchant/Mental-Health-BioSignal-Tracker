"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { clearPatientSession } from "@/lib/demo-access-storage";
import { ROUTES } from "@/lib/routes";

export function PatientHeader() {
  const pathname = usePathname();
  const onDashboard = pathname?.startsWith(ROUTES.patientDashboard);

  const handleSignOut = () => {
    clearPatientSession();
    window.location.href = ROUTES.patientPortal;
  };

  return (
    <header className="bg-background/80 sticky top-0 z-50 border-b backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
        <Link
          href={ROUTES.patientPortal}
          className="text-foreground text-sm font-semibold tracking-tight"
        >
          SignalCare <span className="text-muted-foreground font-normal">Patient</span>
        </Link>
        <nav className="flex items-center gap-2 sm:gap-4">
          <Link
            href={ROUTES.home}
            className="text-muted-foreground hover:text-foreground text-sm transition-colors"
          >
            Clinician sign in
          </Link>
          {onDashboard && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleSignOut}
            >
              <LogOut className="size-3.5" />
              Sign out
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}
