"use client";

import type {
  ReactNode,
} from "react";

import {
  Sidebar,
} from "@/components/layout/sidebar";


export function DashboardShell({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div
      className="
        flex min-h-screen
        bg-slate-50
      "
    >
      <Sidebar />

      <main
        className="
          min-w-0
          flex-1
          overflow-y-auto
        "
      >
        {children}
      </main>
    </div>
  );
}