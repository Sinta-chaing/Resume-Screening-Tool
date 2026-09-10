import type { AnalyzeResponse, ChatResponse, RecordDetail, RecordsListResponse } from "@/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

async function parseJsonResponse<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new Error(`Backend returned an invalid response (HTTP ${response.status})`);
  }
}

function wrapFetchError(error: unknown): Error {
  if (error instanceof Error) {
    if (error.message === "Failed to fetch") {
      return new Error(
        `Cannot reach backend at ${API_URL}. Ensure Django is running (python manage.py runserver 4000) and CORS allows your frontend origin.`
      );
    }
    return error;
  }
  return new Error("Request failed");
}

export async function analyzeResume(
  resume: File,
  jd: File
): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("resume", resume);
  form.append("jd", jd);

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/analyze`, {
      method: "POST",
      body: form,
    });
  } catch (error) {
    throw wrapFetchError(error);
  }

  const json = await parseJsonResponse<AnalyzeResponse>(response);
  if (!response.ok || !json.ok) {
    throw new Error(json.error || "Analyze failed");
  }
  return json;
}

export async function askQuestion(
  question: string,
  sessionId: string
): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, sessionId }),
    });
  } catch (error) {
    throw wrapFetchError(error);
  }

  const json = await parseJsonResponse<ChatResponse>(response);
  if (!response.ok || !json.ok) {
    throw new Error(json.error || "chat failed");
  }
  return json;
}

export async function fetchRecords(order: "asc" | "desc" = "asc"): Promise<RecordsListResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/records?order=${order}`);
  } catch (error) {
    throw wrapFetchError(error);
  }

  const json = await parseJsonResponse<RecordsListResponse>(response);
  if (!response.ok || !json.ok) {
    throw new Error(json.error || "Failed to load records");
  }
  return json;
}

export async function fetchRecord(sessionId: string): Promise<RecordDetail> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/records/${sessionId}`);
  } catch (error) {
    throw wrapFetchError(error);
  }

  const json = await parseJsonResponse<RecordDetail>(response);
  if (!response.ok || !json.ok) {
    throw new Error(json.error || "Failed to load record");
  }
  return json;
}

export async function deleteRecord(sessionId: string): Promise<{ ok: boolean; id: string }> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/records/${sessionId}`, {
      method: "DELETE",
    });
  } catch (error) {
    throw wrapFetchError(error);
  }

  const json = await parseJsonResponse<{ ok: boolean; id: string; error?: string }>(response);
  if (!response.ok || !json.ok) {
    throw new Error(json.error || "Failed to delete record");
  }
  return json;
}
