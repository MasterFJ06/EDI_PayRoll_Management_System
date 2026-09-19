// Centralized FastAPI client. All application HTTP traffic goes through here.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/$/, "");
export const USE_MOCKS = String(import.meta.env.VITE_USE_MOCKS ?? "true").toLowerCase() === "true";
export const AUTH_LOGIN_MODE = (import.meta.env.VITE_AUTH_LOGIN_MODE ?? "json") as "json" | "form";

export class ApiError extends Error {
  status: number;
  details?: unknown;
  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.details = details;
    this.name = "ApiError";
  }
}

function getToken(): string | null {
  return localStorage.getItem("epms_access_token") ?? sessionStorage.getItem("epms_access_token");
}

async function parseError(res: Response): Promise<never> {
  const body = await res.json().catch(() => null) as any;
  const detail = body?.detail;
  const message = Array.isArray(detail)
    ? detail.map((x) => x?.msg).filter(Boolean).join("; ")
    : typeof detail === "string" ? detail : body?.message;

  if (res.status === 401) {
    localStorage.removeItem("epms_access_token");
    sessionStorage.removeItem("epms_access_token");
    localStorage.removeItem("epms_user");
    sessionStorage.removeItem("epms_user");
    window.dispatchEvent(new CustomEvent("epms:session-expired"));
  }

  const fallback: Record<number, string> = {
    400: "The request could not be completed.",
    401: "Session expired. Please sign in again.",
    403: "You do not have permission to perform this action.",
    404: "The requested record was not found.",
    409: "This record already exists or conflicts with another record.",
    422: "Some fields are invalid. Please check the form.",
  };
  throw new ApiError(res.status, message || fallback[res.status] || (res.status >= 500 ? "Server error. Please try again shortly." : "Something went wrong."), body);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const isForm = options.body instanceof URLSearchParams || options.body instanceof FormData;
  const headers = new Headers(options.headers);
  if (!isForm && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, `Cannot reach the FastAPI server at ${API_BASE_URL}. Start the backend or enable VITE_USE_MOCKS=true.`);
  }

  if (!res.ok) await parseError(res);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  try { return JSON.parse(text) as T; } catch { return text as T; }
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, values: Record<string, string>) => request<T>(path, {
    method: "POST",
    body: new URLSearchParams(values),
  }),
};

export function mockDelay<T>(value: T, ms = 350): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}
