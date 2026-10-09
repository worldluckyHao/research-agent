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
  useAuth,
} from "@/contexts/auth-context";

import {
  ApiError,
} from "@/lib/api";


export default function RegisterPage() {
  const router =
    useRouter();

  const {
    register,
  } = useAuth();


  const [
    username,
    setUsername,
  ] = useState("");

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    confirmPassword,
    setConfirmPassword,
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


    if (
      password !==
      confirmPassword
    ) {
      setError(
        "两次输入的密码不一致。",
      );

      return;
    }


    setSubmitting(true);

    try {
      await register({
        username:
          username.trim(),

        email:
          email.trim(),

        password,
      });

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
          "注册失败，请稍后重试。",
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
        py-10
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
          创建账号
        </h1>

        <form
          onSubmit={
            handleSubmit
          }

          className="
            mt-8
            space-y-4
          "
        >
          <input
            placeholder="用户名"

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
              w-full
              rounded-lg
              border
              border-slate-300
              px-4
              py-3
            "
          />


          <input
            placeholder="邮箱"

            type="email"

            value={
              email
            }

            onChange={
              (
                event,
              ) =>
                setEmail(
                  event.target.value,
                )
            }

            required

            autoComplete="email"

            className="
              w-full
              rounded-lg
              border
              border-slate-300
              px-4
              py-3
            "
          />


          <input
            placeholder="密码"

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

            autoComplete="new-password"

            className="
              w-full
              rounded-lg
              border
              border-slate-300
              px-4
              py-3
            "
          />


          <input
            placeholder="再次输入密码"

            type="password"

            value={
              confirmPassword
            }

            onChange={
              (
                event,
              ) =>
                setConfirmPassword(
                  event.target.value,
                )
            }

            required

            autoComplete="new-password"

            className="
              w-full
              rounded-lg
              border
              border-slate-300
              px-4
              py-3
            "
          />


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
              disabled:opacity-60
            "
          >
            {
              submitting
                ? "注册中..."
                : "创建账号"
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
          已有账号？

          {" "}

          <Link
            href="/login"
            className="
              font-medium
              text-slate-950
              underline
            "
          >
            登录
          </Link>
        </p>
      </div>
    </main>
  );
}