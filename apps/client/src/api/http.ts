// Minimal JSON client for the Tilsim API. Errors always arrive as ApiError with a
// stable code: the server's own code (see apps/api, errors.py), or "network".

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  token?: string | null;
  timeoutMs?: number;
}

export function normaliseBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

export function isValidBaseUrl(url: string): boolean {
  try {
    const parsed = new URL(normaliseBaseUrl(url));
    // Plain http only for a local development server.
    return parsed.protocol === "https:" || (parsed.protocol === "http:" && ["localhost", "127.0.0.1"].includes(parsed.hostname));
  } catch {
    return false;
  }
}

export async function request<T>(baseUrl: string, path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.token) headers.Authorization = `Bearer ${options.token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? 20_000);
  let response: Response;
  try {
    response = await fetch(normaliseBaseUrl(baseUrl) + path, {
      method: options.method ?? (options.body === undefined ? "GET" : "POST"),
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });
  } catch (error) {
    throw new ApiError(0, "network", error instanceof Error ? error.message : String(error));
  } finally {
    clearTimeout(timer);
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new ApiError(response.status, "invalid_response", "the server did not return JSON");
    }
  }
  if (!response.ok) {
    const error = (data as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(response.status, error?.code ?? "http_error", error?.message ?? `HTTP ${response.status}`);
  }
  return data as T;
}
