"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  DocumentCard,
} from "@/components/papers/document-card";

import {
  DocumentUpload,
} from "@/components/papers/document-upload";

import {
  ApiError,
} from "@/lib/api";

import {
  listPaperDocuments,
} from "@/lib/documents-api";

import type {
  PaperDocument,
} from "@/types/document";


interface DocumentsSectionProps {
  paperId: number;
}


export function DocumentsSection({
  paperId,
}: DocumentsSectionProps) {
  const [
    documents,
    setDocuments,
  ] = useState<
    PaperDocument[]
  >(
    [],
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  // ============================================================
  // Load Documents
  // ============================================================
  //
  // 从后端重新获取当前 Paper 的所有 Documents。
  // Refresh 和首次进入页面都会复用这个方法。
  //
  const loadDocuments =
    useCallback(
      async () => {
        setError("");

        try {
          const result =
            await listPaperDocuments(
              paperId,
            );

          setDocuments(
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
              "加载 PDF Documents 失败。",
            );
          }
        } finally {
          setLoading(false);
        }
      },
      [
        paperId,
      ],
    );


  // ============================================================
  // Initial Load
  // ============================================================

  useEffect(() => {
    void loadDocuments();
  }, [
    loadDocuments,
  ]);


  // ============================================================
  // Upload Result
  // ============================================================
  //
  // 后端对完全相同的 PDF 会复用已有 Document。
  //
  // 因此：
  // - 如果 document.id 已存在，则更新原记录；
  // - 如果是新 Document，则插入到列表最前面。
  //
  function handleUploaded(
    uploaded:
      PaperDocument,
  ) {
    setDocuments(
      (current) => {
        const exists =
          current.some(
            (document) =>
              document.id ===
              uploaded.id,
          );


        if (exists) {
          return current.map(
            (document) =>
              document.id ===
              uploaded.id
                ? uploaded
                : document,
          );
        }


        return [
          uploaded,
          ...current,
        ];
      },
    );
  }


  // ============================================================
  // Pipeline Update
  // ============================================================
  //
  // Parse / Chunk / Embedding 每完成一个阶段，
  // DocumentCard 会返回最新的 PaperDocument。
  //
  // 这里根据 id 替换对应 Document，
  // 从而实时刷新：
  //
  // status
  // page_count
  // chunk_count
  // embedding_count
  // parsed_at / chunked_at / embedded_at
  //
  function handleUpdated(
    updated:
      PaperDocument,
  ) {
    setDocuments(
      (current) =>
        current.map(
          (document) =>
            document.id ===
            updated.id
              ? updated
              : document,
        ),
    );
  }


  return (
    <section
      className="
        mt-10
        border-t
        border-slate-200
        pt-10
      "
    >
      {/* ===================================================== */}
      {/* Header */}
      {/* ===================================================== */}

      <div
        className="
          flex
          flex-wrap
          items-end
          justify-between
          gap-4
        "
      >
        <div>
          <p
            className="
              text-sm
              font-medium
              text-slate-500
            "
          >
            DOCUMENT PIPELINE
          </p>


          <h2
            className="
              mt-1
              text-2xl
              font-bold
              text-slate-950
            "
          >
            PDF Documents
          </h2>


          <p
            className="
              mt-2
              text-sm
              text-slate-500
            "
          >
            上传论文 PDF，
            并执行解析、切块和向量化处理。
          </p>
        </div>


        <button
          type="button"

          onClick={
            () =>
              void loadDocuments()
          }

          className="
            rounded-lg
            border
            border-slate-300
            px-4
            py-2
            text-sm
            text-slate-700
            transition
            hover:bg-slate-50
          "
        >
          Refresh
        </button>
      </div>


      {/* ===================================================== */}
      {/* Main */}
      {/* ===================================================== */}

      <div
        className="
          mt-6
          grid
          gap-8
          xl:grid-cols-[360px_1fr]
        "
      >
        {/* =================================================== */}
        {/* Upload */}
        {/* =================================================== */}

        <DocumentUpload
          paperId={
            paperId
          }

          onUploaded={
            handleUploaded
          }
        />


        {/* =================================================== */}
        {/* Document List */}
        {/* =================================================== */}

        <div>
          {loading && (
            <p
              className="
                text-sm
                text-slate-500
              "
            >
              正在加载 Documents...
            </p>
          )}


          {error && (
            <div
              className="
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


          {!loading &&
            !error &&
            documents.length ===
              0 && (
              <div
                className="
                  rounded-2xl
                  border
                  border-dashed
                  border-slate-300
                  bg-white
                  p-12
                  text-center
                  text-slate-500
                "
              >
                这篇论文还没有上传 PDF。
              </div>
            )}


          <div
            className="
              space-y-4
            "
          >
            {documents.map(
              (document) => (
                <DocumentCard
                  key={
                    document.id
                  }

                  document={
                    document
                  }

                  onUpdated={
                    handleUpdated
                  }
                />
              ),
            )}
          </div>
        </div>
      </div>
    </section>
  );
}