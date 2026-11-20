"use client";

/**
 * Session state for the whole app, backed by django-allauth's headless API
 * (https://docs.allauth.org/en/latest/headless/openapi-specification/).
 *
 *   const { user, isLoaded, isAuthenticated, login, logout } = useSession();
 *
 * There are no tokens to store: login sets Django's session cookie, and every
 * `apiFetch` call sends it automatically.
 */

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiFetch } from "./api";

const AUTH = "/_allauth/browser/v1/auth";

export interface SessionUser {
  id: number;
  email: string;
  username: string;
  display: string;
  has_usable_password: boolean;
}

export interface AuthError {
  message: string;
  code?: string;
  param?: string;
}

/** Outcome of a login/sign-up/verification call. */
export type AuthResult =
  | { ok: true }
  | { ok: false; pendingEmailVerification: true; errors?: undefined }
  | { ok: false; pendingEmailVerification?: false; errors: AuthError[] };

interface AllauthResponse {
  status: number;
  data?: {
    user?: SessionUser;
    flows?: { id: string; is_pending?: boolean }[];
  };
  meta?: { is_authenticated?: boolean };
  errors?: AuthError[];
}

interface SessionContextValue {
  user: SessionUser | null;
  /** False until the first session check has finished. */
  isLoaded: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<AuthResult>;
  signup: (email: string, password: string) => Promise<AuthResult>;
  logout: () => Promise<void>;
  verifyEmail: (key: string) => Promise<AuthResult>;
  requestPasswordReset: (email: string) => Promise<AuthResult>;
  resetPassword: (key: string, password: string) => Promise<AuthResult>;
  /** Re-reads the session from the server. */
  refresh: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

async function call(
  path: string,
  method: string,
  body?: unknown
): Promise<AllauthResponse> {
  const response = await apiFetch(`${AUTH}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  try {
    return (await response.json()) as AllauthResponse;
  } catch {
    return {
      status: response.status,
      errors: [{ message: "Unexpected response from the server." }],
    };
  }
}

function toResult(res: AllauthResponse): AuthResult {
  if (res.status === 200) return { ok: true };
  const pendingVerify = res.data?.flows?.some(
    (f) => f.id === "verify_email" && f.is_pending
  );
  if (pendingVerify) return { ok: false, pendingEmailVerification: true };
  return {
    ok: false,
    errors: res.errors?.length
      ? res.errors
      : [{ message: "Something went wrong. Please try again." }],
  };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const apply = useCallback((res: AllauthResponse) => {
    setUser(res.meta?.is_authenticated ? res.data?.user ?? null : null);
  }, []);

  const refresh = useCallback(async () => {
    try {
      apply(await call("/session", "GET"));
    } catch {
      setUser(null);
    } finally {
      setIsLoaded(true);
    }
  }, [apply]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const run = useCallback(
    async (path: string, body: unknown) => {
      try {
        const res = await call(path, "POST", body);
        apply(res);
        return toResult(res);
      } catch {
        return {
          ok: false as const,
          errors: [{ message: "Could not reach the server." }],
        };
      }
    },
    [apply]
  );

  const value = useMemo<SessionContextValue>(
    () => ({
      user,
      isLoaded,
      isAuthenticated: !!user,
      login: (email, password) => run("/login", { email, password }),
      signup: (email, password) => run("/signup", { email, password }),
      verifyEmail: (key) => run("/email/verify", { key }),
      requestPasswordReset: (email) => run("/password/request", { email }),
      // A successful reset ends the session (allauth answers 401), so treat
      // "no errors" as success here.
      resetPassword: async (key, password) => {
        try {
          const res = await call("/password/reset", "POST", { key, password });
          apply(res);
          if (res.status === 401 && !res.errors?.length) return { ok: true };
          return toResult(res);
        } catch {
          return { ok: false, errors: [{ message: "Could not reach the server." }] };
        }
      },
      logout: async () => {
        try {
          await call("/session", "DELETE");
        } finally {
          setUser(null);
        }
      },
      refresh,
    }),
    [user, isLoaded, run, refresh]
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside <SessionProvider>");
  return ctx;
}
