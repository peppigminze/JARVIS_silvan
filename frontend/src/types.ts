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

export type Recurrence = "none" | "daily" | "weekly" | "monthly";

export interface Task {
  id: number;
  title: string;
  description: string | null;
  notes: string | null;
  tags: string[];
  status: TaskStatus;
  priority: TaskPriority;
  due_at: string | null;
  reminder_enabled: boolean;
  recurrence: Recurrence;
  last_notified_at: string | null;
  created_at: string;
  completed_at: string | null;
}

export type MemoryType = "fact" | "preference" | "project";

export interface MemoryEntry {
  id: number;
  content: string;
  category: string | null;
  memory_type: MemoryType;
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

export type ActionStatus = "awaiting_confirmation" | "confirmed" | "rejected" | "executing" | "completed" | "failed";

export interface PendingAction {
  id: number;
  message_id: number | null;
  tool_name: string;
  arguments: Record<string, unknown>;
  observations: unknown[];
  status: ActionStatus;
  result: unknown;
  error: string | null;
  created_at: string;
  resolved_at: string | null;
}
