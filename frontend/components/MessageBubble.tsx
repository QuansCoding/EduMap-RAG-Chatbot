import type { Citation, Message } from "@/lib/types";

type BubbleMessage = Pick<Message, "sender" | "content" | "key_points" | "citations" | "found_in_materials">;

interface Props {
  message: BubbleMessage;
  onShare?: () => void;
  shared?: boolean;
}

export default function MessageBubble({ message, onShare, shared }: Props) {
  if (message.sender === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] space-y-3 rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3">
        {message.found_in_materials === false && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            ⚠️ Not found in your course materials. This answer uses general knowledge, so double-check it
            against your textbook or instructor.
          </div>
        )}

        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>

        {message.key_points.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Key points</p>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
              {message.key_points.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          </div>
        )}

        <CitationList citations={message.citations} />

        {onShare && (
          <button
            onClick={onShare}
            disabled={shared}
            className="text-xs text-indigo-600 hover:underline disabled:text-slate-400 disabled:no-underline"
          >
            {shared ? "✓ Shared with group" : "Share with group"}
          </button>
        )}
      </div>
    </div>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</p>
      <ul className="mt-1 space-y-1">
        {citations.map((c) => (
          <li key={c.source_number}>
            {/* <details> is a native HTML expand/collapse; no JavaScript needed */}
            <details className="rounded-md bg-slate-50 px-2 py-1 text-xs">
              <summary className="cursor-pointer">
                [{c.source_number}] {c.document_title} · page {c.page_number}
              </summary>
              <p className="mt-1 whitespace-pre-wrap text-slate-600">“{c.snippet}…”</p>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}