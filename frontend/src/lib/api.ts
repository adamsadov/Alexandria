/**
 * The one way the frontend talks to the Django backend.
 *
 * Requests use relative URLs (`/api/...`, `/_allauth/...`). Next.js forwards
 * them to Django (see next.config.ts), so the browser sees a single origin and
 * the Django session cookie set at login is sent automatically.
 *
 * Writes (POST/PUT/PATCH/DELETE) carry Django's CSRF token in X-CSRFToken.
 * `apiFetch` returns the normal fetch Response, so callers keep using
 * `response.ok`, `response.status` and `response.json()`.
 */

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
}

let csrfRequest: Promise<void> | null = null;

/** Returns the CSRF token, asking Django to set the cookie the first time. */
export async function getCsrfToken(): Promise<string | null> {
  let token = readCookie("csrftoken");
  if (token) return token;
  if (!csrfRequest) {
    csrfRequest = fetch("/api/auth/csrf/", { credentials: "same-origin" })
      .then(() => undefined)
      .finally(() => {
        csrfRequest = null;
      });
  }
  await csrfRequest;
  token = readCookie("csrftoken");
  return token;
}

export async function apiFetch(
  input: string,
  init: RequestInit = {}
): Promise<Response> {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);

  if (UNSAFE_METHODS.has(method)) {
    const csrf = await getCsrfToken();
    if (csrf) headers.set("X-CSRFToken", csrf);
  }

  return fetch(input, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
  });
}

/** Turns a stored media path (e.g. "/media/profile_pics/x.png") into a usable src. */
export function mediaUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return path.startsWith("/") ? path : `/${path}`;
}
