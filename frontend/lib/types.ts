export type Role = "owner" | "member";

export interface Workspace {
  id: string;
  name: string;
  invite_code: string;
  role: Role;
  member_count?: number;
  created_at: string;
}

export interface Member {
  id: string;
  email: string | null;
  display_name: string | null;
  role: Role;
  joined_at: string;
}

export interface WorkspaceDetail extends Workspace {
  members: Member[];
}

export type DocumentStatus = "processing" | "ready" | "failed";

export interface DocumentItem {
  id: string;
  title: string;
  file_type: string;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number | null;
  chunk_count: number | null;
  uploaded_by_email: string | null;
  created_at: string;
}

export interface Citation {
  source_number: number;
  document_id: string;
  document_title: string;
  page_number: number;
  snippet: string;
  similarity: number;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
}

export interface Message {
  id: string;
  sender: "user" | "assistant";
  content: string;
  key_points: string[];
  citations: Citation[];
  found_in_materials: boolean | null;
  created_at: string;
}

export interface SharedInsight {
  id: string;
  question: string;
  answer: string;
  key_points: string[];
  citations: Citation[];
  found_in_materials: boolean | null;
  shared_by_email: string | null;
  created_at: string;
}

export interface RoadmapItem {
  id: string;
  week_number: number;
  title: string;
  summary: string;
  topics: string[];
  readings: string[];
  completed: boolean;
  completed_count: number;
}