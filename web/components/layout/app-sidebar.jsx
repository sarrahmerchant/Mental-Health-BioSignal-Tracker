"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Users,
  UserRound,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import { ROUTES } from "@/lib/routes";

const navMain = [
  {
    title: "Dashboard",
    href: ROUTES.dashboard,
    icon: LayoutDashboard,
  },
  {
    title: "Patients",
    href: ROUTES.patients,
    icon: Users,
  },
  {
    title: "Patient access",
    href: ROUTES.patientAccess,
    icon: ShieldCheck,
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader className="border-b border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<Link href={ROUTES.dashboard} />}
              className="gap-2"
              tooltip="Clinician dashboard"
            >
              <UserRound className="text-sidebar-primary" />
              <span className="font-semibold tracking-tight">
                SignalCare Clinician
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navMain.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    render={<Link href={item.href} />}
                    isActive={
                      item.href === ROUTES.patients
                        ? pathname.startsWith(ROUTES.patients)
                        : pathname === item.href
                    }
                    tooltip={item.title}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarSeparator />
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<Link href={ROUTES.home} />}
              tooltip="Sign out (placeholder)"
            >
              <LogOut />
              <span>Sign out</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
