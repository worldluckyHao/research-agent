"use client";

import Link from "next/link";

import {
  usePathname,
  useRouter,
} from "next/navigation";

import {
  useAuth,
} from "@/contexts/auth-context";


const navigation = [
  {
    label: "Dashboard",
    href: "/dashboard",
  },
  {
    label: "Papers",
    href: "/papers",
  },
  {
    label: "Projects",
    href: "/projects",
  },
  {
    label: "AI Research",
    href: "/research",
  },
];


export function Sidebar() {
  const pathname =
    usePathname();

  const router =
    useRouter();

  const {
    user,
    logout,
  } = useAuth();


  function handleLogout() {
    logout();

    router.replace(
      "/login",
    );
  }


  return (
    <aside
      className="
        flex h-screen
        w-64
        shrink-0
        flex-col
        border-r
        border-slate-200
        bg-slate-950
        text-white
      "
    >
      {/* Brand */}
      <div
        className="
          border-b
          border-slate-800
          px-6
          py-6
        "
      >
        <h1
          className="
            text-xl
            font-semibold
          "
        >
          Research Agent
        </h1>

        <p
          className="
            mt-1
            text-xs
            text-slate-400
          "
        >
          AI Research Workspace
        </p>
      </div>


      {/* Navigation */}
      <nav
        className="
          flex-1
          space-y-2
          p-4
        "
      >
        {navigation.map(
          (item) => {
            const active =
              pathname ===
              item.href;

            return (
              <Link
                key={
                  item.href
                }

                href={
                  item.href
                }

                className={`
                  block
                  rounded-lg
                  px-4
                  py-3
                  text-sm
                  transition

                  ${
                    active
                      ? "bg-white text-slate-950"
                      : "text-slate-300 hover:bg-slate-900 hover:text-white"
                  }
                `}
              >
                {
                  item.label
                }
              </Link>
            );
          },
        )}
      </nav>


      {/* User */}
      <div
        className="
          border-t
          border-slate-800
          p-4
        "
      >
        <div
          className="
            mb-3
            rounded-lg
            bg-slate-900
            p-3
          "
        >
          <p
            className="
              truncate
              text-sm
              font-medium
            "
          >
            {
              user?.username
            }
          </p>

          <p
            className="
              mt-1
              truncate
              text-xs
              text-slate-400
            "
          >
            {
              user?.email
            }
          </p>
        </div>

        <button
          onClick={
            handleLogout
          }

          className="
            w-full
            rounded-lg
            border
            border-slate-700
            px-4
            py-2
            text-sm
            text-slate-300
            transition
            hover:bg-slate-800
            hover:text-white
          "
        >
          退出登录
        </button>
      </div>
    </aside>
  );
}