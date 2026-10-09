import {
  apiRequest,
} from "@/lib/api";

import type {
  CreateProjectRequest,
  Project,
  ProjectListQuery,
  ProjectListResponse,
  ProjectPaper,
  ProjectPaperListResponse,
  UpdateProjectRequest,
} from "@/types/project";


// ============================================================
// Query Builder
// ============================================================

function buildProjectQuery(
  query?: ProjectListQuery,
): string {
  if (!query) {
    return "";
  }

  const params =
    new URLSearchParams();


  if (query.page !== undefined) {
    params.set(
      "page",
      String(query.page),
    );
  }


  if (
    query.page_size !== undefined
  ) {
    params.set(
      "page_size",
      String(query.page_size),
    );
  }


  const queryString =
    params.toString();


  return queryString
    ? `?${queryString}`
    : "";
}


// ============================================================
// Project Page
// ============================================================

export async function getProjectsPage(
  query?: ProjectListQuery,
): Promise<ProjectListResponse> {
  const queryString =
    buildProjectQuery(
      query,
    );


  return apiRequest<ProjectListResponse>(
    `/projects/${queryString}`,
  );
}


// ============================================================
// Project List
// ============================================================
//
// 页面当前只需要 Project[]，
// 因此这里统一解包 items。
//
export async function listProjects(
  query?: ProjectListQuery,
): Promise<Project[]> {
  const response =
    await getProjectsPage(
      query,
    );


  return response.items;
}


// ============================================================
// Project Detail
// ============================================================

export async function getProject(
  projectId: number,
): Promise<Project> {
  return apiRequest<Project>(
    `/projects/${projectId}`,
  );
}


// ============================================================
// Create Project
// ============================================================

export async function createProject(
  data: CreateProjectRequest,
): Promise<Project> {
  return apiRequest<Project>(
    "/projects/",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify(
        data,
      ),
    },
  );
}


// ============================================================
// Update Project
// ============================================================

export async function updateProject(
  projectId: number,
  data: UpdateProjectRequest,
): Promise<Project> {
  return apiRequest<Project>(
    `/projects/${projectId}`,
    {
      method: "PATCH",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify(
        data,
      ),
    },
  );
}


// ============================================================
// Delete Project
// ============================================================

export async function deleteProject(
  projectId: number,
): Promise<void> {
  return apiRequest<void>(
    `/projects/${projectId}`,
    {
      method: "DELETE",
    },
  );
}


// ============================================================
// Project Paper Page
// ============================================================

export async function getProjectPapersPage(
  projectId: number,
  page = 1,
  pageSize = 100,
): Promise<ProjectPaperListResponse> {
  return apiRequest<ProjectPaperListResponse>(
    (
      `/projects/${projectId}/papers` +
      `?page=${page}` +
      `&page_size=${pageSize}`
    ),
  );
}


// ============================================================
// Project Papers
// ============================================================
//
// 后端返回：
//
// {
//   items: [
//     {
//       paper: {...},
//       added_at: "..."
//     }
//   ]
// }
//
// 页面目前直接使用 ProjectPaper[]。
//
export async function listProjectPapers(
  projectId: number,
): Promise<ProjectPaper[]> {
  const response =
    await getProjectPapersPage(
      projectId,
    );


  return response.items;
}


// ============================================================
// Add Paper
// ============================================================
//
// 当前页面不依赖具体 Response Body，
// 因此使用 unknown，避免凭空假设后端返回结构。
//
export async function addPaperToProject(
  projectId: number,
  paperId: number,
): Promise<unknown> {
  return apiRequest<unknown>(
    `/projects/${projectId}/papers/${paperId}`,
    {
      method: "POST",
    },
  );
}


// ============================================================
// Remove Paper
// ============================================================

export async function removePaperFromProject(
  projectId: number,
  paperId: number,
): Promise<unknown> {
  return apiRequest<unknown>(
    `/projects/${projectId}/papers/${paperId}`,
    {
      method: "DELETE",
    },
  );
}