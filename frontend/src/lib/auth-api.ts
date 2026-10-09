import {
  apiRequest,
} from "@/lib/api";

import type {
  RegisterRequest,
  TokenResponse,
  User,
} from "@/types/auth";


// ============================================================
// Login
// ============================================================

export async function loginRequest(
  username: string,
  password: string,
): Promise<TokenResponse> {
  const form =
    new URLSearchParams();

  // FastAPI OAuth2PasswordRequestForm
  // 使用 username / password。
  form.set(
    "username",
    username,
  );

  form.set(
    "password",
    password,
  );


  return apiRequest<TokenResponse>(
    "/auth/login",
    {
      method: "POST",

      auth: false,

      headers: {
        "Content-Type":
          "application/x-www-form-urlencoded",
      },

      body: form.toString(),
    },
  );
}


// ============================================================
// Register
// ============================================================

export async function registerRequest(
  data: RegisterRequest,
): Promise<User> {
  return apiRequest<User>(
    "/users/register",
    {
      method: "POST",

      auth: false,

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
// Current User
// ============================================================

export async function getCurrentUser(
): Promise<User> {
  return apiRequest<User>(
    "/users/me",
  );
}