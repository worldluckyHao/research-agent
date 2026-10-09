"use client";

import {
  useEffect,
  useState,
} from "react";

import Link from "next/link";

import {
  useParams,
} from "next/navigation";

import {
  getPaper,
} from "@/lib/papers-api";

import type {
  Paper,
} from "@/types/paper";


export default function PaperDetailPage() {
  const params =
    useParams();

  const paperId =
    Number(
      params.paperId,
    );


  const [
    paper,
    setPaper,
  ] = useState<Paper | null>(
    null,
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  useEffect(() => {
    async function load() {
      try {
        const result =
          await getPaper(
            paperId,
          );

        setPaper(
          result,
        );
      } catch {
        setError(
          "加载论文详情失败。",
        );
      } finally {
        setLoading(false);
      }
    }

    if (
      Number.isFinite(
        paperId,
      )
    ) {
      void load();
    }
  }, [
    paperId,
  ]);


  if (loading) {
    return (
      <div className="p-8">
        正在加载...
      </div>
    );
  }


  if (
    error ||
    !paper
  ) {
    return (
      <div className="p-8">
        {error || "论文不存在。"}
      </div>
    );
  }


  return (
    <div
      className="
        mx-auto
        max-w-5xl
        p-8
      "
    >
      <Link
        href="/papers"

        className="
          text-sm
          text-slate-500
          hover:text-slate-950
        "
      >
        ← 返回 Papers
      </Link>


      <article
        className="
          mt-6
          rounded-2xl
          border
          border-slate-200
          bg-white
          p-8
          shadow-sm
        "
      >
        <h1
          className="
            text-3xl
            font-bold
            leading-tight
            text-slate-950
          "
        >
          {paper.title}
        </h1>


        <p
          className="
            mt-4
            text-slate-600
          "
        >
          {
            paper.authors.join(
              ", ",
            )
          }
        </p>


        <div
          className="
            mt-4
            flex
            flex-wrap
            gap-3
            text-sm
            text-slate-500
          "
        >
          <span>
            Year: {paper.year}
          </span>

          {paper.source && (
            <span>
              Source: {paper.source}
            </span>
          )}

          {paper.doi && (
            <span>
              DOI: {paper.doi}
            </span>
          )}
        </div>


        {paper.abstract && (
          <section
            className="
              mt-8
              border-t
              border-slate-100
              pt-8
            "
          >
            <h2
              className="
                text-lg
                font-semibold
              "
            >
              Abstract
            </h2>

            <p
              className="
                mt-3
                whitespace-pre-line
                leading-7
                text-slate-600
              "
            >
              {paper.abstract}
            </p>
          </section>
        )}


        {paper.url && (
          <a
            href={paper.url}

            target="_blank"

            rel="noreferrer"

            className="
              mt-8
              inline-block
              rounded-lg
              bg-slate-950
              px-4
              py-2
              text-sm
              text-white
            "
          >
            打开原文
          </a>
        )}
      </article>
    </div>
  );
}