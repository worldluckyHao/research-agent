"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  ExternalPaperCard,
} from "@/components/papers/external-paper-card";

import {
  ApiError,
} from "@/lib/api";

import {
  createPaperImportJob,
  searchExternalPapers,
  waitForPaperImport,
} from "@/lib/external-papers-api";

import type {
  MultiSourcePaperSearchResponse,
  PaperProvider,
  PaperSearchSort,
  UnifiedPaperMetadata,
} from "@/types/external-paper";


interface ExternalPaperSearchProps {
  onImported: () =>
    void | Promise<void>;
}


const providerOptions: {
  value: PaperProvider;
  label: string;
}[] = [
  {
    value: "openalex",
    label: "OpenAlex",
  },
  {
    value: "arxiv",
    label: "arXiv",
  },
  {
    value: "crossref",
    label: "Crossref",
  },
];


function getPaperKey(
  paper: UnifiedPaperMetadata,
): string {
  return (
    `${paper.provider}:` +
    paper.provider_id
  );
}


export function ExternalPaperSearch({
  onImported,
}: ExternalPaperSearchProps) {
  const [
    query,
    setQuery,
  ] = useState("");

  const [
    providers,
    setProviders,
  ] = useState<
    PaperProvider[]
  >([
    "openalex",
    "arxiv",
    "crossref",
  ]);

  const [
    sort,
    setSort,
  ] = useState<
    PaperSearchSort
  >(
    "relevance",
  );

  const [
    result,
    setResult,
  ] = useState<
    MultiSourcePaperSearchResponse
    | null
  >(
    null,
  );

  const [
    searching,
    setSearching,
  ] = useState(false);

  const [
    importingKeys,
    setImportingKeys,
  ] = useState<
    Set<string>
  >(
    new Set(),
  );

  const [
    importedKeys,
    setImportedKeys,
  ] = useState<
    Set<string>
  >(
    new Set(),
  );

  const [
    error,
    setError,
  ] = useState("");

  const [
    message,
    setMessage,
  ] = useState("");


  function toggleProvider(
    provider: PaperProvider,
  ) {
    setProviders(
      (current) => {
        if (
          current.includes(
            provider,
          )
        ) {
          return current.filter(
            (item) =>
              item !==
              provider,
          );
        }

        return [
          ...current,
          provider,
        ];
      },
    );
  }


  async function handleSearch(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setMessage("");


    const trimmedQuery =
      query.trim();


    if (
      trimmedQuery.length < 2
    ) {
      setError(
        "搜索关键词至少需要 2 个字符。",
      );

      return;
    }


    if (
      providers.length === 0
    ) {
      setError(
        "至少选择一个数据源。",
      );

      return;
    }


    setSearching(true);


    try {
      const searchResult =
        await searchExternalPapers({
          query:
            trimmedQuery,

          providers,

          limit:
            10,

          sort,
        });


      setResult(
        searchResult,
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
          "外部论文搜索失败。",
        );
      }
    } finally {
      setSearching(false);
    }
  }


  async function handleImport(
    paper:
      UnifiedPaperMetadata,
  ) {
    const key =
      getPaperKey(
        paper,
      );


    setError("");
    setMessage("");


    setImportingKeys(
      (current) =>
        new Set(
          current,
        ).add(
          key,
        ),
    );


    try {
      const job =
        await createPaperImportJob({
          paper,
        });


      const completedJob =
        await waitForPaperImport(
          job.id,
        );


      setImportedKeys(
        (current) =>
          new Set(
            current,
          ).add(
            key,
          ),
      );


      setMessage(
        completedJob.paper_id
          ? (
              "论文导入成功，" +
              `Paper ID: ${completedJob.paper_id}`
            )
          : "论文导入成功。",
      );


      await onImported();

    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else if (
        err instanceof Error
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "论文导入失败。",
        );
      }
    } finally {
      setImportingKeys(
        (current) => {
          const next =
            new Set(
              current,
            );

          next.delete(
            key,
          );

          return next;
        },
      );
    }
  }


  return (
    <section
      className="
        mt-10
      "
    >
      <div
        className="
          rounded-2xl
          border
          border-slate-200
          bg-white
          p-6
          shadow-sm
        "
      >
        <p
          className="
            text-sm
            font-medium
            text-slate-500
          "
        >
          MULTI-SOURCE SEARCH
        </p>

        <h2
          className="
            mt-1
            text-2xl
            font-bold
            text-slate-950
          "
        >
          External Paper Search
        </h2>

        <p
          className="
            mt-2
            text-sm
            leading-6
            text-slate-600
          "
        >
          同时检索 OpenAlex、
          arXiv 和 Crossref，
          后端负责统一元数据、
          去重和融合。
        </p>


        <form
          onSubmit={
            handleSearch
          }

          className="
            mt-6
            space-y-5
          "
        >
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

              placeholder="例如：multimodal precipitation forecasting"

              minLength={2}

              maxLength={300}

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
              "
            />


            <button
              type="submit"

              disabled={
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


          <div
            className="
              flex
              flex-wrap
              items-center
              gap-4
            "
          >
            {providerOptions.map(
              (provider) => (
                <label
                  key={
                    provider.value
                  }

                  className="
                    flex
                    cursor-pointer
                    items-center
                    gap-2
                    text-sm
                    text-slate-700
                  "
                >
                  <input
                    type="checkbox"

                    checked={
                      providers.includes(
                        provider.value,
                      )
                    }

                    onChange={
                      () =>
                        toggleProvider(
                          provider.value,
                        )
                    }
                  />

                  {
                    provider.label
                  }
                </label>
              ),
            )}


            <select
              value={
                sort
              }

              onChange={
                (event) =>
                  setSort(event.target.value as PaperSearchSort)
              }

              className="
                ml-auto
                rounded-lg
                border
                border-slate-300
                px-3
                py-2
                text-sm
              "
            >
              <option
                value="relevance"
              >
                Relevance
              </option>

              <option
                value="newest"
              >
                Newest
              </option>

              <option
                value="cited"
              >
                Most Cited
              </option>
            </select>
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


        {message && (
          <div
            className="
              mt-5
              rounded-lg
              bg-emerald-50
              px-4
              py-3
              text-sm
              text-emerald-700
            "
          >
            {message}
          </div>
        )}
      </div>


      {result && (
        <div
          className="
            mt-6
          "
        >
          <div
            className="
              mb-4
              flex
              flex-wrap
              items-center
              justify-between
              gap-3
            "
          >
            <div>
              <h3
                className="
                  text-lg
                  font-semibold
                  text-slate-950
                "
              >
                Search Results
              </h3>

              <p
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                {
                  result.candidate_count
                }{" "}
                candidates
                {" · "}
                {
                  result.unique_count
                }{" "}
                unique papers
              </p>
            </div>


            <p
              className="
                text-sm
                text-slate-500
              "
            >
              Providers:{" "}
              {
                result.providers.join(
                  ", ",
                )
              }
            </p>
          </div>


          {result.failed_providers &&
            result.failed_providers.length >
              0 && (
              <div
                className="
                  mb-4
                  rounded-lg
                  bg-amber-50
                  px-4
                  py-3
                  text-sm
                  text-amber-700
                "
              >
                部分数据源搜索失败：
                {" "}
                {
                  result.failed_providers.join(
                    ", ",
                  )
                }
              </div>
            )}


          {result.items.length ===
          0 ? (
            <div
              className="
                rounded-2xl
                border
                border-dashed
                border-slate-300
                bg-white
                p-10
                text-center
                text-slate-500
              "
            >
              没有找到匹配的论文。
            </div>
          ) : (
            <div
              className="
                space-y-4
              "
            >
              {result.items.map(
                (paper) => {
                  const key =
                    getPaperKey(
                      paper,
                    );


                  return (
                    <ExternalPaperCard
                      key={
                        key
                      }

                      paper={
                        paper
                      }

                      importing={
                        importingKeys.has(
                          key,
                        )
                      }

                      imported={
                        importedKeys.has(
                          key,
                        )
                      }

                      onImport={
                        () =>
                          handleImport(
                            paper,
                          )
                      }
                    />
                  );
                },
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}