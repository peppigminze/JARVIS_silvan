import type { SystemStatus } from "../types";

interface Props {
  status: SystemStatus | null;
}

export function StatusBadge({ status }: Props) {
  if (!status) {
    return (
      <span className="status-badge">
        <span className="status-badge__dot" />
        Verbinde...
      </span>
    );
  }

  return (
    <span className={`status-badge ${status.pc_online ? "is-online" : "is-offline"}`}>
      <span className="status-badge__dot" />
      {status.pc_online ? "PC ONLINE" : "PC OFFLINE"}
    </span>
  );
}
