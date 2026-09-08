import { useCallback, useState } from "react";
import type { Settings } from "../types";
import { getSettingsOverview } from "../services/api";
import { usePolling } from "../hooks/usePolling";

export function SettingsView() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [copied, setCopied] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setSettings(await getSettingsOverview());
    } catch {
      // keep showing the last known settings
    }
  }, []);

  usePolling(refresh, 15000, []);

  async function copyWakeCommand() {
    if (!settings?.wake_on_lan.command) return;
    try {
      await navigator.clipboard.writeText(settings.wake_on_lan.command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API unavailable - nothing we can do silently
    }
  }

  if (!settings) {
    return <div className="empty-state">Lade Einstellungen...</div>;
  }

  const wol = settings.wake_on_lan;

  return (
    <div className="settings">
      <section className="settings__section">
        <h2>LLM</h2>
        <dl className="settings__grid">
          <dt>Lokales Modell</dt>
          <dd>{settings.local_llm_model}</dd>
          <dt>Lokale URL</dt>
          <dd>{settings.local_llm_base_url}</dd>
          <dt>Cloud-Fallback</dt>
          <dd>
            {settings.cloud_llm_enabled ? (
              <span className="pill status-completed">Aktiv ({settings.cloud_llm_model})</span>
            ) : (
              <span className="pill status-pending">Deaktiviert</span>
            )}
          </dd>
          <dt>Max. Wiederholungen</dt>
          <dd>{settings.message_max_retries}</dd>
        </dl>
      </section>

      <section className="settings__section">
        <h2>Sicherheit</h2>
        <dl className="settings__grid">
          <dt>Erlaubte Verzeichnisse</dt>
          <dd>
            {settings.allowed_directories.length === 0 ? (
              <span className="pill status-failed">Keine - Datei-/Terminal-Tools deaktiviert</span>
            ) : (
              <ul className="settings__list">
                {settings.allowed_directories.map((dir) => (
                  <li key={dir}>{dir}</li>
                ))}
              </ul>
            )}
          </dd>
        </dl>
        <p className="settings__hint">
          Änderungen an Sicherheitseinstellungen (erlaubte Verzeichnisse, Tokens) erfolgen nur in
          der <code>.env</code>-Datei plus Neustart von Backend/Agent - nie über diese Seite.
        </p>
      </section>

      <section className="settings__section">
        <h2>Wake-on-LAN</h2>
        {wol.configured ? (
          <>
            <dl className="settings__grid">
              <dt>MAC-Adresse</dt>
              <dd>{wol.mac_address}</dd>
              <dt>Broadcast</dt>
              <dd>
                {wol.broadcast}:{wol.port}
              </dd>
            </dl>
            <p className="settings__hint">
              Da Backend/Agent auf diesem PC laufen, können sie sich nicht selbst aufwecken. Führe
              diesen Befehl von einem <strong>anderen Gerät im selben Netzwerk</strong> aus:
            </p>
            <div className="settings__code-row">
              <code className="settings__code">{wol.command}</code>
              <button className="icon-btn" onClick={copyWakeCommand}>
                {copied ? "Kopiert!" : "Kopieren"}
              </button>
            </div>
          </>
        ) : (
          <p className="settings__hint">
            Nicht konfiguriert. Trage <code>WAKE_ON_LAN_MAC</code> in der <code>.env</code> ein
            (MAC-Adresse via <code>ipconfig /all</code> finden).
          </p>
        )}
      </section>
    </div>
  );
}
