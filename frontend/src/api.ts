export type Source = {
  id: string;
  text: string;
  score: number;
  metadata?: {
    path?: string;
    chunk?: number;
    document_id?: string;
    [key: string]: unknown;
  } | null;
};

export type QueryResult = { answer: string; sources: Source[] };
export type UploadResult = {
  filename: string;
  chunks: number;
  document_id: string;
};

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body) {
        const value = (body as { detail: unknown }).detail;
        detail = typeof value === "string" ? value : JSON.stringify(value);
      }
    } catch {
      /* API unavailable or non-JSON response */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const result = await fetch("/api/health");
    return result.ok;
  } catch {
    return false;
  }
}

export async function ask(
  question: string,
  useRag: boolean,
): Promise<QueryResult> {
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, use_rag: useRag }),
  });
  return parseResponse<QueryResult>(response);
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/upload", { method: "POST", body: form });
  return parseResponse<UploadResult>(response);
}
