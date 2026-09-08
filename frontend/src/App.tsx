import { useCallback, useState } from "react";
import "./App.css";
import { Sidebar, type View } from "./components/Sidebar";
import { StatusBadge } from "./components/StatusBadge";
import { ConfirmBar } from "./components/ConfirmBar";
import { ChatView } from "./components/ChatView";
import { TasksView } from "./components/TasksView";
import { MemoryView } from "./components/MemoryView";
import { SettingsView } from "./components/SettingsView";
import { getStatus } from "./services/api";
import { usePolling } from "./hooks/usePolling";
import { useReminderNotifications } from "./hooks/useReminderNotifications";
import type { SystemStatus } from "./types";

const TITLES: Record<View, string> = {
  chat: "Chat",
  tasks: "Tasks",
  memory: "Memory",
  settings: "Settings",
};

export default function App() {
  const [view, setView] = useState<View>("chat");
  const [status, setStatus] = useState<SystemStatus | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await getStatus());
    } catch {
      setStatus((prev) => (prev ? { ...prev, pc_online: false } : prev));
    }
  }, []);

  usePolling(refreshStatus, 10000, []);
  useReminderNotifications();

  return (
    <div className="shell">
      <Sidebar active={view} onChange={setView} pendingTaskCount={status?.pending_messages ?? 0} />
      <div className="main">
        <header className="topbar">
          <span className="topbar__title">{TITLES[view]}</span>
          <StatusBadge status={status} />
        </header>
        <ConfirmBar onResolved={refreshStatus} />
        <div className={`panel ${view === "chat" ? "panel--flush" : ""}`}>
          {view === "chat" && <ChatView />}
          {view === "tasks" && <TasksView />}
          {view === "memory" && <MemoryView />}
          {view === "settings" && <SettingsView />}
        </div>
      </div>
    </div>
  );
}
