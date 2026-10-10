import {
  apiRequest,
} from "@/lib/api";

import type {
  HybridSearchRequest,
  HybridSearchResponse,
  SemanticSearchRequest,
  SemanticSearchResponse,
} from "@/types/retrieval";


// ============================================================
// Semantic Search
// ============================================================

export async function semanticSearchDocument(
  paperId: number,
  documentId: number,
  request: SemanticSearchRequest,
): Promise<SemanticSearchResponse> {
  return apiRequest<
    SemanticSearchResponse
  >(
    (
      `/papers/${paperId}` +
      `/documents/${documentId}` +
      `/search`
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


// ============================================================
// Hybrid Search
// ============================================================

export async function hybridSearchDocument(
  paperId: number,
  documentId: number,
  request: HybridSearchRequest,
): Promise<HybridSearchResponse> {
  return apiRequest<
    HybridSearchResponse
  >(
    (
      `/papers/${paperId}` +
      `/documents/${documentId}` +
      `/hybrid-search`
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