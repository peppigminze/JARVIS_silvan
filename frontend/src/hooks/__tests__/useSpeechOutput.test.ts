import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { useSpeechOutput } from "../useSpeechOutput";

class FakeUtterance {
  lang = "";
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public text: string) {}
}

function installFakeSpeechSynthesis() {
  const spoken: string[] = [];
  const fake = {
    cancel: vi.fn(),
    speak: vi.fn((utterance: FakeUtterance) => {
      spoken.push(utterance.text);
      utterance.onstart?.();
    }),
  };
  (globalThis as any).speechSynthesis = fake;
  (globalThis as any).SpeechSynthesisUtterance = FakeUtterance;
  return { fake, spoken };
}

describe("useSpeechOutput", () => {
  afterEach(() => {
    // Unmount every rendered hook *before* removing the fake API - the
    // hook's own unmount effect calls window.speechSynthesis.cancel(),
    // which would otherwise throw once the fake has been deleted.
    cleanup();
    delete (globalThis as any).speechSynthesis;
    delete (globalThis as any).SpeechSynthesisUtterance;
  });

  it("reports unsupported when the API is missing", () => {
    delete (globalThis as any).speechSynthesis;
    const { result } = renderHook(() => useSpeechOutput());
    expect(result.current.isSupported).toBe(false);
  });

  it("speaks text and reports isSpeaking", () => {
    const { fake } = installFakeSpeechSynthesis();
    const { result } = renderHook(() => useSpeechOutput());

    act(() => result.current.speak("Hallo Silvan"));

    expect(fake.speak).toHaveBeenCalledTimes(1);
    expect(result.current.isSpeaking).toBe(true);
  });

  it("does not speak empty text", () => {
    const { fake } = installFakeSpeechSynthesis();
    const { result } = renderHook(() => useSpeechOutput());

    act(() => result.current.speak("   "));

    expect(fake.speak).not.toHaveBeenCalled();
  });

  it("stop() cancels speech and clears isSpeaking", () => {
    const { fake } = installFakeSpeechSynthesis();
    const { result } = renderHook(() => useSpeechOutput());

    act(() => result.current.speak("Hallo"));
    act(() => result.current.stop());

    expect(fake.cancel).toHaveBeenCalled();
    expect(result.current.isSpeaking).toBe(false);
  });
});
