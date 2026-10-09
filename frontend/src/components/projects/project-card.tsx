import Link from "next/link";

import type {
  Project,
} from "@/types/project";


export function ProjectCard({
  project,
}: {
  project: Project;
}) {
  return (
    <Link
      href={
        `/projects/${project.id}`
      }

      className="
        block
        rounded-2xl
        border
        border-slate-200
        bg-white
        p-6
        shadow-sm
        transition
        hover:-translate-y-0.5
        hover:shadow-md
      "
    >
      <h3
        className="
          text-lg
          font-semibold
          text-slate-950
        "
      >
        {project.name}
      </h3>


      {project.description ? (
        <p
          className="
            mt-3
            line-clamp-3
            text-sm
            leading-6
            text-slate-600
          "
        >
          {project.description}
        </p>
      ) : (
        <p
          className="
            mt-3
            text-sm
            text-slate-400
          "
        >
          暂无项目描述
        </p>
      )}


      <p
        className="
          mt-5
          text-xs
          text-slate-400
        "
      >
        创建于{" "}
        {
          new Date(
            project.created_at,
          ).toLocaleString()
        }
      </p>
    </Link>
  );
}