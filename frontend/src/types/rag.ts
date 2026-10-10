// ============================================================
// RAG Request
// ============================================================

export interface RAGQuestionRequest {
  question: string;

  top_k?: number;

  use_reranker?: boolean;
}


// ============================================================
// Citation
// ============================================================

export interface RAGCitation {
  source_id: string;

  chunk_id: number;

  chunk_index: number;

  start_page: number;

  end_page: number;
}


// ============================================================
// Model
// ============================================================

export interface RAGModelInfo {
  provider: string;

  model_name: string;
}


// ============================================================
// Prompt
// ============================================================

export interface RAGPromptInfo {
  system_prompt_id: string;

  system_prompt_version: number;

  user_prompt_id: string;

  user_prompt_version: number;
}


// ============================================================
// Response
// ============================================================

export interface RAGAnswerResponse {
  document_id: number;

  question: string;

  answer: string;

  grounded: boolean;

  retrieval_count: number;

  model:
    | RAGModelInfo
    | null;

  prompt:
    | RAGPromptInfo
    | null;

  citations: RAGCitation[];

  invalid_citations: string[];
}