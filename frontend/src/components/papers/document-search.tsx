"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  ApiError,
} from "@/lib/api";

import {
  hybridSearchDocument,
  semanticSearchDocument,
} from "@/lib/retrieval-api";

import type {
  HybridSearchResponse,
  RetrievalMode,
  SemanticSearchResponse,
} from "@/types/retrieval";


interface DocumentSearchProps {
  paperId: number;

  documentId: number;

  enabled: boolean;
}


// ============================================================
// Score
// ============================================================

function formatScore(
  value:
    | number
    | null
    | undefined,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "-";
  }

  return value.toFixed(
    4,
  );
}


// ============================================================
// Component
// ============================================================

export function DocumentSearch({
  paperId,
  documentId,
  enabled,
}: DocumentSearchProps) {
  const [
    mode,
    setMode,
  ] = useState<RetrievalMode>(
    "hybrid",
  );

  const [
    query,
    setQuery,
  ] = useState("");

  const [
    topK,
    setTopK,
  ] = useState(5);

  const [
    minScore,
    setMinScore,
  ] = useState(0);

  const [
    useReranker,
    setUseReranker,
  ] = useState(true);

  const [
    semanticResult,
    setSemanticResult,
  ] = useState<
    SemanticSearchResponse
    | null
  >(
    null,
  );

  const [
    hybridResult,
    setHybridResult,
  ] = useState<
    HybridSearchResponse
    | null
  >(
    null,
  );

  const [
    searching,
    setSearching,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");


  async function handleSubmit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");


    const trimmedQuery =
      query.trim();


    if (
      trimmedQuery.length < 2
    ) {
      setError(
        "检索问题至少需要 2 个字符。",
      );

      return;
    }


    setSearching(
      true,
    );


    try {
      if (
        mode ===
        "semantic"
      ) {
        const result =
          await semanticSearchDocument(
            paperId,
            documentId,
            {
              query:
                trimmedQuery,

              top_k:
                topK,

              min_score:
                minScore,
            },
          );


        setSemanticResult(
          result,
        );

        setHybridResult(
          null,
        );

      } else {
        const result =
          await hybridSearchDocument(
            paperId,
            documentId,
            {
              query:
                trimmedQuery,

              top_k:
                topK,

              use_reranker:
                useReranker,
            },
          );


        setHybridResult(
          result,
        );

        setSemanticResult(
          null,
        );
      }

    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "Document Search 失败。",
        );
      }
    } finally {
      setSearching(
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
          RETRIEVAL
        </p>

        <h3
          className="
            mt-1
            text-xl
            font-semibold
            text-slate-950
          "
        >
          Document Search
        </h3>

        <p
          className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          "
        >
          在当前 PDF 的 Chunk
          中执行语义检索或混合检索。
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
          Embedding，再执行检索。
        </div>
      )}


      <form
        onSubmit={
          handleSubmit
        }

        className="
          mt-6
          space-y-5
        "
      >
        {/* ================================================= */}
        {/* Search Mode */}
        {/* ================================================= */}

        <div
          className="
            flex
            flex-wrap
            gap-2
          "
        >
          <button
            type="button"

            onClick={
              () =>
                setMode(
                  "semantic",
                )
            }

            className={
              (
                mode ===
                "semantic"
              )
                ? (
                  "rounded-lg bg-slate-950 " +
                  "px-4 py-2 text-sm text-white"
                )
                : (
                  "rounded-lg border border-slate-300 " +
                  "px-4 py-2 text-sm text-slate-700"
                )
            }
          >
            Semantic
          </button>


          <button
            type="button"

            onClick={
              () =>
                setMode(
                  "hybrid",
                )
            }

            className={
              (
                mode ===
                "hybrid"
              )
                ? (
                  "rounded-lg bg-slate-950 " +
                  "px-4 py-2 text-sm text-white"
                )
                : (
                  "rounded-lg border border-slate-300 " +
                  "px-4 py-2 text-sm text-slate-700"
                )
            }
          >
            Hybrid
          </button>
        </div>


        {/* ================================================= */}
        {/* Query */}
        {/* ================================================= */}

        <div
          className="
            flex
            gap-3
          "
        >
          <input
            value={
              query
            }

            onChange={
              (event) =>
                setQuery(
                  event.target.value,
                )
            }

            minLength={2}

            maxLength={1000}

            placeholder="例如：What method does this paper use for precipitation nowcasting?"

            disabled={
              !enabled ||
              searching
            }

            className="
              min-w-0
              flex-1
              rounded-lg
              border
              border-slate-300
              px-4
              py-3
              outline-none
              focus:border-slate-950
              disabled:bg-slate-100
            "
          />


          <button
            type="submit"

            disabled={
              !enabled ||
              searching
            }

            className="
              rounded-lg
              bg-slate-950
              px-6
              py-3
              text-sm
              font-medium
              text-white
              disabled:opacity-50
            "
          >
            {
              searching
                ? "Searching..."
                : "Search"
            }
          </button>
        </div>


        {/* ================================================= */}
        {/* Options */}
        {/* ================================================= */}

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

              <option value={10}>
                10
              </option>

              <option value={20}>
                20
              </option>
            </select>
          </label>


          {mode ===
            "semantic" && (
            <label
              className="
                text-sm
                text-slate-600
              "
            >
              Min Score{" "}

              <input
                type="number"

                min="-1"

                max="1"

                step="0.05"

                value={
                  minScore
                }

                onChange={
                  (event) =>
                    setMinScore(
                      Number(
                        event.target.value,
                      ),
                    )
                }

                className="
                  ml-2
                  w-24
                  rounded-lg
                  border
                  border-slate-300
                  px-3
                  py-2
                "
              />
            </label>
          )}


          {mode ===
            "hybrid" && (
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
              />

              Use Reranker
            </label>
          )}
        </div>
      </form>


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
      {/* Semantic Result */}
      {/* =================================================== */}

      {semanticResult && (
        <div
          className="
            mt-8
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
            <div>
              <h4
                className="
                  font-semibold
                  text-slate-950
                "
              >
                Semantic Results
              </h4>

              <p
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                {
                  semanticResult
                    .returned_count
                }{" "}
                chunks returned
              </p>
            </div>


            <div
              className="
                text-right
                text-xs
                text-slate-500
              "
            >
              <p>
                {
                  semanticResult
                    .model
                    .model_name
                }
              </p>

              <p>
                {
                  semanticResult
                    .model
                    .dimension
                }
                -dim
              </p>
            </div>
          </div>


          <div
            className="
              mt-4
              space-y-3
            "
          >
            {semanticResult.items.map(
              (
                item,
                index,
              ) => (
                <article
                  key={
                    item.chunk_id
                  }

                  className="
                    rounded-xl
                    border
                    border-slate-200
                    bg-slate-50
                    p-5
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
                    <p
                      className="
                        text-sm
                        font-semibold
                        text-slate-800
                      "
                    >
                      #
                      {
                        index + 1
                      }
                      {" · "}
                      Chunk{" "}
                      {
                        item.chunk_index
                      }
                    </p>


                    <span
                      className="
                        rounded-full
                        bg-white
                        px-3
                        py-1
                        text-xs
                        text-slate-600
                      "
                    >
                      Similarity{" "}
                      {
                        formatScore(
                          item
                            .similarity_score,
                        )
                      }
                    </span>
                  </div>


                  <p
                    className="
                      mt-4
                      whitespace-pre-wrap
                      text-sm
                      leading-6
                      text-slate-700
                    "
                  >
                    {item.content}
                  </p>


                  <div
                    className="
                      mt-4
                      flex
                      flex-wrap
                      gap-4
                      text-xs
                      text-slate-500
                    "
                  >
                    <span>
                      Pages{" "}
                      {
                        item.start_page
                      }
                      -
                      {
                        item.end_page
                      }
                    </span>

                    <span>
                      {
                        item.token_count
                      }{" "}
                      tokens
                    </span>

                    <span>
                      Distance{" "}
                      {
                        formatScore(
                          item
                            .cosine_distance,
                        )
                      }
                    </span>
                  </div>
                </article>
              ),
            )}
          </div>
        </div>
      )}


      {/* =================================================== */}
      {/* Hybrid Result */}
      {/* =================================================== */}

      {hybridResult && (
        <div
          className="
            mt-8
          "
        >
          <div>
            <h4
              className="
                font-semibold
                text-slate-950
              "
            >
              Hybrid Results
            </h4>


            <div
              className="
                mt-3
                grid
                gap-3
                sm:grid-cols-4
              "
            >
              <ResultMetric
                label="Semantic"
                value={
                  hybridResult
                    .semantic_candidate_count
                }
              />

              <ResultMetric
                label="Lexical"
                value={
                  hybridResult
                    .lexical_candidate_count
                }
              />

              <ResultMetric
                label="Fused"
                value={
                  hybridResult
                    .fused_candidate_count
                }
              />

              <ResultMetric
                label="Returned"
                value={
                  hybridResult
                    .returned_count
                }
              />
            </div>


            <p
              className="
                mt-3
                text-xs
                text-slate-500
              "
            >
              Reranker:{" "}
              {
                hybridResult
                  .reranker_used
                  ? "Enabled"
                  : "Disabled"
              }
            </p>
          </div>


          <div
            className="
              mt-4
              space-y-3
            "
          >
            {hybridResult.items.map(
              (
                item,
                index,
              ) => (
                <article
                  key={
                    item.chunk_id
                  }

                  className="
                    rounded-xl
                    border
                    border-slate-200
                    bg-slate-50
                    p-5
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
                    <p
                      className="
                        text-sm
                        font-semibold
                        text-slate-800
                      "
                    >
                      #
                      {
                        index + 1
                      }
                      {" · "}
                      Chunk{" "}
                      {
                        item.chunk_index
                      }
                    </p>


                    <span
                      className="
                        rounded-full
                        bg-white
                        px-3
                        py-1
                        text-xs
                        text-slate-600
                      "
                    >
                      RRF{" "}
                      {
                        formatScore(
                          item
                            .rrf_score,
                        )
                      }
                    </span>
                  </div>


                  <p
                    className="
                      mt-4
                      whitespace-pre-wrap
                      text-sm
                      leading-6
                      text-slate-700
                    "
                  >
                    {item.content}
                  </p>


                  <div
                    className="
                      mt-4
                      grid
                      gap-2
                      text-xs
                      text-slate-500
                      sm:grid-cols-2
                      xl:grid-cols-4
                    "
                  >
                    <span>
                      Semantic:{" "}
                      {
                        formatScore(
                          item
                            .semantic_score,
                        )
                      }
                    </span>

                    <span>
                      Lexical:{" "}
                      {
                        formatScore(
                          item
                            .lexical_score,
                        )
                      }
                    </span>

                    <span>
                      RRF:{" "}
                      {
                        formatScore(
                          item
                            .rrf_score,
                        )
                      }
                    </span>

                    <span>
                      Rerank:{" "}
                      {
                        formatScore(
                          item
                            .rerank_score,
                        )
                      }
                    </span>
                  </div>


                  <div
                    className="
                      mt-3
                      flex
                      flex-wrap
                      gap-4
                      text-xs
                      text-slate-400
                    "
                  >
                    <span>
                      Pages{" "}
                      {
                        item.start_page
                      }
                      -
                      {
                        item.end_page
                      }
                    </span>

                    <span>
                      {
                        item.token_count
                      }{" "}
                      tokens
                    </span>
                  </div>
                </article>
              ),
            )}
          </div>
        </div>
      )}
    </section>
  );
}


// ============================================================
// Metric
// ============================================================

function ResultMetric({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div
      className="
        rounded-lg
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
          text-lg
          font-semibold
          text-slate-950
        "
      >
        {value}
      </p>
    </div>
  );
}