import { corpusStats, mockEmails } from "./mock-data";
import type { EmailRecord } from "./types";

const USE_MOCK = true;
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`SDOC API error ${res.status} on ${path}`);
  }
  return (await res.json()) as T;
}

export async function getEmails(): Promise<EmailRecord[]> {
  if (USE_MOCK) return mockEmails;
  return request<EmailRecord[]>("/emails");
}

export async function getEmailById(
  emailId: string,
): Promise<EmailRecord | null> {
  if (USE_MOCK) {
    return mockEmails.find((email) => email.email_id === emailId) ?? null;
  }
  return request<EmailRecord>(`/emails/${emailId}`);
}

export async function getCorpusStats(): Promise<typeof corpusStats> {
  if (USE_MOCK) return corpusStats;
  return request<typeof corpusStats>("/stats");
}