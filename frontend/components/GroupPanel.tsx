"use client";

import { useCallback, useEffect, useState } from "react";
import MessageBubble from "@/components/MessageBubble";
import { api, errorMessage } from "@/lib/api";
import type { SharedInsight, WorkspaceDetail } from "@/lib/types";

export default function GroupPanel({ workspace }: { workspace: WorkspaceDetail }) {
  const [insights, setInsights] = useState<SharedInsight[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadInsights = useCallback(async () => {
    try {
      setInsights(await api.listShared(workspace.id));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [workspace.id]);

  useEffect(() => {
    api
      .listShared(workspace.id)
      .then(setInsights)
      .catch((err) => setError(errorMessage(err)));
  }, [workspace.id]);

  async function copyCode() {
    await navigator.clipboard.writeText(workspace.invite_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-slate-50 p-4">
        <p className="text-sm font-medium">Invite classmates</p>
        <div className="mt-2 flex items-center gap-2">
          <code className="rounded-lg bg-white px-3 py-2 font-mono text-lg tracking-widest">{workspace.invite_code}</code>
          <button onClick={copyCode} className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-white">
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </section>

      <section>
        <p className="text-sm font-medium">Members ({workspace.members.length})</p>
        <ul className="mt-2 space-y-1 text-sm">
          {workspace.members.map((m) => (
            <li key={m.id} className="flex justify-between">
              <span className="truncate">{m.display_name || m.email}</span>
              <span className="text-xs text-slate-500">{m.role}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">Shared insights</p>
          <button onClick={loadInsights} className="text-xs text-indigo-600 hover:underline">
            Refresh
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        {insights.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            Nothing shared yet. Use “Share with group” under any AI answer in your chat.
          </p>
        ) : (
          <ul className="mt-3 space-y-4">
            {insights.map((insight) => (
              <li key={insight.id} className="space-y-2">
                <p className="text-xs text-slate-500">
                  {insight.shared_by_email ?? "A member"} asked: <span className="text-slate-800">{insight.question}</span>
                </p>
                <MessageBubble message={{ ...insight, sender: "assistant", content: insight.answer }} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}