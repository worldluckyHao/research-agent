import {
  apiRequest,
} from "@/lib/api";

import type {
  PaperDocument,
  PaperDocumentListResponse,
} from "@/types/document";


// ============================================================
// List Documents
// ============================================================

export async function listPaperDocuments(
  paperId: number,
): Promise<PaperDocument[]> {
  const response =
    await apiRequest<
      PaperDocumentListResponse
    >(
      `/papers/${paperId}/documents`,
    );

  return response.items;
}


// ============================================================
// Get Document
// ============================================================

export async function getPaperDocument(
  paperId: number,
  documentId: number,
): Promise<PaperDocument> {
  return apiRequest<PaperDocument>(
    (
      `/papers/${paperId}` +
      `/documents/${documentId}`
    ),
  );
}


// ============================================================
// Upload PDF
// ============================================================

export async function uploadPaperDocument(
  paperId: number,
  file: File,
): Promise<PaperDocument> {
  const formData =
    new FormData();

  formData.append(
    "file",
    file,
  );

  return apiRequest<PaperDocument>(
    `/papers/${paperId}/documents`,
    {
      method: "POST",
      body: formData,
    },
  );
}


// ============================================================
// Parse
// ============================================================

export async function parsePaperDocument(
  paperId: number,
  documentId: number,
  force = false,
): Promise<PaperDocument> {
  return apiRequest<PaperDocument>(
    (
      `/papers/${paperId}` +
      `/documents/${documentId}` +
      `/parse?force=${force}`
    ),
    {
      method: "POST",
    },
  );
}


// ============================================================
// Chunk
// ============================================================

export async function chunkPaperDocument(
  paperId: number,
  documentId: number,
  force = false,
): Promise<PaperDocument> {
  return apiRequest<PaperDocument>(
    (
      `/papers/${paperId}` +
      `/documents/${documentId}` +
      `/chunk?force=${force}`
    ),
    {
      method: "POST",
    },
  );
}


// ============================================================
// Embed
// ============================================================

export async function embedPaperDocument(
  paperId: number,
  documentId: number,
  force = false,
): Promise<PaperDocument> {
  return apiRequest<PaperDocument>(
    (
      `/papers/${paperId}` +
      `/documents/${documentId}` +
      `/embed?force=${force}`
    ),
    {
      method: "POST",
    },
  );
}


// ============================================================
// Polling
// ============================================================

export type DocumentStage =
  | "parse"
  | "chunk"
  | "embedding";


function isStageCompleted(
  document: PaperDocument,
  stage: DocumentStage,
): boolean {
  switch (stage) {
    case "parse":
      return Boolean(
        document.parsed_at,
      );

    case "chunk":
      return Boolean(
        document.chunked_at,
      );

    case "embedding":
      return Boolean(
        document.embedded_at,
      );
  }
}


function getStageError(
  document: PaperDocument,
  stage: DocumentStage,
): string | null {
  switch (stage) {
    case "parse":
      return (
        document.parse_error ??
        null
      );

    case "chunk":
      return (
        document.chunk_error ??
        null
      );

    case "embedding":
      return (
        document.embedding_error ??
        null
      );
  }
}


// ============================================================
// Wait For Stage
// ============================================================
//
// 不依赖 status 字符串具体取值。
// 直接使用后端更可靠的：
//
// parsed_at
// chunked_at
// embedded_at
//
// 判断是否真正完成。
//
export async function waitForDocumentStage(
  paperId: number,
  documentId: number,
  stage: DocumentStage,
): Promise<PaperDocument> {
  const maxAttempts =
    120;

  const intervalMs =
    1500;


  for (
    let attempt = 0;
    attempt < maxAttempts;
    attempt += 1
  ) {
    const document =
      await getPaperDocument(
        paperId,
        documentId,
      );


    const stageError =
      getStageError(
        document,
        stage,
      );


    if (stageError) {
      throw new Error(
        stageError,
      );
    }


    if (
      isStageCompleted(
        document,
        stage,
      )
    ) {
      return document;
    }


    await new Promise<void>(
      (resolve) => {
        window.setTimeout(
          resolve,
          intervalMs,
        );
      },
    );
  }


  throw new Error(
    `${stage} 任务未在预期时间内完成。`,
  );
}