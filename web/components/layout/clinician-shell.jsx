"use client";

import { usePathname } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { ROUTES } from "@/lib/routes";

function titleForPath(pathname) {
  if (pathname === ROUTES.dashboard) return "Dashboard";
  if (pathname === ROUTES.patients) return "Patients";
  if (pathname.startsWith(`${ROUTES.patients}/`)) return "Patient detail";
  if (pathname === ROUTES.patientAccess) return "Patient access";
  return "Overview";
}

export function ClinicianShell({ children }) {
  const pathname = usePathname();
  const title = titleForPath(pathname);

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="bg-background/80 flex h-14 shrink-0 items-center gap-2 border-b px-4 backdrop-blur-sm">
          <SidebarTrigger />
          <Separator orientation="vertical" className="mr-1 h-6" />
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
              Clinician
            </span>
            <span className="truncate text-sm font-medium">{title}</span>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-6 p-6">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
