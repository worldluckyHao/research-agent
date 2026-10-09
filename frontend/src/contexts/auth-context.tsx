"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  getCurrentUser,
  loginRequest,
  registerRequest,
} from "@/lib/auth-api";

import {
  getAccessToken,
  removeAccessToken,
  saveAccessToken,
} from "@/lib/token-storage";

import type {
  AuthContextValue,
  RegisterRequest,
  User,
} from "@/types/auth";


// ============================================================
// Context
// ============================================================

const AuthContext =
  createContext<AuthContextValue | null>(
    null,
  );


// ============================================================
// Provider
// ============================================================

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [
    user,
    setUser,
  ] = useState<User | null>(
    null,
  );

  const [
    loading,
    setLoading,
  ] = useState(true);


  // ----------------------------------------------------------
  // Restore Login
  // ----------------------------------------------------------

  useEffect(() => {
    async function restoreAuth() {
      const token =
        getAccessToken();

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const currentUser =
          await getCurrentUser();

        setUser(
          currentUser,
        );
      } catch {
        removeAccessToken();

        setUser(
          null,
        );
      } finally {
        setLoading(false);
      }
    }

    void restoreAuth();
  }, []);


  // ----------------------------------------------------------
  // Login
  // ----------------------------------------------------------

  async function login(
    username: string,
    password: string,
  ): Promise<void> {
    const token =
      await loginRequest(
        username,
        password,
      );

    saveAccessToken(
      token.access_token,
    );

    try {
      const currentUser =
        await getCurrentUser();

      setUser(
        currentUser,
      );
    } catch (error) {
      removeAccessToken();

      throw error;
    }
  }


  // ----------------------------------------------------------
  // Register
  // ----------------------------------------------------------

  async function register(
    data: RegisterRequest,
  ): Promise<void> {
    await registerRequest(
      data,
    );

    // 注册成功后自动登录。
    await login(
      data.username,
      data.password,
    );
  }


  // ----------------------------------------------------------
  // Logout
  // ----------------------------------------------------------

  function logout(): void {
    removeAccessToken();

    setUser(
      null,
    );
  }


  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


// ============================================================
// Hook
// ============================================================

export function useAuth(): AuthContextValue {
  const context =
    useContext(
      AuthContext,
    );

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider.",
    );
  }

  return context;
}