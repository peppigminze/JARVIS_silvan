import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { flushOfflineQueue, listMessages, sendMessage } from "../services/api";
import { usePolling } from "../hooks/usePolling";

interface LocalQueued {
  client_id: string;
  content: string;
}

const STATUS_LABEL: Record<ChatMessage["status"], string> = {
  pending: "Wartet auf PC",
  processing: "Wird verarbeitet",
  completed: "Erledigt",
  failed: "Fehlgeschlagen",
  cancelled: "Abgebrochen",
};

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
          <div className="bubble">{message.response}</div>
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
