import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../StatusBadge";
import type { SystemStatus } from "../../types";

const baseStatus: SystemStatus = {
  pc_online: true,
  last_seen: new Date().toISOString(),
  pending_messages: 0,
  llm_provider: "local",
  llm_available: true,
};

describe("StatusBadge", () => {
  it("shows a connecting state before the first status is loaded", () => {
    render(<StatusBadge status={null} />);
    expect(screen.getByText("Verbinde...")).toBeInTheDocument();
  });

  it("shows PC ONLINE when the PC is reachable", () => {
    render(<StatusBadge status={baseStatus} />);
    expect(screen.getByText("PC ONLINE")).toBeInTheDocument();
  });

  it("shows PC OFFLINE when the PC is unreachable", () => {
    render(<StatusBadge status={{ ...baseStatus, pc_online: false }} />);
    expect(screen.getByText("PC OFFLINE")).toBeInTheDocument();
  });
});
