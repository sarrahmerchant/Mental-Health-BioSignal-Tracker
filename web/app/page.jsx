import Link from "next/link";

import { SiteHeader } from "@/components/layout/site-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ROUTES } from "@/lib/routes";

export const metadata = {
  title: "Sign in",
  description: "Clinician sign-in",
};

export default function LandingPage() {
  return (
    <div className="bg-muted/30 flex min-h-full flex-col">
      <SiteHeader />
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-16">
        <div className="w-full max-w-md space-y-8">
          <div className="space-y-2 text-center">
            <h1 className="text-3xl font-semibold tracking-tight">
              Clinician sign in
            </h1>
            <p className="text-muted-foreground text-sm">
              Healthcare biosignal tracking for your practice. Authentication is
              not wired yet—this screen is a layout placeholder.
            </p>
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Credentials</CardTitle>
              <CardDescription>Use your organization email.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  placeholder="you@clinic.org"
                  disabled
                />
              </div>
              <div className="grid gap-2">
                <label htmlFor="password" className="text-sm font-medium">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  disabled
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-3">
              <Button className="w-full" disabled>
                Sign in
              </Button>
              <Button
                nativeButton={false}
                render={<Link href={ROUTES.dashboard} />}
                variant="outline"
                className="w-full"
              >
                Continue to dashboard (dev)
              </Button>
            </CardFooter>
          </Card>
        </div>
      </main>
    </div>
  );
}
