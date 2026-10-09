"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  CreatePaperForm,
} from "@/components/papers/create-paper-form";

import {
  ExternalPaperSearch,
} from "@/components/papers/external-paper-search";

import {
  PaperCard,
} from "@/components/papers/paper-card";

import {
  ApiError,
} from "@/lib/api";

import {
  listPapers,
} from "@/lib/papers-api";

import type {
  Paper,
} from "@/types/paper";


export default function PapersPage() {
  const [
    papers,
    setPapers,
  ] = useState<Paper[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  const loadPapers =
    useCallback(
      async () => {
        setError("");

        try {
          const result =
            await listPapers({
              page: 1,

              page_size: 100,

              sort_by:
                "created_at",

              sort_order:
                "desc",
            });


          setPapers(
            result,
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
              "加载论文失败。",
            );
          }
        } finally {
          setLoading(false);
        }
      },
      [],
    );


  useEffect(() => {
    void loadPapers();
  }, [
    loadPapers,
  ]);


  return (
    <div
      className="
        mx-auto
        max-w-7xl
        p-8
      "
    >
      <header>
        <p
          className="
            text-sm
            font-medium
            text-slate-500
          "
        >
          PAPER LIBRARY
        </p>

        <h1
          className="
            mt-1
            text-3xl
            font-bold
            text-slate-950
          "
        >
          Papers
        </h1>

        <p
          className="
            mt-2
            text-slate-600
          "
        >
          管理本地论文库，
          并从多个学术数据源搜索和导入论文。
        </p>
      </header>


      <section
        className="
          mt-8
        "
      >
        <div
          className="
            flex
            items-end
            justify-between
            gap-4
          "
        >
          <div>
            <h2
              className="
                text-2xl
                font-semibold
                text-slate-950
              "
            >
              My Library
            </h2>

            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              当前共显示 {
                papers.length
              } 篇论文
            </p>
          </div>


          <button
            type="button"

            onClick={
              () =>
                void loadPapers()
            }

            className="
              rounded-lg
              border
              border-slate-300
              px-4
              py-2
              text-sm
              text-slate-700
              hover:bg-slate-50
            "
          >
            Refresh
          </button>
        </div>


        <div
          className="
            mt-5
            grid
            gap-8
            xl:grid-cols-[360px_1fr]
          "
        >
          <CreatePaperForm
            onCreated={
              (paper) =>
                setPapers(
                  (current) => [
                    paper,
                    ...current,
                  ],
                )
            }
          />


          <div>
            {loading && (
              <p
                className="
                  text-sm
                  text-slate-500
                "
              >
                正在加载论文...
              </p>
            )}


            {error && (
              <div
                className="
                  rounded-xl
                  bg-red-50
                  p-4
                  text-sm
                  text-red-700
                "
              >
                {error}
              </div>
            )}


            {!loading &&
              !error &&
              papers.length ===
                0 && (
                <div
                  className="
                    rounded-2xl
                    border
                    border-dashed
                    border-slate-300
                    bg-white
                    p-12
                    text-center
                    text-slate-500
                  "
                >
                  当前还没有论文。
                </div>
              )}


            <div
              className="
                grid
                gap-4
              "
            >
              {papers.map(
                (paper) => (
                  <PaperCard
                    key={
                      paper.id
                    }

                    paper={
                      paper
                    }
                  />
                ),
              )}
            </div>
          </div>
        </div>
      </section>


      <ExternalPaperSearch
        onImported={
          loadPapers
        }
      />
    </div>
  );
}