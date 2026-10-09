import Link from "next/link";

import type {
  Paper,
} from "@/types/paper";


export function PaperCard({
  paper,
}: {
  paper: Paper;
}) {
  return (
    <Link
      href={
        `/papers/${paper.id}`
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
      <div
        className="
          flex
          items-start
          justify-between
          gap-4
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
            {paper.title}
          </h3>

          <p
            className="
              mt-2
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
        </div>

        <span
          className="
            shrink-0
            rounded-full
            bg-slate-100
            px-3
            py-1
            text-xs
            font-medium
            text-slate-600
          "
        >
          {paper.year}
        </span>
      </div>


      {paper.abstract && (
        <p
          className="
            mt-4
            line-clamp-3
            text-sm
            leading-6
            text-slate-600
          "
        >
          {paper.abstract}
        </p>
      )}


      <div
        className="
          mt-5
          flex
          flex-wrap
          gap-2
        "
      >
        {paper.source && (
          <span
            className="
              rounded-md
              bg-blue-50
              px-2
              py-1
              text-xs
              text-blue-700
            "
          >
            {paper.source}
          </span>
        )}

        {paper.doi && (
          <span
            className="
              rounded-md
              bg-slate-100
              px-2
              py-1
              text-xs
              text-slate-600
            "
          >
            DOI
          </span>
        )}
      </div>
    </Link>
  );
}