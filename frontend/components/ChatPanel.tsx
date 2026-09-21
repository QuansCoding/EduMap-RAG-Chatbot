"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import MessageBubble from "@/components/MessageBubble";
import { api, errorMessage } from "@/lib/api";
import type { ChatSession, Message } from "@/lib/types";

export default function ChatPanel({ workspaceId }: { workspaceId: string }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sharedIds, setSharedIds] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load my sessions for this workspace; open the most recent one.
  useEffect(() => {
    api
      .listSessions(workspaceId)
      .then((list) => {
        setSessions(list);
        if (list.length > 0) setActiveId(list[0].id);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [workspaceId]);

  // Load messages whenever the active session changes.
  useEffect(() => {
    if (!activeId) return;
    api
      .listMessages(activeId)
      .then(setMessages)
      .catch((err) => setError(errorMessage(err)));
  }, [activeId]);

  // Auto-scroll to the newest message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleNewChat() {
    setError(null);
    try {
      const session = await api.createSession(workspaceId);
      setSessions((prev) => [session, ...prev]);
      setActiveId(session.id);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function ensureSession(): Promise<string> {
    if (activeId) return activeId;
    const session = await api.createSession(workspaceId);
    setSessions((prev) => [session, ...prev]);
    setActiveId(session.id);
    return session.id;
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = input.trim();
    if (!content || sending) return;

    setSending(true);
    setError(null);
    setInput("");

    const tempId = `temp-${Date.now()}`;
    const optimistic: Message = {
      id: tempId,
      sender: "user",
      content,
      key_points: [],
      citations: [],
      found_in_materials: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      const sessionId = await ensureSession();
      const { user_message, assistant_message } = await api.sendMessage(sessionId, content);
      // Replace the optimistic message with the real saved ones.
      setMessages((prev) => [...prev.filter((m) => m.id !== tempId), user_message, assistant_message]);
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId && s.title === "New chat" ? { ...s, title: content.slice(0, 60) } : s)),
      );
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== tempId)); // roll back
      setInput(content);
      setError(errorMessage(err));
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter makes a new line.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  async function handleShare(messageId: string) {
    try {
      await api.shareMessage(messageId);
      setSharedIds((prev) => new Set(prev).add(messageId));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="flex h-full min-h-[70vh] flex-col">
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
        <h2 className="font-semibold">AI Study Chat</h2>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">private</span>
        <select
          value={activeId ?? ""}
          onChange={(e) => setActiveId(e.target.value || null)}
          className="ml-auto max-w-[45%] rounded-lg border border-slate-300 px-2 py-1 text-sm"
        >
          {sessions.length === 0 && <option value="">No chats yet</option>}
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </select>
        <button onClick={handleNewChat} className="rounded-lg border border-slate-300 px-2 py-1 text-sm hover:bg-slate-50">
          + New
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {messages.length === 0 && !sending && (
          <div className="mx-auto max-w-sm pt-10 text-center text-sm text-slate-500">
            <p className="font-medium text-slate-700">Ask anything about your course materials.</p>
            <p className="mt-2">Try: “Summarize the key ideas from lecture 3” or “What will week 5 cover?”</p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            onShare={m.sender === "assistant" ? () => handleShare(m.id) : undefined}
            shared={sharedIds.has(m.id)}
          />
        ))}
        {sending && <p className="text-sm text-slate-500">Searching your materials and thinking…</p>}
        <div ref={bottomRef} />
      </div>

      {error && <p className="mb-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <form onSubmit={handleSend} className="flex gap-2 border-t border-slate-200 pt-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={2000}
          rows={2}
          placeholder="Ask a question… (Enter to send, Shift+Enter for a new line)"
          className="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-lg bg-indigo-600 px-4 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}