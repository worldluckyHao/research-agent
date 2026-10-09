"use client";

import {
  useEffect,
  type ReactNode,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  useAuth,
} from "@/contexts/auth-context";


export function ProtectedRoute({
  children,
}: {
  children: ReactNode;
}) {
  const router =
    useRouter();

  const {
    user,
    loading,
  } = useAuth();


  useEffect(() => {
    if (
      !loading &&
      !user
    ) {
      router.replace(
        "/login",
      );
    }
  }, [
    loading,
    user,
    router,
  ]);


  if (
    loading ||
    !user
  ) {
    return (
      <div
        className="
          flex min-h-screen
          items-center
          justify-center
          bg-slate-50
        "
      >
        <div
          className="
            rounded-xl
            border
            border-slate-200
            bg-white
            px-6
            py-4
            text-sm
            text-slate-500
            shadow-sm
          "
        >
          正在验证登录状态...
        </div>
      </div>
    );
  }


  return (
    <>
      {children}
    </>
  );
}