"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/routes";

export function PlaceholderPatientLink() {
  return (
    <Link
      href={ROUTES.patient("example-id")}
      className={cn(buttonVariants(), "w-fit no-underline")}
    >
      Open placeholder patient
    </Link>
  );
}
