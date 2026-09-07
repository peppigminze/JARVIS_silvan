import { useCallback, useState } from "react";
import type { MemoryEntry } from "../types";
import { listMemory, saveMemory } from "../services/api";
import { usePolling } from "../hooks/usePolling";

export function MemoryView() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setEntries(await listMemory());
    } catch {
      // keep showing last known list
    }
  }, []);

  usePolling(refresh, 8000, []);

  async function handleSave() {
    const c = content.trim();
    if (!c || busy) return;
    setBusy(true);
    try {
      const entry = await saveMemory(c, category.trim() || undefined);
      setEntries((prev) => [entry, ...prev]);
      setContent("");
      setCategory("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="list-header">
        <h1>Memory</h1>
        <div className="inline-form">
          <input
            className="text-input"
            placeholder="Was soll JARVIS sich merken?"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
            style={{ minWidth: 220 }}
          />
          <input
            className="text-input"
            placeholder="Kategorie (optional)"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{ width: 140 }}
          />
          <button className="btn-primary" onClick={handleSave} disabled={busy || !content.trim()}>
            Speichern
          </button>
        </div>
      </div>

      {entries.length === 0 ? (
        <div className="empty-state">Noch keine Erinnerungen gespeichert.</div>
      ) : (
        <div className="card-list">
          {entries.map((m) => (
            <div className="card" key={m.id}>
              <div className="card__body">
                <p className="card__title">{m.content}</p>
                <div className="card__meta">
                  {m.category && <span className="category-tag">{m.category}</span>}
                  <span>{new Date(m.updated_at).toLocaleDateString("de-CH")}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
