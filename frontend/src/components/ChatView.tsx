import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, ToolObservation } from "../types";
import { flushOfflineQueue, listMessages, sendMessage } from "../services/api";
import { usePolling } from "../hooks/usePolling";

interface LocalQueued {
  client_id: string;
  content: string;
}

const STATUS_LABEL: Record<ChatMessage["status"], string> = {
  pending: "⏳ Wartet auf PC",
  processing: "⏳ Wird verarbeitet",
  completed: "Erledigt",
  failed: "Fehlgeschlagen",
  cancelled: "Abgebrochen",
};

// Shows how a completed request was actually answered (project spec
// section 21) - 🖥️ local Ollama, or ☁️ the optional cloud fallback
// (only ever used when local was unreachable, see README section 17).
const PROCESSED_BY_LABEL: Record<"local" | "cloud", string> = {
  local: "🖥️ Lokal",
  cloud: "☁️ Cloud",
};

// Short, human labels for tool activity (project spec section 29: show
// what ran, never the raw tool name or any chain-of-thought reasoning).
const TOOL_ACTIVITY_LABEL: Record<string, string> = {
  read_file: "Datei gelesen",
  write_file: "Datei geschrieben",
  list_files: "Dateien aufgelistet",
  search_files: "Dateien durchsucht",
  move_file: "Datei verschoben",
  copy_file: "Datei kopiert",
  delete_file: "Datei gelöscht",
  create_task: "Aufgabe erstellt",
  list_tasks: "Aufgaben abgerufen",
  complete_task: "Aufgabe erledigt",
  delete_task: "Aufgabe gelöscht",
  save_memory: "Erinnerung gespeichert",
  search_memory: "Erinnerung durchsucht",
  get_current_time: "Uhrzeit abgefragt",
  get_system_status: "Systeminfo abgefragt",
  cpu_usage: "CPU-Auslastung abgefragt",
  ram_usage: "RAM-Auslastung abgefragt",
  disk_usage: "Speicherplatz abgefragt",
  network_status: "Netzwerkstatus abgefragt",
  list_running_applications: "Programme aufgelistet",
  open_application: "Programm geöffnet",
  close_application: "Programm geschlossen",
  run_command: "Befehl ausgeführt",
};

function toolActivityLabel(tool: string): string {
  return TOOL_ACTIVITY_LABEL[tool] ?? tool;
}

export function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [queued, setQueued] = useState<LocalQueued[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const refresh = useCallback(async () => {
    try {
      const msgs = await listMessages();
      setMessages(msgs);
      setQueued((prev) => prev.filter((q) => !msgs.some((m) => m.client_id === q.client_id)));
    } catch {
      // Backend unreachable - the chat simply shows what it already has.
    }
  }, []);

  usePolling(refresh, 3000, []);
  usePolling(flushOfflineQueue, 5000, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, queued]);

  async function handleSend() {
    const content = draft.trim();
    if (!content || sending) return;
    setDraft("");
    setSending(true);
    try {
      const result = await sendMessage(content);
      if ("queued" in result) {
        setQueued((prev) => [...prev, { client_id: result.client_id, content }]);
      } else {
        setMessages((prev) => [...prev, result]);
      }
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const hasContent = messages.length > 0 || queued.length > 0;

  return (
    <div className="chat">
      <div className="chat__messages" ref={scrollRef}>
        {!hasContent && (
          <div className="chat__empty">
            Schreib JARVIS eine Nachricht. Läuft dein PC gerade nicht, wird sie gespeichert
            und verarbeitet, sobald er wieder online ist.
          </div>
        )}

        {messages.map((m) => (
          <MessageBubbles key={m.id} message={m} />
        ))}

        {queued.map((q) => (
          <div key={q.client_id} className="bubble-row is-user">
            <div className="bubble">{q.content}</div>
            <div className="bubble-meta">
              <span className="pill status-pending">Gespeichert (offline)</span>
            </div>
          </div>
        ))}
      </div>

      <div className="chat__composer">
        <textarea
          className="chat__input"
          placeholder="Nachricht an JARVIS..."
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="chat__send" onClick={handleSend} disabled={sending || !draft.trim()}>
          Senden
        </button>
      </div>
    </div>
  );
}

function MessageBubbles({ message }: { message: ChatMessage }) {
  return (
    <>
      <div className="bubble-row is-user">
        <div className="bubble">{message.content}</div>
      </div>

      {message.status === "completed" && message.response && (
        <div className="bubble-row is-jarvis">
          {message.observations.length > 0 && <ToolActivity observations={message.observations} />}
          <div className="bubble">{message.response}</div>
          {message.processed_by && (
            <div className="bubble-meta">
              <span className="pill status-completed">{PROCESSED_BY_LABEL[message.processed_by]}</span>
            </div>
          )}
        </div>
      )}

      {message.status !== "completed" && (
        <div className="bubble-row is-jarvis">
          <div className={`bubble ${message.status === "failed" ? "is-error" : ""}`}>
            {message.status === "failed"
              ? message.error || "Die Aktion konnte nicht ausgeführt werden."
              : message.response || "..."}
          </div>
          <div className="bubble-meta">
            <span className={`pill status-${message.status}`}>{STATUS_LABEL[message.status]}</span>
          </div>
        </div>
      )}
    </>
  );
}

function ToolActivity({ observations }: { observations: ToolObservation[] }) {
  return (
    <div className="tool-activity">
      {observations.map((obs, i) => (
        <div className="tool-activity__line" key={i}>
          <span aria-hidden="true">🔧</span> {toolActivityLabel(obs.tool)}{" "}
          <span className={obs.error ? "tool-activity__fail" : "tool-activity__ok"}>
            {obs.error ? "✗" : "✓"}
          </span>
        </div>
      ))}
    </div>
  );
}
