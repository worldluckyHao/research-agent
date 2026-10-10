// ============================================================
// Semantic Search
// ============================================================

export interface SemanticSearchRequest {
  query: string;

  top_k?: number;

  min_score?: number;
}


export interface SemanticSearchModelInfo {
  provider: string;

  model_name: string;

  dimension: number;
}


export interface SemanticSearchResultItem {
  chunk_id: number;

  chunk_index: number;

  content: string;

  start_page: number;

  end_page: number;

  token_count: number;

  similarity_score: number;

  cosine_distance: number;
}


export interface SemanticSearchResponse {
  document_id: number;

  query: string;

  top_k: number;

  min_score: number;

  returned_count: number;

  model: SemanticSearchModelInfo;

  items: SemanticSearchResultItem[];
}


// ============================================================
// Hybrid Search
// ============================================================

export interface HybridSearchRequest {
  query: string;

  top_k?: number;

  use_reranker?: boolean;
}


export interface HybridSearchResultItem {
  chunk_id: number;

  chunk_index: number;

  content: string;

  start_page: number;

  end_page: number;

  token_count: number;

  semantic_rank:
    | number
    | null;

  semantic_score:
    | number
    | null;

  lexical_rank:
    | number
    | null;

  lexical_score:
    | number
    | null;

  rrf_score: number;

  rerank_score:
    | number
    | null;
}


export interface HybridSearchResponse {
  document_id: number;

  query: string;

  top_k: number;

  reranker_used: boolean;

  semantic_candidate_count: number;

  lexical_candidate_count: number;

  fused_candidate_count: number;

  returned_count: number;

  items: HybridSearchResultItem[];
}


// ============================================================
// Frontend Search Mode
// ============================================================

export type RetrievalMode =
  | "semantic"
  | "hybrid";