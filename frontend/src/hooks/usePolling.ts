import { useEffect, useRef } from "react";

/**
 * Calls `callback` immediately and then every `intervalMs`.
 * Skips overlapping calls if the previous one hasn't resolved yet.
 */
export function usePolling(callback: () => Promise<void> | void, intervalMs: number, deps: unknown[] = []) {
  const runningRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      if (runningRef.current || cancelled) return;
      runningRef.current = true;
      try {
        await callback();
      } finally {
        runningRef.current = false;
      }
    };

    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
