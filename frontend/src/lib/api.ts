type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API ${status}: ${JSON.stringify(body)}`);
  }
}

async function api<T>(
  path: string,
  options: {
    method?: HttpMethod;
    body?: unknown;
    params?: Record<string, string>;
  } = {},
): Promise<T> {
  const { method = "GET", body, params } = options;
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("govflow-token")
      : null;

  const url = new URL(path, window.location.origin);
  if (params)
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url.toString(), {
    method,
    headers,
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  if (!res.ok)
    throw new ApiError(
      res.status,
      await res.json().catch(() => null),
    );
  return res.json();
}

export const apiClient = {
  get: <T>(path: string, params?: Record<string, string>) =>
    api<T>(path, { params }),
  post: <T>(path: string, body?: unknown) =>
    api<T>(path, { method: "POST", body }),
  put: <T>(path: string, body: unknown) =>
    api<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) =>
    api<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => api<T>(path, { method: "DELETE" }),
};
