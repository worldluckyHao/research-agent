// ============================================================
// Token
// ============================================================

export interface TokenResponse {
  access_token: string;
  token_type: string;
}


// ============================================================
// User
// ============================================================

export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}


// ============================================================
// Register
// ============================================================

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}


// ============================================================
// Auth Context
// ============================================================

export interface AuthContextValue {
  user: User | null;
  loading: boolean;

  login: (
    username: string,
    password: string,
  ) => Promise<void>;

  register: (
    data: RegisterRequest,
  ) => Promise<void>;

  logout: () => void;
}