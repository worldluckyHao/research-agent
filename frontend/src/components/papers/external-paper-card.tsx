"use client";

import type {
  UnifiedPaperMetadata,
} from "@/types/external-paper";


interface ExternalPaperCardProps {
  paper:
    UnifiedPaperMetadata;

  importing: boolean;

  imported: boolean;

  onImport: () => void;
}


export function ExternalPaperCard({
  paper,
  importing,
  imported,
  onImport,
}: ExternalPaperCardProps) {
  const sources =
    paper.sources?.length
      ? paper.sources
      : [paper.provider];


  return (
    <article
      className="
        rounded-2xl
        border
        border-slate-200
        bg-white
        p-6
        shadow-sm
      "
    >
      <div
        className="
          flex
          items-start
          justify-between
          gap-5
        "
      >
        <div
          className="
            min-w-0
            flex-1
          "
        >
          <h3
            className="
              text-lg
              font-semibold
              leading-7
              text-slate-950
            "
          >
            {paper.title}
          </h3>


          {paper.authors &&
            paper.authors.length > 0 && (
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
            )}


          <div
            className="
              mt-3
              flex
              flex-wrap
              gap-2
            "
          >
            {paper.year && (
              <span
                className="
                  rounded-full
                  bg-slate-100
                  px-3
                  py-1
                  text-xs
                  text-slate-600
                "
              >
                {paper.year}
              </span>
            )}


            {sources.map(
              (source) => (
                <span
                  key={
                    source
                  }

                  className="
                    rounded-full
                    bg-blue-50
                    px-3
                    py-1
                    text-xs
                    text-blue-700
                  "
                >
                  {source}
                </span>
              ),
            )}


            {paper.is_open_access ===
              true && (
              <span
                className="
                  rounded-full
                  bg-emerald-50
                  px-3
                  py-1
                  text-xs
                  text-emerald-700
                "
              >
                Open Access
              </span>
            )}
          </div>
        </div>


        <button
          type="button"

          disabled={
            importing ||
            imported
          }

          onClick={
            onImport
          }

          className="
            shrink-0
            rounded-lg
            bg-slate-950
            px-4
            py-2
            text-sm
            font-medium
            text-white
            disabled:cursor-not-allowed
            disabled:opacity-50
          "
        >
          {
            imported
              ? "Imported ✓"
              : importing
                ? "Importing..."
                : "Import"
          }
        </button>
      </div>


      {paper.venue && (
        <p
          className="
            mt-4
            text-sm
            text-slate-500
          "
        >
          Venue: {paper.venue}
        </p>
      )}


      {paper.abstract && (
        <p
          className="
            mt-4
            max-h-24
            overflow-hidden
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
          gap-x-5
          gap-y-2
          text-xs
          text-slate-500
        "
      >
        {paper.doi && (
          <span>
            DOI: {paper.doi}
          </span>
        )}


        {paper.arxiv_id && (
          <span>
            arXiv: {
              paper.arxiv_id
            }
          </span>
        )}


        {paper.cited_by_count !==
          undefined && (
          <span>
            Citations: {
              paper.cited_by_count
            }
          </span>
        )}
      </div>


      <div
        className="
          mt-5
          flex
          gap-3
        "
      >
        {paper.url && (
          <a
            href={
              paper.url
            }

            target="_blank"

            rel="noreferrer"

            className="
              text-sm
              font-medium
              text-blue-700
              hover:underline
            "
          >
            查看原文
          </a>
        )}


        {paper.pdf_url && (
          <a
            href={
              paper.pdf_url
            }

            target="_blank"

            rel="noreferrer"

            className="
              text-sm
              font-medium
              text-blue-700
              hover:underline
            "
          >
            PDF
          </a>
        )}
      </div>
    </article>
  );
}