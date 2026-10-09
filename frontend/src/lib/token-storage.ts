const ACCESS_TOKEN_KEY =
  "research_agent_access_token";


// ============================================================
// Get Token
// ============================================================

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return localStorage.getItem(
    ACCESS_TOKEN_KEY,
  );
}


// ============================================================
// Save Token
// ============================================================

export function saveAccessToken(
  token: string,
): void {
  if (typeof window === "undefined") {
    return;
  }

  localStorage.setItem(
    ACCESS_TOKEN_KEY,
    token,
  );
}


// ============================================================
// Remove Token
// ============================================================

export function removeAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  localStorage.removeItem(
    ACCESS_TOKEN_KEY,
  );
}