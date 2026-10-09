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
  ApiError,
} from "@/lib/api";

import {
  listPapers,
} from "@/lib/papers-api";

import {
  addPaperToProject,
  getProject,
  listProjectPapers,
  removePaperFromProject,
} from "@/lib/projects-api";

import type {
  Paper,
} from "@/types/paper";

import type {
  Project,
  ProjectPaper,
} from "@/types/project";


export default function ProjectDetailPage() {
  const params =
    useParams();

  const projectId =
    Number(
      params.projectId,
    );


  const [
    project,
    setProject,
  ] = useState<Project | null>(
    null,
  );

  const [
    projectPapers,
    setProjectPapers,
  ] = useState<ProjectPaper[]>(
    [],
  );

  const [
    allPapers,
    setAllPapers,
  ] = useState<Paper[]>(
    [],
  );

  const [
    selectedPaperId,
    setSelectedPaperId,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    actionLoading,
    setActionLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");


  async function reloadProjectPapers() {
    const result =
      await listProjectPapers(
        projectId,
      );

    setProjectPapers(
      result,
    );
  }


  useEffect(() => {
    async function load() {
      try {
        const [
          projectResult,
          projectPaperResult,
          allPaperResult,
        ] = await Promise.all([
          getProject(
            projectId,
          ),

          listProjectPapers(
            projectId,
          ),

          listPapers(),
        ]);


        setProject(
          projectResult,
        );

        setProjectPapers(
          projectPaperResult,
        );

        setAllPapers(
          allPaperResult,
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
            "加载项目失败。",
          );
        }
      } finally {
        setLoading(false);
      }
    }


    if (
      Number.isFinite(
        projectId,
      )
    ) {
      void load();
    }
  }, [
    projectId,
  ]);


  async function handleAddPaper() {
    if (
      !selectedPaperId
    ) {
      return;
    }


    setError("");
    setActionLoading(true);


    try {
      await addPaperToProject(
        projectId,
        Number(
          selectedPaperId,
        ),
      );


      await reloadProjectPapers();

      setSelectedPaperId("");

    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "添加论文失败。",
        );
      }
    } finally {
      setActionLoading(false);
    }
  }


  async function handleRemovePaper(
    paperId: number,
  ) {
    setError("");
    setActionLoading(true);


    try {
      await removePaperFromProject(
        projectId,
        paperId,
      );


      await reloadProjectPapers();

    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "移除论文失败。",
        );
      }
    } finally {
      setActionLoading(false);
    }
  }


  if (loading) {
    return (
      <div className="p-8">
        正在加载项目...
      </div>
    );
  }


  if (!project) {
    return (
      <div className="p-8">
        {
          error ||
          "项目不存在。"
        }
      </div>
    );
  }


  const projectPaperIds =
    new Set(
      projectPapers.map(
        (item) =>
          item.paper.id,
      ),
    );


  const availablePapers =
    allPapers.filter(
      (paper) =>
        !projectPaperIds.has(
          paper.id,
        ),
    );


  return (
    <div
      className="
        mx-auto
        max-w-6xl
        p-8
      "
    >
      <Link
        href="/projects"

        className="
          text-sm
          text-slate-500
          hover:text-slate-950
        "
      >
        ← 返回 Projects
      </Link>


      <header
        className="
          mt-6
        "
      >
        <h1
          className="
            text-3xl
            font-bold
            text-slate-950
          "
        >
          {project.name}
        </h1>


        <p
          className="
            mt-2
            max-w-3xl
            text-slate-600
          "
        >
          {
            project.description ||
            "暂无项目描述。"
          }
        </p>


        <p
          className="
            mt-3
            text-xs
            text-slate-400
          "
        >
          创建时间：{" "}
          {
            new Date(
              project.created_at,
            ).toLocaleString()
          }
        </p>
      </header>


      {error && (
        <div
          className="
            mt-6
            rounded-lg
            bg-red-50
            p-4
            text-sm
            text-red-700
          "
        >
          {error}
        </div>
      )}


      <section
        className="
          mt-8
          rounded-2xl
          border
          border-slate-200
          bg-white
          p-6
          shadow-sm
        "
      >
        <h2
          className="
            text-xl
            font-semibold
            text-slate-950
          "
        >
          添加论文
        </h2>


        <p
          className="
            mt-1
            text-sm
            text-slate-500
          "
        >
          将 Paper Library 中已有论文加入当前科研项目。
        </p>


        <div
          className="
            mt-4
            flex
            gap-3
          "
        >
          <select
            value={
              selectedPaperId
            }

            onChange={
              (event) =>
                setSelectedPaperId(
                  event.target.value,
                )
            }

            className="
              min-w-0
              flex-1
              rounded-lg
              border
              border-slate-300
              px-4
              py-3
            "
          >
            <option value="">
              选择论文
            </option>


            {availablePapers.map(
              (paper) => (
                <option
                  key={
                    paper.id
                  }

                  value={
                    paper.id
                  }
                >
                  {paper.title}
                </option>
              ),
            )}
          </select>


          <button
            type="button"

            disabled={
              actionLoading ||
              !selectedPaperId
            }

            onClick={
              handleAddPaper
            }

            className="
              rounded-lg
              bg-slate-950
              px-5
              py-3
              text-sm
              font-medium
              text-white
              disabled:opacity-50
            "
          >
            {
              actionLoading
                ? "处理中..."
                : "添加"
            }
          </button>
        </div>
      </section>


      <section
        className="
          mt-8
        "
      >
        <div
          className="
            flex
            items-center
            justify-between
          "
        >
          <h2
            className="
              text-xl
              font-semibold
              text-slate-950
            "
          >
            项目论文
          </h2>

          <span
            className="
              text-sm
              text-slate-500
            "
          >
            {
              projectPapers.length
            }{" "}
            papers
          </span>
        </div>


        {projectPapers.length === 0 ? (
          <div
            className="
              mt-4
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
            当前项目还没有论文。
          </div>
        ) : (
          <div
            className="
              mt-4
              space-y-3
            "
          >
            {projectPapers.map(
              (item) => {
                const paper =
                  item.paper;


                return (
                  <div
                    key={
                      paper.id
                    }

                    className="
                      flex
                      items-center
                      justify-between
                      gap-5
                      rounded-xl
                      border
                      border-slate-200
                      bg-white
                      p-5
                    "
                  >
                    <div
                      className="
                        min-w-0
                      "
                    >
                      <Link
                        href={
                          `/papers/${paper.id}`
                        }

                        className="
                          font-medium
                          text-slate-950
                          hover:underline
                        "
                      >
                        {paper.title}
                      </Link>


                      <p
                        className="
                          mt-1
                          text-sm
                          text-slate-500
                        "
                      >
                        {
                          paper.authors.join(
                            ", ",
                          )
                        }
                      </p>


                      <p
                        className="
                          mt-2
                          text-xs
                          text-slate-400
                        "
                      >
                        加入项目：{" "}
                        {
                          new Date(
                            item.added_at,
                          ).toLocaleString()
                        }
                      </p>
                    </div>


                    <button
                      type="button"

                      disabled={
                        actionLoading
                      }

                      onClick={
                        () =>
                          handleRemovePaper(
                            paper.id,
                          )
                      }

                      className="
                        shrink-0
                        rounded-lg
                        border
                        border-red-200
                        px-3
                        py-2
                        text-sm
                        text-red-600
                        hover:bg-red-50
                        disabled:opacity-50
                      "
                    >
                      移除
                    </button>
                  </div>
                );
              },
            )}
          </div>
        )}
      </section>
    </div>
  );
}