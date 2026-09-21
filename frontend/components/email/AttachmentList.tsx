import { FileText } from "lucide-react";

type AttachmentKind = "SI" | "BL" | "INVOICE" | "OTHER";

const KIND_STYLE: Record<AttachmentKind, { label: string; className: string }> = {
  SI: {
    label: "SI",
    className: "border-violet-200 bg-violet-50 text-violet-700",
  },
  BL: {
    label: "BL",
    className: "border-indigo-200 bg-indigo-50 text-indigo-700",
  },
  INVOICE: {
    label: "INVOICE",
    className: "border-cyan-200 bg-cyan-50 text-cyan-700",
  },
  OTHER: {
    label: "FILE",
    className: "border-slate-200 bg-slate-100 text-slate-600",
  },
};

function basename(path: string): string {
  return path.split("/").pop() ?? path;
}

function attachmentKind(path: string): AttachmentKind {
  const base = basename(path).toLowerCase().replace(/\.[a-z0-9]+$/, "");

  if (/(^|[_\-.])si($|[_\-.])/.test(base)) return "SI";
  if (/(^|[_\-.])bl($|[_\-.])/.test(base)) return "BL";
  if (/invoice|(^|[_\-.])inv($|[_\-.])/.test(base)) return "INVOICE";
  return "OTHER";
}

export default function AttachmentList({
  attachments,
}: {
  attachments: string[];
}) {
  return (
    <section className="rounded-sm border border-slate-200 bg-white">
      <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
        <p className="text-xs font-medium text-slate-500">
          Attachments
        </p>
        <span className="font-mono text-xs text-slate-400">
          {attachments.length}
        </span>
      </header>

      {attachments.length === 0 ? (
        <p className="px-5 py-6 text-sm text-slate-500">
          No attachments on this message.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {attachments.map((path) => {
            const kind = attachmentKind(path);
            const style = KIND_STYLE[kind];
            const name = basename(path);

            return (
              <li
                key={path}
                className="flex items-center gap-3 px-5 py-3"
              >
                <FileText
                  className="h-4 w-4 shrink-0 text-slate-400"
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-700">
                  {name}
                </span>
                <span
                  className={`inline-flex items-center whitespace-nowrap rounded-sm border px-1.5 py-0.5 font-mono text-[10px] font-medium ${style.className}`}
                >
                  {style.label}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}