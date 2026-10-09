"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  ApiError,
} from "@/lib/api";

import {
  createPaper,
} from "@/lib/papers-api";

import type {
  Paper,
} from "@/types/paper";


export function CreatePaperForm({
  onCreated,
}: {
  onCreated: (
    paper: Paper,
  ) => void;
}) {
  const [
    title,
    setTitle,
  ] = useState("");

  const [
    authors,
    setAuthors,
  ] = useState("");

  const [
    year,
    setYear,
  ] = useState(
    String(
      new Date().getFullYear(),
    ),
  );

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
      const authorList =
        authors
          .split(",")
          .map(
            (author) =>
              author.trim(),
          )
          .filter(Boolean);

      if (
        authorList.length === 0
      ) {
        setError(
          "至少填写一位作者。",
        );

        return;
      }


      const paper =
        await createPaper({
          title:
            title.trim(),

          authors:
            authorList,

          year:
            Number(year),

          language:
            "en",
        });


      onCreated(
        paper,
      );


      setTitle("");
      setAuthors("");

    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "创建论文失败。",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }


  return (
    <form
      onSubmit={
        handleSubmit
      }

      className="
        rounded-2xl
        border
        border-slate-200
        bg-white
        p-6
        shadow-sm
      "
    >
      <h3
        className="
          text-lg
          font-semibold
          text-slate-950
        "
      >
        添加论文
      </h3>

      <p
        className="
          mt-1
          text-sm
          text-slate-500
        "
      >
        现在先支持手动添加；
        下一步接入 Crossref、arXiv 和 OpenAlex。
      </p>


      <div
        className="
          mt-5
          space-y-4
        "
      >
        <input
          value={title}

          onChange={
            (event) =>
              setTitle(
                event.target.value,
              )
          }

          placeholder="论文标题"

          required

          minLength={3}

          className="
            w-full
            rounded-lg
            border
            border-slate-300
            px-4
            py-3
            outline-none
            focus:border-slate-950
          "
        />


        <input
          value={authors}

          onChange={
            (event) =>
              setAuthors(
                event.target.value,
              )
          }

          placeholder="作者，以英文逗号分隔"

          required

          className="
            w-full
            rounded-lg
            border
            border-slate-300
            px-4
            py-3
            outline-none
            focus:border-slate-950
          "
        />


        <input
          value={year}

          onChange={
            (event) =>
              setYear(
                event.target.value,
              )
          }

          type="number"

          min="1900"

          max="2100"

          required

          className="
            w-full
            rounded-lg
            border
            border-slate-300
            px-4
            py-3
            outline-none
            focus:border-slate-950
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
          disabled={
            submitting
          }

          type="submit"

          className="
            rounded-lg
            bg-slate-950
            px-5
            py-3
            text-sm
            font-medium
            text-white
            disabled:opacity-60
          "
        >
          {
            submitting
              ? "创建中..."
              : "添加论文"
          }
        </button>
      </div>
    </form>
  );
}