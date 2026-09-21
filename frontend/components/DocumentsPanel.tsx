"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, errorMessage } from "@/lib/api";
import type { DocumentItem, DocumentStatus } from "@/lib/types";

const FILE_TYPES = [
  { value: "slides", label: "Lecture slides" },
  { value: "syllabus", label: "Syllabus" },
  { value: "textbook", label: "Textbook / chapter" },
  { value: "notes", label: "Notes" },
  { value: "other", label: "Other" },
];

const STATUS_STYLES: Record<DocumentStatus, string> = {
  processing: "bg-amber-100 text-amber-800",
  ready: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800",
};

interface Props {
  workspaceId: string;
  isOwner: boolean;
  currentEmail: string | undefined;
}

export default function DocumentsPanel({ workspaceId, isOwner, currentEmail }: Props) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState("slides");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // useCallback keeps the same function identity between renders,
  // so effects that depend on it don't re-run needlessly.
  const loadDocuments = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments(workspaceId));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [workspaceId]);

  // Initial load. (setState happens inside .then, i.e. after the network responds, which is
  // what React's lint rules want; calling loadDocuments() directly here would be flagged.)
  useEffect(() => {
    api
      .listDocuments(workspaceId)
      .then(setDocuments)
      .catch((err) => setError(errorMessage(err)));
  }, [workspaceId]);

  const hasProcessing = documents.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const timer = setInterval(loadDocuments, 3000);
    return () => clearInterval(timer); // cleanup
  }, [hasProcessing, loadDocuments]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(workspaceId, file, fileType);
      setDocuments((prev) => [doc, ...prev]);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(doc: DocumentItem) {
    if (!window.confirm(`Delete "${doc.title}"? Its content will no longer be searchable.`)) return;
    try {
      await api.deleteDocument(doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleUpload} className="space-y-3 rounded-xl border border-dashed border-slate-300 p-4">
        <p className="text-sm font-medium">Upload course material (PDF, max 10 MB)</p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm"
        />
        <div className="flex gap-2">
          <select
            value={fileType}
            onChange={(e) => setFileType(e.target.value)}
            className="rounded-lg border border-slate-300 px-2 py-1 text-sm"
          >
            {FILE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={!file || uploading}
            className="rounded-lg bg-indigo-600 px-4 py-1 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Shared with everyone in this group. Don&apos;t upload private or sensitive documents.
        </p>
      </form>

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {documents.length === 0 ? (
        <p className="text-sm text-slate-500">No documents yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {documents.map((doc) => (
            <li key={doc.id} className="flex items-start gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{doc.title}</p>
                <p className="text-xs text-slate-500">
                  {doc.file_type}
                  {doc.page_count ? ` · ${doc.page_count} pages` : ""}
                  {doc.uploaded_by_email ? ` · ${doc.uploaded_by_email}` : ""}
                </p>
                {doc.status === "failed" && doc.error_message && (
                  <p className="mt-1 text-xs text-red-600">{doc.error_message}</p>
                )}
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[doc.status]}`}>{doc.status}</span>
              {(isOwner || doc.uploaded_by_email === currentEmail) && (
                <button onClick={() => handleDelete(doc)} className="text-xs text-slate-400 hover:text-red-600">
                  Delete
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}