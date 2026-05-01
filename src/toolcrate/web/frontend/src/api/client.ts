export interface ProblemJson {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  code?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  readonly title: string | undefined;
  readonly detail: string | undefined;
  readonly raw: unknown;

  constructor(status: number, body: ProblemJson | string | undefined) {
    const title = typeof body === "object" && body ? body.title : undefined;
    const detail = typeof body === "object" && body ? body.detail : undefined;
    super(`${status} ${title ?? "request failed"}${detail ? `: ${detail}` : ""}`);
    this.name = "ApiError";
    this.status = status;
    this.code = typeof body === "object" && body ? body.code : undefined;
    this.title = title;
    this.detail = detail;
    this.raw = body;
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: BodyInit | null;
}

export async function apiFetch<T = unknown>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  if (options.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  if (!headers.has("accept")) {
    headers.set("accept", "application/json");
  }

  const resp = await fetch(path, {
    ...options,
    headers,
    credentials: options.credentials ?? "include",
  });

  if (resp.status === 204) {
    return null as T;
  }

  const contentType = resp.headers.get("content-type") ?? "";
  const isJson = contentType.includes("json");
  const body = isJson ? await resp.json().catch(() => undefined) : await resp.text().catch(() => "");

  if (!resp.ok) {
    throw new ApiError(resp.status, body as ProblemJson | string | undefined);
  }
  return body as T;
}
