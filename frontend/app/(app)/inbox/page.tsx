import InboxTable from "@/components/email/InboxTable";
import { getEmails } from "@/lib/api";

export const metadata = { title: "Inbox" };

export default async function InboxPage() {
  const emails = await getEmails();

  return <InboxTable emails={emails} />;
}