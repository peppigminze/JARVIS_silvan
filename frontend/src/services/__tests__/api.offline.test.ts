import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushOfflineQueue, hasQueuedMessages, sendMessage } from "../api";

/**
 * Covers the offline-queue behavior (project spec section 36:
 * "Frontend ... offline state"). The PWA must queue outgoing messages
 * locally when the backend can't be reached, and flush them once it's
 * reachable again - without ever creating a duplicate (client_id is
 * the idempotency key the backend dedupes on).
 */
describe("offline message queue", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("has no queued messages initially", () => {
    expect(hasQueuedMessages()).toBe(false);
  });

  it("queues a message locally when the network request fails", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    const result = await sendMessage("hallo offline");

    expect("queued" in result && result.queued).toBe(true);
    expect(hasQueuedMessages()).toBe(true);
  });

  it("does not queue a message that sends successfully", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 1,
          client_id: "x",
          content: "hi",
          status: "pending",
          response: null,
          error: null,
          retry_count: 0,
          created_at: new Date().toISOString(),
          processed_at: null,
        }),
        { status: 200 }
      )
    );

    const result = await sendMessage("hallo online");

    expect("queued" in result).toBe(false);
    expect(hasQueuedMessages()).toBe(false);
  });

  it("flushes the queue once the backend becomes reachable again", async () => {
    vi.spyOn(global, "fetch").mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await sendMessage("wird nachgeholt");
    expect(hasQueuedMessages()).toBe(true);

    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 2,
          client_id: "y",
          content: "wird nachgeholt",
          status: "pending",
          response: null,
          error: null,
          retry_count: 0,
          created_at: new Date().toISOString(),
          processed_at: null,
        }),
        { status: 200 }
      )
    );

    await flushOfflineQueue();

    expect(hasQueuedMessages()).toBe(false);
  });

  it("stops flushing (keeps the rest queued) on the first failure", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await sendMessage("bleibt gequeued");
    expect(hasQueuedMessages()).toBe(true);

    // Still offline during the flush attempt.
    await flushOfflineQueue();

    expect(hasQueuedMessages()).toBe(true);
  });
});
