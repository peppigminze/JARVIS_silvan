// Shared across every notification-emitting hook (reminders, message
// completion, ...) so the permission prompt is only ever requested
// once per session, regardless of how many independent pollers exist.
let askedThisSession = false;

export async function ensureNotificationPermission(): Promise<boolean> {
  if (!("Notification" in window)) return false;
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;
  if (askedThisSession) return false;
  askedThisSession = true;
  try {
    const result = await Notification.requestPermission();
    return result === "granted";
  } catch {
    return false;
  }
}
