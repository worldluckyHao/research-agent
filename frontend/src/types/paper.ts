// ============================================================
// Paper
// ============================================================

export interface Paper {
  id: number;

  title: string;

  authors: string[];

  year: number;

  abstract?: string | null;

  keywords?: string[];

  language?: string;

  doi?: string | null;

  url?: string | null;

  source?: string | null;
}


// ============================================================
// Create Paper
// ============================================================

export interface CreatePaperRequest {
  title: string;

  authors: string[];

  year: number;

  abstract?: string;

  keywords?: string[];

  language?: string;

  doi?: string;

  url?: string;

  source?: string;
}

// ============================================================
// Paper List Response
// ============================================================

export interface PaperListResponse {
  items: Paper[];

  total: number;

  page: number;

  page_size: number;

  pages: number;
}


// ============================================================
// Paper List Query
// ============================================================

export interface PaperListQuery {
  page?: number;

  page_size?: number;

  year?: number;

  source?: string;

  search?: string;

  sort_by?:
    | "id"
    | "title"
    | "year"
    | "created_at"
    | "updated_at";

  sort_order?:
    | "asc"
    | "desc";
}