"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  ApiError,
} from "@/lib/api";

import {
  askPaperDocument,
} from "@/lib/rag-api";

import type {
  RAGAnswerResponse,
} from "@/types/rag";


interface RAGChatProps {
  paperId: number;

  documentId: number;

  enabled: boolean;
}


// ============================================================
// Citation Card
// ============================================================

function CitationCard({
  sourceId,
  chunkIndex,
  startPage,
  endPage,
}: {
  sourceId: string;

  chunkIndex: number;

  startPage: number;

  endPage: number;
}) {
  return (
    <div
      className="
        rounded-xl
        border
        border-slate-200
        bg-slate-50
        p-4
      "
    >
      <div
        className="
          flex
          items-center
          justify-between
          gap-3
        "
      >
        <span
          className="
            rounded-full
            bg-slate-950
            px-3
            py-1
            text-xs
            font-semibold
            text-white
          "
        >
          {sourceId}
        </span>

        <span
          className="
            text-xs
            text-slate-400
          "
        >
          Chunk #{chunkIndex}
        </span>
      </div>


      <p
        className="
          mt-3
          text-sm
          text-slate-600
        "
      >
        Page{" "}
        {startPage}

        {
          endPage !==
          startPage
            ? ` - ${endPage}`
            : ""
        }
      </p>
    </div>
  );
}


// ============================================================
// RAG Chat
// ============================================================

export function RAGChat({
  paperId,
  documentId,
  enabled,
}: RAGChatProps) {
  const [
    question,
    setQuestion,
  ] = useState("");

  const [
    topK,
    setTopK,
  ] = useState(5);

  const [
    useReranker,
    setUseReranker,
  ] = useState(true);

  const [
    result,
    setResult,
  ] = useState<
    RAGAnswerResponse
    | null
  >(
    null,
  );

  const [
    asking,
    setAsking,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");


  // ==========================================================
  // Submit
  // ==========================================================

  async function handleSubmit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");


    const trimmedQuestion =
      question.trim();


    if (
      trimmedQuestion.length <
      2
    ) {
      setError(
        "问题至少需要 2 个字符。",
      );

      return;
    }


    setAsking(
      true,
    );


    try {
      const response =
        await askPaperDocument(
          paperId,
          documentId,
          {
            question:
              trimmedQuestion,

            top_k:
              topK,

            use_reranker:
              useReranker,
          },
        );


      setResult(
        response,
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
          "RAG 问答失败。",
        );
      }
    } finally {
      setAsking(
        false,
      );
    }
  }


  return (
    <section
      className="
        mt-8
        border-t
        border-slate-200
        pt-8
      "
    >
      {/* =================================================== */}
      {/* Header */}
      {/* =================================================== */}

      <div>
        <p
          className="
            text-xs
            font-medium
            uppercase
            tracking-wide
            text-slate-400
          "
        >
          CITATION-AWARE RAG
        </p>


        <h3
          className="
            mt-1
            text-xl
            font-semibold
            text-slate-950
          "
        >
          Ask This Paper
        </h3>


        <p
          className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          "
        >
          基于当前 PDF
          的 Hybrid Retrieval
          生成带引用的回答。
        </p>
      </div>


      {!enabled && (
        <div
          className="
            mt-5
            rounded-lg
            bg-amber-50
            px-4
            py-3
            text-sm
            text-amber-700
          "
        >
          请先完成 Document
          Embedding，再使用 RAG。
        </div>
      )}


      {/* =================================================== */}
      {/* Question */}
      {/* =================================================== */}

      <form
        onSubmit={
          handleSubmit
        }

        className="
          mt-6
          space-y-4
        "
      >
        <textarea
          value={
            question
          }

          onChange={
            (event) =>
              setQuestion(
                event.target.value,
              )
          }

          minLength={2}

          maxLength={1000}

          rows={4}

          disabled={
            !enabled ||
            asking
          }

          placeholder={
            "例如：What is the main architecture proposed " +
            "in this paper and what problem does it solve?"
          }

          className="
            w-full
            resize-none
            rounded-xl
            border
            border-slate-300
            px-4
            py-3
            leading-6
            outline-none
            focus:border-slate-950
            disabled:bg-slate-100
          "
        />


        <div
          className="
            flex
            flex-wrap
            items-center
            gap-5
          "
        >
          <label
            className="
              text-sm
              text-slate-600
            "
          >
            Top K{" "}

            <select
              value={
                topK
              }

              onChange={
                (event) =>
                  setTopK(
                    Number(
                      event.target.value,
                    ),
                  )
              }

              disabled={
                asking
              }

              className="
                ml-2
                rounded-lg
                border
                border-slate-300
                px-3
                py-2
              "
            >
              <option value={3}>
                3
              </option>

              <option value={5}>
                5
              </option>

              <option value={8}>
                8
              </option>

              <option value={10}>
                10
              </option>
            </select>
          </label>


          <label
            className="
              flex
              items-center
              gap-2
              text-sm
              text-slate-600
            "
          >
            <input
              type="checkbox"

              checked={
                useReranker
              }

              onChange={
                (event) =>
                  setUseReranker(
                    event.target.checked,
                  )
              }

              disabled={
                asking
              }
            />

            Use Reranker
          </label>


          <button
            type="submit"

            disabled={
              !enabled ||
              asking
            }

            className="
              ml-auto
              rounded-lg
              bg-slate-950
              px-6
              py-3
              text-sm
              font-medium
              text-white
              disabled:cursor-not-allowed
              disabled:opacity-50
            "
          >
            {
              asking
                ? "Thinking..."
                : "Ask Paper"
            }
          </button>
        </div>
      </form>


      {asking && (
        <div
          className="
            mt-5
            rounded-lg
            bg-blue-50
            px-4
            py-3
            text-sm
            text-blue-700
          "
        >
          正在执行 Hybrid Retrieval
          → Evidence Context
          → LLM
          → Citation Validation...
        </div>
      )}


      {error && (
        <div
          className="
            mt-5
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


      {/* =================================================== */}
      {/* Answer */}
      {/* =================================================== */}

      {result && (
        <div
          className="
            mt-8
            space-y-6
          "
        >
          <article
            className="
              rounded-2xl
              border
              border-slate-200
              bg-slate-50
              p-6
            "
          >
            <div
              className="
                flex
                flex-wrap
                items-center
                justify-between
                gap-3
              "
            >
              <h4
                className="
                  text-lg
                  font-semibold
                  text-slate-950
                "
              >
                Answer
              </h4>


              <span
                className={
                  result.grounded
                    ? (
                      "rounded-full bg-emerald-100 " +
                      "px-3 py-1 text-xs font-medium " +
                      "text-emerald-700"
                    )
                    : (
                      "rounded-full bg-amber-100 " +
                      "px-3 py-1 text-xs font-medium " +
                      "text-amber-700"
                    )
                }
              >
                {
                  result.grounded
                    ? "Grounded ✓"
                    : "Not Fully Grounded"
                }
              </span>
            </div>


            <p
              className="
                mt-5
                whitespace-pre-wrap
                text-sm
                leading-7
                text-slate-700
              "
            >
              {result.answer}
            </p>
          </article>


          {/* ================================================= */}
          {/* Runtime Metadata */}
          {/* ================================================= */}

          <div
            className="
              grid
              gap-3
              sm:grid-cols-3
            "
          >
            <InfoCard
              label="Evidence"
              value={
                String(
                  result
                    .retrieval_count,
                )
              }
            />

            <InfoCard
              label="Citations"
              value={
                String(
                  result
                    .citations
                    .length,
                )
              }
            />

            <InfoCard
              label="Invalid Citations"
              value={
                String(
                  result
                    .invalid_citations
                    .length,
                )
              }
            />
          </div>


          {/* ================================================= */}
          {/* Citations */}
          {/* ================================================= */}

          <section>
            <h4
              className="
                font-semibold
                text-slate-950
              "
            >
              Citations
            </h4>


            {result.citations.length ===
            0 ? (
              <div
                className="
                  mt-3
                  rounded-lg
                  bg-amber-50
                  p-4
                  text-sm
                  text-amber-700
                "
              >
                本次回答没有有效 Citation。
              </div>
            ) : (
              <div
                className="
                  mt-3
                  grid
                  gap-3
                  sm:grid-cols-2
                  xl:grid-cols-3
                "
              >
                {result.citations.map(
                  (
                    citation,
                  ) => (
                    <CitationCard
                      key={
                        (
                          citation
                            .source_id +
                          ":" +
                          citation
                            .chunk_id
                        )
                      }

                      sourceId={
                        citation
                          .source_id
                      }

                      chunkIndex={
                        citation
                          .chunk_index
                      }

                      startPage={
                        citation
                          .start_page
                      }

                      endPage={
                        citation
                          .end_page
                      }
                    />
                  ),
                )}
              </div>
            )}
          </section>


          {/* ================================================= */}
          {/* Invalid Citations */}
          {/* ================================================= */}

          {result
            .invalid_citations
            .length > 0 && (
            <section
              className="
                rounded-xl
                border
                border-red-200
                bg-red-50
                p-5
              "
            >
              <h4
                className="
                  font-semibold
                  text-red-800
                "
              >
                Invalid Citations
              </h4>


              <div
                className="
                  mt-3
                  flex
                  flex-wrap
                  gap-2
                "
              >
                {
                  result
                    .invalid_citations
                    .map(
                      (
                        citation,
                      ) => (
                        <span
                          key={
                            citation
                          }

                          className="
                            rounded-full
                            bg-white
                            px-3
                            py-1
                            text-xs
                            text-red-700
                          "
                        >
                          {
                            citation
                          }
                        </span>
                      ),
                    )
                }
              </div>
            </section>
          )}


          {/* ================================================= */}
          {/* Model + Prompt */}
          {/* ================================================= */}

          <section
            className="
              rounded-xl
              border
              border-slate-200
              bg-white
              p-5
            "
          >
            <h4
              className="
                font-semibold
                text-slate-950
              "
            >
              Generation Metadata
            </h4>


            <div
              className="
                mt-4
                grid
                gap-4
                text-sm
                text-slate-600
                sm:grid-cols-2
              "
            >
              <div>
                <p
                  className="
                    text-xs
                    text-slate-400
                  "
                >
                  Model
                </p>

                <p
                  className="
                    mt-1
                  "
                >
                  {
                    result.model
                      ? (
                        `${result.model.provider}` +
                        " / " +
                        `${result.model.model_name}`
                      )
                      : "-"
                  }
                </p>
              </div>


              <div>
                <p
                  className="
                    text-xs
                    text-slate-400
                  "
                >
                  Prompt Version
                </p>

                <p
                  className="
                    mt-1
                  "
                >
                  {
                    result.prompt
                      ? (
                        `System v${result.prompt.system_prompt_version}` +
                        " · " +
                        `User v${result.prompt.user_prompt_version}`
                      )
                      : "-"
                  }
                </p>
              </div>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}


// ============================================================
// Info Card
// ============================================================

function InfoCard({
  label,
  value,
}: {
  label: string;

  value: string;
}) {
  return (
    <div
      className="
        rounded-xl
        bg-slate-50
        px-4
        py-3
      "
    >
      <p
        className="
          text-xs
          text-slate-400
        "
      >
        {label}
      </p>

      <p
        className="
          mt-1
          text-xl
          font-semibold
          text-slate-950
        "
      >
        {value}
      </p>
    </div>
  );
}