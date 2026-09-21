import { createClient } from "@supabase/supabase-js";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const url = process.env.SUPABASE_URL;
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!url || !serviceKey) {
  console.error(
    "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running.\n" +
      "The service role key is in Supabase → Project Settings → API.",
  );
  process.exit(1);
}

const supabase = createClient(url, serviceKey, {
  auth: { persistSession: false },
});

// Adjust these paths if your data lives elsewhere.
const repoRoot = path.resolve(__dirname, "../..");
const emailsDir = path.join(repoRoot, "data", "emails");
const classificationPath = path.join(repoRoot, "data", "classification.json");

const classification = JSON.parse(
  await readFile(classificationPath, "utf8"),
);

const entries = await readdir(emailsDir);
const rows = [];

for (const entry of entries) {
  if (!entry.endsWith(".json")) continue;

  const raw = await readFile(path.join(emailsDir, entry), "utf8");
  const email = JSON.parse(raw);
  const c = classification[email.email_id];

  if (!c) {
    console.warn(`skip ${entry} — no classification for ${email.email_id}`);
    continue;
  }

  rows.push({
    email_id: email.email_id,
    from_address: email.from,
    subject: email.subject,
    body: email.body,
    received_at: email.received_at ?? null,
    attachments: email.attachments ?? [],
    category: c.category,
    status: c.status,
    review_reason: c.review_reason,
    defect_fields: c.defect_fields ?? [],
    has_defect: c.has_defect,
  });
}

console.log(`Prepared ${rows.length} rows.`);

const CHUNK = 100;

for (let i = 0; i < rows.length; i += CHUNK) {
  const chunk = rows.slice(i, i + CHUNK);
  const { error } = await supabase.from("emails").upsert(chunk);

  if (error) {
    console.error("Insert failed:", error);
    process.exit(1);
  }

  console.log(`Inserted ${i + chunk.length}/${rows.length}`);
}

console.log("Done.");