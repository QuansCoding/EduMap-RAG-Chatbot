import { supabase } from "./supabase";
import type {
  ChatSession,
  DocumentItem,
  Message,
  RoadmapItem,
  SharedInsight,
  Workspace,
  WorkspaceDetail,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong";
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  // getSession() also refreshes an expired access token automatically.
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  // For FormData (file uploads) the browser sets the multipart Content-Type itself.
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    if (response.status === 401) {
      await supabase.auth.signOut(); // session is invalid → force re-login
    }
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail; // FastAPI's HTTPException format
    } catch {
      // response had no JSON body; keep the default message
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T; // No Content
  return (await response.json()) as T;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  health: async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_URL}/api/health`);
      return response.ok;
    } catch {
      return false;
    }
  },

  // Workspaces
  listWorkspaces: () => apiFetch<Workspace[]>("/api/workspaces"),
  createWorkspace: (name: string) =>
    apiFetch<Workspace>("/api/workspaces", { method: "POST", body: json({ name }) }),
  joinWorkspace: (inviteCode: string) =>
    apiFetch<Workspace>("/api/workspaces/join", { method: "POST", body: json({ invite_code: inviteCode }) }),
  getWorkspace: (id: string) => apiFetch<WorkspaceDetail>(`/api/workspaces/${id}`),
  listShared: (id: string) => apiFetch<SharedInsight[]>(`/api/workspaces/${id}/shared`),

  // Documents
  listDocuments: (workspaceId: string) => apiFetch<DocumentItem[]>(`/api/workspaces/${workspaceId}/documents`),
  uploadDocument: (workspaceId: string, file: File, fileType: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("file_type", fileType);
    return apiFetch<DocumentItem>(`/api/workspaces/${workspaceId}/documents`, { method: "POST", body: form });
  },
  deleteDocument: (documentId: string) => apiFetch<void>(`/api/documents/${documentId}`, { method: "DELETE" }),

  // Chat
  listSessions: (workspaceId: string) => apiFetch<ChatSession[]>(`/api/workspaces/${workspaceId}/chat/sessions`),
  createSession: (workspaceId: string) =>
    apiFetch<ChatSession>(`/api/workspaces/${workspaceId}/chat/sessions`, { method: "POST", body: json({}) }),
  listMessages: (sessionId: string) => apiFetch<Message[]>(`/api/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: string, content: string) =>
    apiFetch<{ user_message: Message; assistant_message: Message }>(`/api/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: json({ content }),
    }),
  shareMessage: (messageId: string) =>
    apiFetch<{ shared: boolean }>(`/api/chat/messages/${messageId}/share`, { method: "POST" }),

  // Roadmap
  getRoadmap: (workspaceId: string) => apiFetch<RoadmapItem[]>(`/api/workspaces/${workspaceId}/roadmap`),
  generateRoadmap: (workspaceId: string, documentId: string) =>
    apiFetch<RoadmapItem[]>(`/api/workspaces/${workspaceId}/roadmap/generate`, {
      method: "POST",
      body: json({ document_id: documentId }),
    }),
  setProgress: (itemId: string, completed: boolean) =>
    apiFetch<{ completed: boolean }>(`/api/roadmap/items/${itemId}/progress`, {
      method: "PUT",
      body: json({ completed }),
    }),
};