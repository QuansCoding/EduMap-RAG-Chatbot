"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import ChatPanel from "@/components/ChatPanel";
import DocumentsPanel from "@/components/DocumentsPanel";
import GroupPanel from "@/components/GroupPanel";
import RequireAuth from "@/components/RequireAuth";
import RoadmapPanel from "@/components/RoadmapPanel";
import { api, errorMessage } from "@/lib/api";
import type { WorkspaceDetail } from "@/lib/types";
import { useSession } from "@/lib/useSession";

type Tab = "roadmap" | "documents" | "group";

const TABS: { id: Tab; label: string }[] = [
  { id: "roadmap", label: "🗺️ Roadmap" },
  { id: "documents", label: "📄 Documents" },
  { id: "group", label: "👥 Group" },
];

export default function WorkspacePage() {
  return (
    <RequireAuth>
      <WorkspaceView />
    </RequireAuth>
  );
}

function WorkspaceView() {
  const { id } = useParams<{ id: string }>();
  const { session } = useSession();
  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("roadmap");

  useEffect(() => {
    api
      .getWorkspace(id)
      .then(setWorkspace)
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  if (error) {
    return (
      <main className="p-8">
        <p className="text-red-600">{error}</p>
        <Link href="/dashboard" className="mt-4 inline-block text-indigo-600 hover:underline">
          ← Back to dashboard
        </Link>
      </main>
    );
  }
  if (!workspace) return <p className="p-8 text-slate-500">Loading workspace…</p>;

  const isOwner = workspace.role === "owner";

  return (
    <main className="mx-auto max-w-7xl p-4">
      <header className="mb-4 flex flex-wrap items-center gap-3">
        <Link href="/dashboard" className="text-sm text-slate-500 hover:underline">
          ← Groups
        </Link>
        <h1 className="text-xl font-bold">{workspace.name}</h1>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{isOwner ? "Owner" : "Member"}</span>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-4">
          <nav className="mb-4 flex gap-1 border-b border-slate-200">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm ${
                  tab === t.id ? "border-indigo-600 font-medium text-indigo-700" : "border-transparent text-slate-500"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
          {tab === "roadmap" && (
            <RoadmapPanel workspaceId={id} isOwner={isOwner} memberCount={workspace.members.length} />
          )}
          {tab === "documents" && (
            <DocumentsPanel workspaceId={id} isOwner={isOwner} currentEmail={session?.user.email} />
          )}
          {tab === "group" && <GroupPanel workspace={workspace} />}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 lg:sticky lg:top-4 lg:h-[calc(100vh-6rem)]">
          <ChatPanel workspaceId={id} />
        </section>
      </div>
    </main>
  );
}