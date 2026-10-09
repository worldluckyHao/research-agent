import {
  apiRequest,
} from "@/lib/api";

import type {
  CreatePaperRequest,
  Paper,
  PaperListQuery,
  PaperListResponse,
} from "@/types/paper";


// ============================================================
// Build Query String
// ============================================================

function buildPaperQuery(
  query?: PaperListQuery,
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
      String(
        query.page_size,
      ),
    );
  }


  if (query.year !== undefined) {
    params.set(
      "year",
      String(query.year),
    );
  }


  if (query.source) {
    params.set(
      "source",
      query.source,
    );
  }


  if (query.search) {
    params.set(
      "search",
      query.search,
    );
  }


  if (query.sort_by) {
    params.set(
      "sort_by",
      query.sort_by,
    );
  }


  if (query.sort_order) {
    params.set(
      "sort_order",
      query.sort_order,
    );
  }


  const queryString =
    params.toString();


  return queryString
    ? `?${queryString}`
    : "";
}


// ============================================================
// List Page
// ============================================================
//
// 保留完整分页信息。
// 后面真正制作分页 UI 时直接使用这个方法。
//
export async function getPapersPage(
  query?: PaperListQuery,
): Promise<PaperListResponse> {
  const queryString =
    buildPaperQuery(
      query,
    );


  return apiRequest<PaperListResponse>(
    `/papers/${queryString}`,
  );
}


// ============================================================
// List Papers
// ============================================================
//
// 页面当前只关心 Paper[]，
// 因此 API Layer 在这里统一解包 response.items。
//
export async function listPapers(
  query?: PaperListQuery,
): Promise<Paper[]> {
  const response =
    await getPapersPage(
      query,
    );


  return response.items;
}


// ============================================================
// Detail
// ============================================================

export async function getPaper(
  paperId: number,
): Promise<Paper> {
  return apiRequest<Paper>(
    `/papers/${paperId}`,
  );
}


// ============================================================
// Create
// ============================================================

export async function createPaper(
  data: CreatePaperRequest,
): Promise<Paper> {
  return apiRequest<Paper>(
    "/papers/",
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
// Delete
// ============================================================

export async function deletePaper(
  paperId: number,
): Promise<void> {
  return apiRequest<void>(
    `/papers/${paperId}`,
    {
      method: "DELETE",
    },
  );
}