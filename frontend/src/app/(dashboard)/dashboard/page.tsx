"use client";

import {
  useAuth,
} from "@/contexts/auth-context";


export default function DashboardPage() {
  const {
    user,
  } = useAuth();


  const cards = [
    {
      title: "Papers",
      value: "--",
      description:
        "管理和搜索研究论文",
    },
    {
      title: "Projects",
      value: "--",
      description:
        "组织科研项目与论文",
    },
    {
      title: "RAG",
      value: "Ready",
      description:
        "论文知识库问答",
    },
    {
      title: "Research Agent",
      value: "Ready",
      description:
        "科研智能体工作流",
    },
  ];


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
          Research Workspace
        </p>

        <h2
          className="
            mt-1
            text-3xl
            font-bold
            tracking-tight
            text-slate-950
          "
        >
          欢迎回来，
          {
            user?.username
          }
        </h2>

        <p
          className="
            mt-2
            text-slate-600
          "
        >
          从论文检索到研究方案生成，
          管理你的完整科研工作流。
        </p>
      </header>


      <section
        className="
          mt-8
          grid
          gap-5
          md:grid-cols-2
          xl:grid-cols-4
        "
      >
        {cards.map(
          (card) => (
            <div
              key={
                card.title
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
              <p
                className="
                  text-sm
                  font-medium
                  text-slate-500
                "
              >
                {
                  card.title
                }
              </p>

              <p
                className="
                  mt-3
                  text-2xl
                  font-semibold
                  text-slate-950
                "
              >
                {
                  card.value
                }
              </p>

              <p
                className="
                  mt-2
                  text-sm
                  text-slate-500
                "
              >
                {
                  card.description
                }
              </p>
            </div>
          ),
        )}
      </section>


      <section
        className="
          mt-8
          rounded-2xl
          border
          border-slate-200
          bg-white
          p-8
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
          Research-Agent Workflow
        </h3>

        <div
          className="
            mt-5
            flex
            flex-wrap
            gap-3
            text-sm
          "
        >
          {[
            "Search Papers",
            "Import",
            "Project",
            "PDF",
            "Retrieval",
            "RAG",
            "Compare",
            "Research Gap",
            "Research Idea",
            "Experiment",
          ].map(
            (step) => (
              <span
                key={step}

                className="
                  rounded-full
                  bg-slate-100
                  px-4
                  py-2
                  text-slate-700
                "
              >
                {step}
              </span>
            ),
          )}
        </div>
      </section>
    </div>
  );
}