import type { ApiError } from "./types";

export class HttpError extends Error {
  status: number;
  details?: { field: string; message: string }[];

  constructor(message: string, status: number, details?: { field: string; message: string }[]) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

async function parseError(response: Response): Promise<HttpError> {
  try {
    const body = (await response.json()) as ApiError;
    return new HttpError(body.error?.message || "Request failed", response.status, body.error?.details);
  } catch {
    return new HttpError("Request failed", response.status);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 204) {
    return undefined as T;
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.blob()) as T;
}

export function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}
