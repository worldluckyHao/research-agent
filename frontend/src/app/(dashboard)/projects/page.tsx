"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  CreateProjectForm,
} from "@/components/projects/create-project-form";

import {
  ProjectCard,
} from "@/components/projects/project-card";

import {
  ApiError,
} from "@/lib/api";

import {
  listProjects,
} from "@/lib/projects-api";

import type {
  Project,
} from "@/types/project";


export default function ProjectsPage() {
  const [
    projects,
    setProjects,
  ] = useState<Project[]>([]);

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
          await listProjects();

        setProjects(
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
            "加载项目失败。",
          );
        }
      } finally {
        setLoading(false);
      }
    }


    void load();
  }, []);


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
          RESEARCH WORKSPACE
        </p>

        <h2
          className="
            mt-1
            text-3xl
            font-bold
            text-slate-950
          "
        >
          Projects
        </h2>

        <p
          className="
            mt-2
            text-slate-600
          "
        >
          使用科研项目组织论文和 AI Research Workflow。
        </p>
      </header>


      <div
        className="
          mt-8
          grid
          gap-8
          xl:grid-cols-[360px_1fr]
        "
      >
        <CreateProjectForm
          onCreated={
            (project) =>
              setProjects(
                (current) => [
                  project,
                  ...current,
                ],
              )
          }
        />


        <section>
          {loading && (
            <p
              className="
                text-sm
                text-slate-500
              "
            >
              正在加载项目...
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
            projects.length === 0 && (
              <div
                className="
                  rounded-2xl
                  border
                  border-dashed
                  border-slate-300
                  bg-white
                  p-12
                  text-center
                "
              >
                <p
                  className="
                    text-slate-600
                  "
                >
                  当前还没有科研项目。
                </p>
              </div>
            )}


          <div
            className="
              grid
              gap-4
              lg:grid-cols-2
            "
          >
            {projects.map(
              (project) => (
                <ProjectCard
                  key={
                    project.id
                  }

                  project={
                    project
                  }
                />
              ),
            )}
          </div>
        </section>
      </div>
    </div>
  );
}