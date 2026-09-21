"use client";

import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { DocumentItem, RoadmapItem } from "@/lib/types";

interface Props {
  workspaceId: string;
  isOwner: boolean;
  memberCount: number;
}

export default function RoadmapPanel({ workspaceId, isOwner, memberCount }: Props) {
  const [items, setItems] = useState<RoadmapItem[]>([]);
  const [readyDocs, setReadyDocs] = useState<DocumentItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Promise.all runs both requests at the same time and waits for both.
    Promise.all([api.getRoadmap(workspaceId), api.listDocuments(workspaceId)])
      .then(([roadmap, docs]) => {
        setItems(roadmap);
        const ready = docs.filter((d) => d.status === "ready");
        setReadyDocs(ready);
        const preferred = ready.find((d) => d.file_type === "syllabus") ?? ready[0];
        if (preferred) setSelectedDoc(preferred.id);
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [workspaceId]);

  async function handleGenerate() {
    if (!selectedDoc) return;
    if (
      items.length > 0 &&
      !window.confirm("Regenerating replaces the current roadmap and resets everyone's progress. Continue?")
    ) {
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      setItems(await api.generateRoadmap(workspaceId, selectedDoc));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setGenerating(false);
    }
  }

  async function toggle(item: RoadmapItem) {
    const completed = !item.completed;
    // Optimistic update first...
    setItems((prev) =>
      prev.map((i) =>
        i.id === item.id ? { ...i, completed, completed_count: i.completed_count + (completed ? 1 : -1) } : i,
      ),
    );
    try {
      await api.setProgress(item.id, completed);
    } catch (err) {
      // ...roll back if the server says no.
      setItems((prev) => prev.map((i) => (i.id === item.id ? item : i)));
      setError(errorMessage(err));
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading roadmap…</p>;

  const doneCount = items.filter((i) => i.completed).length;

  return (
    <div className="space-y-4">
      {isOwner && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 p-3">
          {readyDocs.length === 0 ? (
            <p className="text-sm text-slate-500">Upload a syllabus in the Documents tab to generate a roadmap.</p>
          ) : (
            <>
              <select
                value={selectedDoc}
                onChange={(e) => setSelectedDoc(e.target.value)}
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-2 py-1 text-sm"
              >
                {readyDocs.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} ({d.file_type})
                  </option>
                ))}
              </select>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="rounded-lg bg-indigo-600 px-3 py-1 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {generating ? "Generating…" : items.length ? "Regenerate" : "Generate roadmap"}
              </button>
            </>
          )}
        </div>
      )}

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {items.length === 0 ? (
        <p className="text-sm text-slate-500">
          No roadmap yet.{isOwner ? "" : " Ask the group owner to generate one from the syllabus."}
        </p>
      ) : (
        <>
          <div>
            <div className="flex justify-between text-xs text-slate-500">
              <span>Your progress</span>
              <span>
                {doneCount} / {items.length} weeks
              </span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-emerald-500 transition-all"
                style={{ width: `${(doneCount / items.length) * 100}%` }}
              />
            </div>
          </div>

          <ol className="space-y-3">
            {items.map((item) => (
              <li
                key={item.id}
                className={`rounded-xl border p-4 ${item.completed ? "border-emerald-200 bg-emerald-50/50" : "border-slate-200"}`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={item.completed}
                    onChange={() => toggle(item)}
                    className="mt-1 h-4 w-4 accent-emerald-600"
                    aria-label={`Mark week ${item.week_number} complete`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold uppercase text-indigo-600">Week {item.week_number}</p>
                    <p className="font-medium">{item.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{item.summary}</p>
                    {item.topics.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {item.topics.map((t, i) => (
                          <span key={i} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                    {item.readings.length > 0 && (
                      <p className="mt-2 text-xs text-slate-500">📖 {item.readings.join(" · ")}</p>
                    )}
                    <p className="mt-2 text-xs text-slate-400">
                      {item.completed_count} of {memberCount} members finished
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}