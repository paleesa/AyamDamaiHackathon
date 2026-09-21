import { corpusStats as mockCorpusStats, mockEmails } from "./mock-data";
import { supabase } from "./supabase";
import type { ComparisonFieldRow, EmailRow } from "./supabase-types";
import type { EmailRecord } from "./types";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

/* ------------------------------------------------------------------ */
/* Row → domain mappers                                                */
/* ------------------------------------------------------------------ */

function toEmailRecord(row: EmailRow): EmailRecord {
  return {
    email_id: row.email_id,
    from: row.from_address,
    subject: row.subject,
    body: row.body,
    attachments: row.attachments ?? [],
    received_at: row.received_at,
    classification: {
      category: row.category,
      status: row.status,
      review_reason: row.review_reason,
      defect_fields: row.defect_fields ?? [],
      has_defect: row.has_defect,
    },
  };
}

/* ------------------------------------------------------------------ */
/* Emails                                                              */
/* ------------------------------------------------------------------ */

export async function getEmails(): Promise<EmailRecord[]> {
  if (USE_MOCK) return mockEmails;

  const { data, error } = await supabase
    .from("emails")
    .select("*")
    .order("received_at", { ascending: false, nullsFirst: false });

  if (error) throw error;
  return (data as EmailRow[]).map(toEmailRecord);
}

export async function getEmailById(
  emailId: string,
): Promise<EmailRecord | null> {
  if (USE_MOCK) {
    return mockEmails.find((email) => email.email_id === emailId) ?? null;
  }

  const { data, error } = await supabase
    .from("emails")
    .select("*")
    .eq("email_id", emailId)
    .maybeSingle();

  if (error) throw error;
  return data ? toEmailRecord(data as EmailRow) : null;
}

/* ------------------------------------------------------------------ */
/* Comparison fields — used by the (upcoming) comparison page          */
/* ------------------------------------------------------------------ */

export async function getComparisonFields(
  emailId: string,
): Promise<ComparisonFieldRow[]> {
  if (USE_MOCK) return [];

  const { data, error } = await supabase
    .from("comparison_fields")
    .select("*")
    .eq("email_id", emailId);

  if (error) throw error;
  return (data ?? []) as ComparisonFieldRow[];
}

/* ------------------------------------------------------------------ */
/* Dashboard aggregates                                                */
/* ------------------------------------------------------------------ */
/*                                                                     */
/* For now this still uses the mock corpus. When you want real numbers */
/* from Supabase, create a Postgres view or RPC — see the note below.  */
/* ------------------------------------------------------------------ */

export async function getCorpusStats(): Promise<typeof mockCorpusStats> {
  // TODO: replace with a Postgres view or an RPC call.
  return mockCorpusStats;
}