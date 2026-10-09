"use client";

import {
  FormEvent,
  useState,
} from "react";

import Link from "next/link";

import {
  useRouter,
} from "next/navigation";

import {
  ApiError,
} from "@/lib/api";

import {
  useAuth,
} from "@/contexts/auth-context";


export default function LoginPage() {
  const router =
    useRouter();

  const {
    login,
  } = useAuth();


  const [
    username,
    setUsername,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    submitting,
    setSubmitting,
  ] = useState(false);


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setSubmitting(true);

    try {
      await login(
        username.trim(),
        password,
      );

      router.replace(
        "/dashboard",
      );
    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "登录失败，请稍后重试。",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }


  return (
    <main
      className="
        flex min-h-screen
        items-center
        justify-center
        bg-slate-950
        px-6
      "
    >
      <div
        className="
          w-full
          max-w-md
          rounded-2xl
          bg-white
          p-8
          shadow-2xl
        "
      >
        <div>
          <p
            className="
              text-sm
              font-semibold
              text-slate-500
            "
          >
            RESEARCH AGENT
          </p>

          <h1
            className="
              mt-2
              text-3xl
              font-bold
              text-slate-950
            "
          >
            登录
          </h1>

          <p
            className="
              mt-2
              text-sm
              text-slate-500
            "
          >
            登录你的智能科研工作台。
          </p>
        </div>


        <form
          onSubmit={
            handleSubmit
          }

          className="
            mt-8
            space-y-5
          "
        >
          <div>
            <label
              htmlFor="username"
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              用户名
            </label>

            <input
              id="username"

              value={
                username
              }

              onChange={
                (
                  event,
                ) =>
                  setUsername(
                    event.target.value,
                  )
              }

              required

              autoComplete="username"

              className="
                mt-2
                w-full
                rounded-lg
                border
                border-slate-300
                px-4
                py-3
                outline-none
                transition
                focus:border-slate-950
              "
            />
          </div>


          <div>
            <label
              htmlFor="password"
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              密码
            </label>

            <input
              id="password"

              type="password"

              value={
                password
              }

              onChange={
                (
                  event,
                ) =>
                  setPassword(
                    event.target.value,
                  )
              }

              required

              autoComplete="current-password"

              className="
                mt-2
                w-full
                rounded-lg
                border
                border-slate-300
                px-4
                py-3
                outline-none
                transition
                focus:border-slate-950
              "
            />
          </div>


          {error && (
            <div
              className="
                rounded-lg
                bg-red-50
                px-4
                py-3
                text-sm
                text-red-700
              "
            >
              {error}
            </div>
          )}


          <button
            type="submit"

            disabled={
              submitting
            }

            className="
              w-full
              rounded-lg
              bg-slate-950
              px-4
              py-3
              font-medium
              text-white
              transition
              hover:bg-slate-800
              disabled:cursor-not-allowed
              disabled:opacity-60
            "
          >
            {
              submitting
                ? "登录中..."
                : "登录"
            }
          </button>
        </form>


        <p
          className="
            mt-6
            text-center
            text-sm
            text-slate-500
          "
        >
          还没有账号？

          {" "}

          <Link
            href="/register"
            className="
              font-medium
              text-slate-950
              underline
            "
          >
            注册
          </Link>
        </p>
      </div>
    </main>
  );
}