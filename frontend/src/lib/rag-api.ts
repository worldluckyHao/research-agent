import {
  apiRequest,
} from "@/lib/api";

import type {
  RAGAnswerResponse,
  RAGQuestionRequest,
} from "@/types/rag";


// ============================================================
// Ask Document
// ============================================================

export async function askPaperDocument(
  paperId: number,
  documentId: number,
  request: RAGQuestionRequest,
): Promise<RAGAnswerResponse> {
  return apiRequest<
    RAGAnswerResponse
  >(
    (
      `/papers/${paperId}` +
      `/documents/${documentId}` +
      `/rag`
    ),
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify(
        request,
      ),
    },
  );
}