import type {
  Paper,
} from "@/types/paper";


// ============================================================
// Project
// ============================================================

export interface Project {
  id: number;

  name: string;

  description?: string | null;

  owner_id: number;

  created_at: string;

  updated_at: string;
}


// ============================================================
// Create Project
// ============================================================

export interface CreateProjectRequest {
  name: string;

  description?: string | null;
}


// ============================================================
// Update Project
// ============================================================

export interface UpdateProjectRequest {
  name?: string | null;

  description?: string | null;
}


// ============================================================
// Project List Response
// ============================================================

export interface ProjectListResponse {
  items: Project[];

  total: number;

  page: number;

  page_size: number;

  pages: number;
}


// ============================================================
// Project List Query
// ============================================================

export interface ProjectListQuery {
  page?: number;

  page_size?: number;
}


// ============================================================
// Project Paper
// ============================================================

export interface ProjectPaper {
  paper: Paper;

  added_at: string;
}


// ============================================================
// Project Paper List Response
// ============================================================

export interface ProjectPaperListResponse {
  items: ProjectPaper[];

  total: number;

  page: number;

  page_size: number;

  pages: number;
}