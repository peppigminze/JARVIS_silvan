import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VoiceOrb } from "../VoiceOrb";

describe("VoiceOrb", () => {
  it("renders with the state-specific class", () => {
    const { container } = render(<VoiceOrb state="listening" onClick={() => {}} />);
    expect(container.querySelector(".voice-orb--listening")).toBeInTheDocument();
  });

  it("calls onClick when pressed", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<VoiceOrb state="idle" onClick={onClick} />);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled and shows the unsupported state when unsupported", () => {
    render(<VoiceOrb state="unsupported" onClick={() => {}} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("reflects the listening state via aria-pressed", () => {
    render(<VoiceOrb state="listening" onClick={() => {}} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
  });
});
