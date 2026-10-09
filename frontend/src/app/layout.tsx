import type {
  Metadata,
} from "next";

import {
  AuthProvider,
} from "@/contexts/auth-context";

import "./globals.css";


export const metadata: Metadata = {
  title:
    "Research Agent",

  description:
    "AI-powered academic research assistant",
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}