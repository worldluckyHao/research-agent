// ============================================================
// Paper Document
// ============================================================

export interface PaperDocument {
  id: number;

  paper_id: number;

  uploaded_by_id:
    | number
    | null;

  original_filename: string;

  storage_backend: string;

  mime_type: string;

  size_bytes: number;

  sha256: string;

  status: string;

  created_at: string;

  updated_at: string;


  // ==========================================================
  // Parse
  // ==========================================================

  page_count?:
    | number
    | null;

  parser_name?:
    | string
    | null;

  parser_version?:
    | string
    | null;

  parse_error?:
    | string
    | null;

  parsed_at?:
    | string
    | null;


  // ==========================================================
  // Chunk
  // ==========================================================

  chunk_status: string;

  chunk_count: number;

  chunker_name?:
    | string
    | null;

  chunker_version?:
    | string
    | null;

  chunk_size_tokens?:
    | number
    | null;

  chunk_overlap_tokens?:
    | number
    | null;

  chunk_error?:
    | string
    | null;

  chunked_at?:
    | string
    | null;


  // ==========================================================
  // Embedding
  // ==========================================================

  embedding_status: string;

  embedding_count: number;

  embedding_provider?:
    | string
    | null;

  embedding_model?:
    | string
    | null;

  embedding_dimension?:
    | number
    | null;

  embedding_normalized?:
    | boolean
    | null;

  embedding_error?:
    | string
    | null;

  embedded_at?:
    | string
    | null;
}


// ============================================================
// Document List
// ============================================================

export interface PaperDocumentListResponse {
  items: PaperDocument[];

  total: number;
}