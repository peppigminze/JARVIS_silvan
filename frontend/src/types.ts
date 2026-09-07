export type MessageStatus = "pending" | "processing" | "completed" | "failed" | "cancelled";
export type TaskStatus = "pending" | "completed" | "cancelled";
export type TaskPriority = "low" | "medium" | "high";

export interface ChatMessage {
  id: number;
  client_id: string | null;
  content: string;
  status: MessageStatus;
  response: string | null;
  error: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_at: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface MemoryEntry {
  id: number;
  content: string;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface SystemStatus {
  pc_online: boolean;
  last_seen: string | null;
  pending_messages: number;
  llm_provider: string;
  llm_available: boolean | null;
}
