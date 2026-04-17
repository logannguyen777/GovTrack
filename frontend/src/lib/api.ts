/**
 * GovFlow API client — production-grade fetch wrapper.
 *
 * Status-aware handling:
 *   401 → clear token + queryClient + redirect to /auth/login?next=<path>
 *   403 → toast "Bạn không có quyền thực hiện thao tác này"
 *   429 → toast with Retry-After countdown
 *   500/502/503/504 → toast + exponential-backoff retry (GET only, max 2)
 *   Network failure → toast "Không thể kết nối máy chủ"
 *
 * Request timeout: 30 seconds via AbortController.
 */

import { toast } from "sonner";
import { getQueryClient } from "@/components/providers/query-provider";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API ${status}: ${JSON.stringify(body)}`);
  }
}

// ---------------------------------------------------------------------------
// 401 callback — registered by AuthProvider on mount so we avoid a circular
// import between api.ts and auth-provider.tsx.
// ---------------------------------------------------------------------------

type UnauthorizedHandler = (currentPath: string) => void;
let _onUnauthorized: UnauthorizedHandler | null = null;

export function registerUnauthorizedHandler(fn: UnauthorizedHandler): void {
  _onUnauthorized = fn;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

const REQUEST_TIMEOUT_MS = 30_000;
const RETRYABLE_STATUSES = new Set([500, 502, 503, 504]);

async function apiFetch<T>(
  path: string,
  options: {
    method?: HttpMethod;
    body?: unknown;
    params?: Record<string, string>;
    /** Current attempt index (0-based); used for retry backoff. */
    _attempt?: number;
  } = {},
): Promise<T> {
  const { method = "GET", body, params, _attempt = 0 } = options;

  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("govflow-token")
      : null;

  const base =
    typeof window !== "undefined" ? window.location.origin : "http://localhost:3100";
  const url = new URL(path, base);
  if (params)
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  // 30-second request timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(url.toString(), {
      method,
      headers,
      signal: controller.signal,
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (err) {
    clearTimeout(timeoutId);
    const isAbort =
      err instanceof DOMException && err.name === "AbortError";
    toast.error(
      isAbort
        ? "Yêu cầu mất quá nhiều thời gian, vui lòng thử lại."
        : "Không thể kết nối máy chủ.",
    );
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!res.ok) {
    const bodyData = await res.json().catch(() => null);

    // --- 401: clear auth state, dispatch event, redirect to login ---
    if (res.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("govflow-token");
        localStorage.removeItem("govflow-user");
        // Clear all cached server state so stale data doesn't linger.
        try { getQueryClient().clear(); } catch { /* noop if not yet initialised */ }
        // Notify WS manager and any other listeners.
        window.dispatchEvent(new CustomEvent("auth:expired"));
      }
      const currentPath =
        typeof window !== "undefined" ? window.location.pathname : "/";
      _onUnauthorized?.(currentPath);
      throw new ApiError(401, bodyData);
    }

    // --- 403: no permission toast ---
    if (res.status === 403) {
      toast.error("Bạn không có quyền thực hiện thao tác này.");
      throw new ApiError(403, bodyData);
    }

    // --- 429: rate limit toast with Retry-After ---
    if (res.status === 429) {
      const retryAfter = res.headers.get("Retry-After");
      const seconds = retryAfter ? parseInt(retryAfter, 10) : null;
      toast.warning(
        seconds && !isNaN(seconds)
          ? `Quá nhiều yêu cầu, vui lòng thử lại sau ${seconds} giây.`
          : "Quá nhiều yêu cầu, vui lòng thử lại sau.",
      );
      throw new ApiError(429, bodyData);
    }

    // --- 5xx: retry idempotent methods up to 2 times ---
    if (RETRYABLE_STATUSES.has(res.status)) {
      if (method === "GET" && _attempt < 2) {
        const delay = Math.min(1000 * 2 ** (_attempt + 1), 8000);
        await new Promise((r) => setTimeout(r, delay));
        return apiFetch<T>(path, { method, body, params, _attempt: _attempt + 1 });
      }
      toast.error("Lỗi hệ thống, vui lòng thử lại.");
      throw new ApiError(res.status, bodyData);
    }

    throw new ApiError(res.status, bodyData);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API surface
// ---------------------------------------------------------------------------

export const apiClient = {
  get: <T>(path: string, params?: Record<string, string>) =>
    apiFetch<T>(path, { params }),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body }),
  put: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};
