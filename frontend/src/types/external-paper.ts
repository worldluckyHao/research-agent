// ============================================================
// Provider
// ============================================================

export type PaperProvider =
  | "openalex"
  | "arxiv"
  | "crossref";


export type PaperSearchSort =
  | "relevance"
  | "newest"
  | "cited";


// ============================================================
// Unified Paper Metadata
// ============================================================
//
// 后端只有 provider / provider_id / title 是必填字段。
// 其余字段可能因 Provider 不同而缺失。
//
export interface UnifiedPaperMetadata {
  provider: string;

  provider_id: string;

  sources?: string[];

  provider_ids?: Record<
    string,
    string
  >;

  title: string;

  authors?: string[];

  abstract?: string | null;

  year?: number | null;

  publication_date?:
    | string
    | null;

  doi?: string | null;

  arxiv_id?:
    | string
    | null;

  url?: string | null;

  pdf_url?: string | null;

  venue?: string | null;

  cited_by_count?: number;

  is_open_access?:
    | boolean
    | null;

  language?: string | null;

  topics?: string[];
}


// ============================================================
// Search
// ============================================================

export interface ExternalPaperSearchQuery {
  query: string;

  providers?: PaperProvider[];

  limit?: number;

  sort?: PaperSearchSort;
}


export interface MultiSourcePaperSearchResponse {
  query: string;

  providers: string[];

  failed_providers?: string[];

  candidate_count: number;

  unique_count: number;

  items: UnifiedPaperMetadata[];
}


// ============================================================
// Import
// ============================================================

export interface PaperImportRequest {
  paper: UnifiedPaperMetadata;

  project_id?: number | null;
}


export interface PaperImportJob {
  id: string;

  status: string;

  project_id?:
    | number
    | null;

  paper_id?:
    | number
    | null;

  error_message?:
    | string
    | null;

  created_at: string;

  updated_at: string;
}