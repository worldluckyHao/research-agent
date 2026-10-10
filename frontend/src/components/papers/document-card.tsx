"use client";

import {
  useState,
} from "react";

import {
  DocumentSearch,
} from "@/components/papers/document-search";

import {
  ApiError,
} from "@/lib/api";

import {
  chunkPaperDocument,
  embedPaperDocument,
  parsePaperDocument,
  waitForDocumentStage,
} from "@/lib/documents-api";

import type {
  PaperDocument,
} from "@/types/document";

import {
  RAGChat,
} from "@/components/papers/rag-chat";

interface DocumentCardProps {
  document:
    PaperDocument;

  onUpdated: (
    document: PaperDocument,
  ) => void;
}


// ============================================================
// File Size
// ============================================================

function formatFileSize(
  bytes: number,
): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (
    bytes <
    1024 * 1024
  ) {
    return (
      (
        bytes /
        1024
      ).toFixed(1) +
      " KB"
    );
  }

  return (
    (
      bytes /
      1024 /
      1024
    ).toFixed(2) +
    " MB"
  );
}


// ============================================================
// Status
// ============================================================

function StatusBadge({
  label,
  status,
}: {
  label: string;
  status: string;
}) {
  return (
    <div
      className="
        rounded-xl
        border
        border-slate-200
        bg-slate-50
        px-4
        py-3
      "
    >
      <p
        className="
          text-xs
          font-medium
          uppercase
          tracking-wide
          text-slate-400
        "
      >
        {label}
      </p>

      <p
        className="
          mt-1
          text-sm
          font-semibold
          text-slate-800
        "
      >
        {status}
      </p>
    </div>
  );
}


// ============================================================
// Component
// ============================================================

export function DocumentCard({
  document,
  onUpdated,
}: DocumentCardProps) {
  const [
    processing,
    setProcessing,
  ] = useState<
    | "parse"
    | "chunk"
    | "embedding"
    | "pipeline"
    | null
  >(
    null,
  );

  const [
    error,
    setError,
  ] = useState("");

  const [
    message,
    setMessage,
  ] = useState("");


  const parsed =
    Boolean(
      document.parsed_at,
    );

  const chunked =
    Boolean(
      document.chunked_at,
    );

  const embedded =
    Boolean(
      document.embedded_at,
    );


  function handleError(
    err: unknown,
    fallback: string,
  ) {
    if (
      err instanceof ApiError
    ) {
      setError(
        err.message,
      );

      return;
    }

    if (
      err instanceof Error
    ) {
      setError(
        err.message,
      );

      return;
    }

    setError(
      fallback,
    );
  }


  // ==========================================================
  // Parse
  // ==========================================================

  async function handleParse() {
    setProcessing(
      "parse",
    );

    setError("");
    setMessage("");


    try {
      const submitted =
        await parsePaperDocument(
          document.paper_id,
          document.id,
        );

      onUpdated(
        submitted,
      );


      const completed =
        await waitForDocumentStage(
          document.paper_id,
          document.id,
          "parse",
        );

      onUpdated(
        completed,
      );


      setMessage(
        "PDF 解析完成。",
      );

    } catch (err) {
      handleError(
        err,
        "PDF 解析失败。",
      );
    } finally {
      setProcessing(
        null,
      );
    }
  }


  // ==========================================================
  // Chunk
  // ==========================================================

  async function handleChunk() {
    setProcessing(
      "chunk",
    );

    setError("");
    setMessage("");


    try {
      const submitted =
        await chunkPaperDocument(
          document.paper_id,
          document.id,
        );

      onUpdated(
        submitted,
      );


      const completed =
        await waitForDocumentStage(
          document.paper_id,
          document.id,
          "chunk",
        );

      onUpdated(
        completed,
      );


      setMessage(
        "Document Chunking 完成。",
      );

    } catch (err) {
      handleError(
        err,
        "Document Chunking 失败。",
      );
    } finally {
      setProcessing(
        null,
      );
    }
  }


  // ==========================================================
  // Embedding
  // ==========================================================

  async function handleEmbed() {
    setProcessing(
      "embedding",
    );

    setError("");
    setMessage("");


    try {
      const submitted =
        await embedPaperDocument(
          document.paper_id,
          document.id,
        );

      onUpdated(
        submitted,
      );


      const completed =
        await waitForDocumentStage(
          document.paper_id,
          document.id,
          "embedding",
        );

      onUpdated(
        completed,
      );


      setMessage(
        "Embedding 生成完成。",
      );

    } catch (err) {
      handleError(
        err,
        "Embedding 生成失败。",
      );
    } finally {
      setProcessing(
        null,
      );
    }
  }


  // ==========================================================
  // Full Pipeline
  // ==========================================================

  async function handlePipeline() {
    setProcessing(
      "pipeline",
    );

    setError("");
    setMessage("");


    try {
      let current =
        document;


      if (!current.parsed_at) {
        current =
          await parsePaperDocument(
            current.paper_id,
            current.id,
          );

        onUpdated(
          current,
        );


        current =
          await waitForDocumentStage(
            current.paper_id,
            current.id,
            "parse",
          );

        onUpdated(
          current,
        );
      }


      if (!current.chunked_at) {
        current =
          await chunkPaperDocument(
            current.paper_id,
            current.id,
          );

        onUpdated(
          current,
        );


        current =
          await waitForDocumentStage(
            current.paper_id,
            current.id,
            "chunk",
          );

        onUpdated(
          current,
        );
      }


      if (!current.embedded_at) {
        current =
          await embedPaperDocument(
            current.paper_id,
            current.id,
          );

        onUpdated(
          current,
        );


        current =
          await waitForDocumentStage(
            current.paper_id,
            current.id,
            "embedding",
          );

        onUpdated(
          current,
        );
      }


      setMessage(
        "Document Pipeline 全部完成。",
      );

    } catch (err) {
      handleError(
        err,
        "Document Pipeline 执行失败。",
      );
    } finally {
      setProcessing(
        null,
      );
    }
  }


  const busy =
    processing !== null;


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
      {/* =================================================== */}
      {/* Document Metadata */}
      {/* =================================================== */}

      <div
        className="
          flex
          flex-wrap
          items-start
          justify-between
          gap-4
        "
      >
        <div
          className="
            min-w-0
          "
        >
          <h3
            className="
              text-lg
              font-semibold
              text-slate-950
            "
          >
            {
              document
                .original_filename
            }
          </h3>

          <p
            className="
              mt-2
              text-sm
              text-slate-500
            "
          >
            {
              formatFileSize(
                document.size_bytes,
              )
            }
            {" · "}
            {
              document.mime_type
            }
          </p>
        </div>


        <span
          className="
            rounded-full
            bg-slate-100
            px-3
            py-1
            text-xs
            font-medium
            text-slate-600
          "
        >
          Document #
          {document.id}
        </span>
      </div>


      {/* =================================================== */}
      {/* Pipeline Status */}
      {/* =================================================== */}

      <div
        className="
          mt-5
          grid
          gap-3
          sm:grid-cols-3
        "
      >
        <StatusBadge
          label="Parse"
          status={
            document.status
          }
        />

        <StatusBadge
          label="Chunk"
          status={
            document.chunk_status
          }
        />

        <StatusBadge
          label="Embedding"
          status={
            document.embedding_status
          }
        />
      </div>


      {/* =================================================== */}
      {/* Metrics */}
      {/* =================================================== */}

      <div
        className="
          mt-5
          grid
          gap-3
          sm:grid-cols-3
        "
      >
        <div>
          <p
            className="
              text-xs
              text-slate-400
            "
          >
            Pages
          </p>

          <p
            className="
              mt-1
              font-medium
            "
          >
            {
              document.page_count ??
              "-"
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
            Chunks
          </p>

          <p
            className="
              mt-1
              font-medium
            "
          >
            {
              document.chunk_count
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
            Embeddings
          </p>

          <p
            className="
              mt-1
              font-medium
            "
          >
            {
              document.embedding_count
            }
          </p>
        </div>
      </div>


      {/* =================================================== */}
      {/* Pipeline Actions */}
      {/* =================================================== */}

      <div
        className="
          mt-6
          flex
          flex-wrap
          gap-3
        "
      >
        <button
          type="button"

          onClick={
            handleParse
          }

          disabled={
            busy
          }

          className="
            rounded-lg
            border
            border-slate-300
            px-4
            py-2
            text-sm
            font-medium
            disabled:opacity-50
          "
        >
          {
            processing ===
              "parse"
              ? "Parsing..."
              : parsed
                ? "Parse Completed ✓"
                : "Parse PDF"
          }
        </button>


        <button
          type="button"

          onClick={
            handleChunk
          }

          disabled={
            busy ||
            !parsed
          }

          className="
            rounded-lg
            border
            border-slate-300
            px-4
            py-2
            text-sm
            font-medium
            disabled:opacity-50
          "
        >
          {
            processing ===
              "chunk"
              ? "Chunking..."
              : chunked
                ? "Chunks Completed ✓"
                : "Build Chunks"
          }
        </button>


        <button
          type="button"

          onClick={
            handleEmbed
          }

          disabled={
            busy ||
            !chunked
          }

          className="
            rounded-lg
            border
            border-slate-300
            px-4
            py-2
            text-sm
            font-medium
            disabled:opacity-50
          "
        >
          {
            processing ===
              "embedding"
              ? "Embedding..."
              : embedded
                ? "Embedding Completed ✓"
                : "Generate Embeddings"
          }
        </button>


        <button
          type="button"

          onClick={
            handlePipeline
          }

          disabled={
            busy ||
            embedded
          }

          className="
            rounded-lg
            bg-slate-950
            px-4
            py-2
            text-sm
            font-medium
            text-white
            disabled:opacity-50
          "
        >
          {
            processing ===
              "pipeline"
              ? "Running Pipeline..."
              : embedded
                ? "Pipeline Completed ✓"
                : "Run Full Pipeline"
          }
        </button>
      </div>


      {processing ===
        "pipeline" && (
        <div
          className="
            mt-4
            rounded-lg
            bg-blue-50
            px-4
            py-3
            text-sm
            text-blue-700
          "
        >
          正在执行：
          Parse → Chunk → Embedding。
          请保持 Celery Worker 运行。
        </div>
      )}


      {error && (
        <div
          className="
            mt-4
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
            mt-4
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


      {/* =================================================== */}
      {/* Retrieval */}
      {/* =================================================== */}

      <DocumentSearch
        paperId={
          document.paper_id
        }

        documentId={
          document.id
        }

        enabled={
          embedded
        }
      />
      <RAGChat
          paperId={
            document.paper_id
          }

          documentId={
            document.id
          }

          enabled={
            embedded
          }
      />



      <div
        className="
          mt-6
          border-t
          border-slate-100
          pt-4
          text-xs
          text-slate-400
        "
      >
        Uploaded{" "}
        {
          new Date(
            document.created_at,
          ).toLocaleString()
        }
      </div>
    </article>
  );
}