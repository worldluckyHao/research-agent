import type {
  ReactNode,
} from "react";

import {
  ProtectedRoute,
} from "@/components/auth/protected-route";

import {
  DashboardShell,
} from "@/components/layout/dashboard-shell";


export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ProtectedRoute>
      <DashboardShell>
        {children}
      </DashboardShell>
    </ProtectedRoute>
  );
}