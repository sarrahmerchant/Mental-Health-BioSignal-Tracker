import Link from "next/link";

import { ROUTES } from "@/lib/routes";

export function SiteHeader() {
  return (
    <header className="bg-background/80 sticky top-0 z-50 border-b backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
        <Link
          href={ROUTES.home}
          className="text-foreground text-sm font-semibold tracking-tight"
        >
          SignalCare
        </Link>
        <nav className="text-muted-foreground flex items-center gap-6 text-sm">
          <Link
            href={ROUTES.patientPortal}
            className="hover:text-foreground transition-colors"
          >
            Patient portal
          </Link>
          <Link href={ROUTES.home} className="hover:text-foreground transition-colors">
            Sign in
          </Link>
          <Link
            href={ROUTES.dashboard}
            className="text-foreground hover:text-foreground/80 transition-colors"
          >
            Continue to app
          </Link>
        </nav>
      </div>
    </header>
  );
}
