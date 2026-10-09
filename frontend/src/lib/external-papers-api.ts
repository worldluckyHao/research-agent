import {
  apiRequest,
} from "@/lib/api";

import type {
  ExternalPaperSearchQuery,
  MultiSourcePaperSearchResponse,
  PaperImportJob,
  PaperImportRequest,
} from "@/types/external-paper";


// ============================================================
// External Paper Search
// ============================================================

export async function searchExternalPapers(
  query: ExternalPaperSearchQuery,
): Promise<MultiSourcePaperSearchResponse> {
  const params =
    new URLSearchParams();


  params.set(
    "query",
    query.query.trim(),
  );


  // FastAPI 的 list query parameter
  // 使用重复 key：
  //
  // providers=openalex
  // &providers=arxiv
  //
  query.providers?.forEach(
    (provider) => {
      params.append(
        "providers",
        provider,
      );
    },
  );


  if (
    query.limit !== undefined
  ) {
    params.set(
      "limit",
      String(query.limit),
    );
  }


  if (query.sort) {
    params.set(
      "sort",
      query.sort,
    );
  }


  return apiRequest<
    MultiSourcePaperSearchResponse
  >(
    (
      "/external/papers/search?" +
      params.toString()
    ),
  );
}


// ============================================================
// Create Import Job
// ============================================================

export async function createPaperImportJob(
  data: PaperImportRequest,
): Promise<PaperImportJob> {
  return apiRequest<
    PaperImportJob
  >(
    "/external/papers/import-jobs",
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
// Get Import Job
// ============================================================

export async function getPaperImportJob(
  jobId: string,
): Promise<PaperImportJob> {
  return apiRequest<
    PaperImportJob
  >(
    (
      "/external/papers/" +
      `import-jobs/${jobId}`
    ),
  );
}


// ============================================================
// Wait For Import
// ============================================================
//
// 不假设后端 status 的具体枚举。
// 使用真实业务字段判断：
//
// paper_id     → 已成功产生 Paper
// error_message → 导入失败
//
// 最大等待约 60 秒。
//
export async function waitForPaperImport(
  jobId: string,
): Promise<PaperImportJob> {
  const maxAttempts = 40;

  const intervalMs = 1500;


  for (
    let attempt = 0;
    attempt < maxAttempts;
    attempt += 1
  ) {
    const job =
      await getPaperImportJob(
        jobId,
      );


    if (
      job.paper_id !== null &&
      job.paper_id !== undefined
    ) {
      return job;
    }


    if (job.error_message) {
      throw new Error(
        job.error_message,
      );
    }


    await new Promise<void>(
      (resolve) => {
        window.setTimeout(
          resolve,
          intervalMs,
        );
      },
    );
  }


  throw new Error(
    "论文导入任务未在预期时间内完成，请稍后刷新论文库查看。",
  );
}