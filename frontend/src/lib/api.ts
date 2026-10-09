import {
  getAccessToken,
} from "@/lib/token-storage";


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1";


// ============================================================
// API Error
// ============================================================

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(
    message: string,
    status: number,
    code?: string,
  ) {
    super(message);

    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}


// ============================================================
// Options
// ============================================================

interface ApiRequestOptions
  extends RequestInit {
  auth?: boolean;
}


// ============================================================
// Parse Error
// ============================================================

async function extractErrorMessage(
  response: Response,
): Promise<{
  message: string;
  code?: string;
}> {
  try {
    const data = await response.json();

    // 项目自己的统一异常格式：
    //
    // {
    //   "code": "...",
    //   "message": "..."
    // }
    if (
      typeof data?.message === "string"
    ) {
      return {
        message: data.message,
        code: data.code,
      };
    }

    // FastAPI 默认：
    //
    // {
    //   "detail": "..."
    // }
    if (
      typeof data?.detail === "string"
    ) {
      return {
        message: data.detail,
      };
    }

    // Pydantic Validation Error。
    if (
      Array.isArray(data?.detail)
    ) {
      return {
        message:
          data.detail
            .map(
              (item: {
                msg?: string;
              }) => item.msg,
            )
            .filter(Boolean)
            .join("; ") ||
          "Request validation failed.",
      };
    }
  } catch {
    // Response 不是 JSON 时继续使用默认错误。
  }

  return {
    message:
      `Request failed with status ${response.status}.`,
  };
}


// ============================================================
// Request
// ============================================================

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    auth = true,
    headers,
    ...requestInit
  } = options;

  const requestHeaders =
    new Headers(headers);


  // ----------------------------------------------------------
  // JWT
  // ----------------------------------------------------------

  if (auth) {
    const token =
      getAccessToken();

    if (token) {
      requestHeaders.set(
        "Authorization",
        `Bearer ${token}`,
      );
    }
  }


  // ----------------------------------------------------------
  // Request
  // ----------------------------------------------------------

  const response =
    await fetch(
      `${API_BASE_URL}${path}`,
      {
        ...requestInit,
        headers: requestHeaders,
      },
    );


  // ----------------------------------------------------------
  // Error
  // ----------------------------------------------------------

  if (!response.ok) {
    const error =
      await extractErrorMessage(
        response,
      );

    throw new ApiError(
      error.message,
      response.status,
      error.code,
    );
  }


  // 204 No Content。
  if (
    response.status === 204
  ) {
    return undefined as T;
  }


  return response.json() as Promise<T>;
}