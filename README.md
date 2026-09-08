# JARVIS – V1 (Local-First Personal AI Agent)

JARVIS ist ein persönlicher AI-Assistent, der **primär lokal auf deinem
Windows-PC läuft**. Es wird keine kostenpflichtige API vorausgesetzt: das
Sprachmodell läuft über eine lokale LLM-Runtime (z. B. [Ollama](https://ollama.com)).

Dieses Repository enthält die erste funktionierende Version (V1):

- ein **FastAPI-Backend** (Chat, Tasks, Memory, Sync-Queue, Auth, Reminder-Scheduler)
- einen **lokalen PC-Agent-Prozess**, der Nachrichten mit dem lokalen LLM
  und einem mehrschrittigen Tool-System verarbeitet - inklusive echter
  PC-Steuerung (Dateien, Terminal, Programme) mit Bestätigungspflicht
- eine **React/TypeScript PWA**, die auch dann nutzbar ist, wenn dein PC
  gerade ausgeschaltet ist (Nachrichten werden dann als `pending`
  gespeichert und automatisch verarbeitet, sobald der PC wieder online ist)

> **Sicherheitsmodell:** Jedes Tool hat eine Sicherheitsstufe (`SAFE` /
> `CONFIRM_REQUIRED` / `BLOCKED`). Lesende Aktionen (Dateien auflisten/lesen,
> Systeminfos) laufen automatisch. Alles, was etwas verändert - Datei
> schreiben/verschieben/löschen, Programme öffnen/schließen, Terminal-Befehle -
> pausiert die Pipeline und wartet auf deine Bestätigung in der PWA. Datei-
> und Terminal-Tools sind zusätzlich auf `ALLOWED_DIRECTORIES` beschränkt
> (leer per Default - siehe Abschnitt 6) und ein harter Denylist blockt
> offensichtlich katastrophale Befehle (Formatieren, `shutdown`, Fork-Bombs, ...)
> noch bevor sie zur Bestätigung kommen. Siehe Abschnitt 16 "Tool-Sicherheit"
> für Details.

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Python-Installation](#2-python-installation)
3. [Node-Installation](#3-node-installation)
4. [Lokale LLM-Runtime installieren (Ollama)](#4-lokale-llm-runtime-installieren-ollama)
5. [Modell einrichten](#5-modell-einrichten)
6. [Projekt einrichten (.env)](#6-projekt-einrichten-env)
7. [Backend starten](#7-backend-starten)
8. [Agent starten](#8-agent-starten)
9. [Frontend starten](#9-frontend-starten)
10. [PWA verwenden](#10-pwa-verwenden)
11. [Tests ausführen](#11-tests-ausführen)
12. [Troubleshooting](#12-troubleshooting)
13. [Projektstruktur](#13-projektstruktur)
14. [Architektur](#14-architektur)
15. [Roadmap / bekannte Einschränkungen von V1](#15-roadmap--bekannte-einschränkungen-von-v1)
16. [Tool-Sicherheit](#16-tool-sicherheit)
17. [Cloud-LLM-Fallback (optional)](#17-cloud-llm-fallback-optional)
18. [Wake-on-LAN](#18-wake-on-lan)
19. [Autostart (Windows)](#19-autostart-windows)
20. [Security-Hardening-Pass](#20-security-hardening-pass)

---

## 1. Voraussetzungen

- Windows 10/11 (die Anleitung ist auf Windows/PowerShell ausgerichtet,
  funktioniert aber genauso unter macOS/Linux mit den analogen Befehlen)
- Python 3.12 oder neuer
- Node.js 20 oder neuer (inkl. npm)
- ausreichend Hardware für lokale LLM-Inferenz (idealerweise eine GPU;
  kleinere Modelle laufen aber auch rein auf der CPU)

## 2. Python-Installation

Falls Python noch nicht installiert ist: [python.org/downloads](https://www.python.org/downloads/)
herunterladen und installieren. Wichtig: beim Installer **"Add python.exe
to PATH"** aktivieren.

Prüfen in PowerShell:

```powershell
python --version
```

## 3. Node-Installation

Node.js von [nodejs.org](https://nodejs.org/) installieren (LTS-Version).

Prüfen:

```powershell
node --version
npm --version
```

## 4. Lokale LLM-Runtime installieren (Ollama)

JARVIS erwartet standardmäßig eine **Ollama-kompatible** lokale
Chat-API unter `http://localhost:11434`. Andere OpenAI-kompatible lokale
Runtimes (z. B. LM Studio) funktionieren ebenso, solange sie
`POST /v1/chat/completions` bereitstellen.

1. Ollama herunterladen und installieren: [ollama.com/download](https://ollama.com/download)
2. Prüfen, dass der Dienst läuft:
   ```powershell
   ollama --version
   ```

## 5. Modell einrichten

Ein Modell herunterladen, z. B.:

```powershell
ollama pull llama3.1:8b
```

Du kannst jedes andere von Ollama unterstützte Modell verwenden - trage
den Modellnamen einfach in `.env` unter `LOCAL_LLM_MODEL` ein.

## 6. Projekt einrichten (.env)

Im Projekt-Root:

```powershell
git clone <dein-repo-url> jarvis
cd jarvis
copy .env.example .env
```

Öffne `.env` und passe mindestens die beiden Tokens an (nicht die
Standardwerte verwenden):

```env
USER_TOKEN=irgendein-langer-zufälliger-string
AGENT_TOKEN=ein-anderer-langer-zufälliger-string
```

Falls du ein anderes Modell als `llama3.1:8b` heruntergeladen hast, passe
`LOCAL_LLM_MODEL` entsprechend an.

Trage außerdem ein, welche Verzeichnisse JARVIS' Datei- und
Terminal-Tools anfassen dürfen (leer = alles deaktiviert):

```env
ALLOWED_DIRECTORIES=C:\Users\du\Documents\Projects,C:\Users\du\Desktop
```

Kopiere außerdem die Frontend-Env-Datei:

```powershell
copy frontend\.env.example frontend\.env
```

und trage in `frontend\.env` denselben Wert wie `USER_TOKEN` oben ein.

## 7. Backend starten

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Prüfen: [http://localhost:8000/health](http://localhost:8000/health)
sollte `{"status":"ok"}` zurückgeben.

Die SQLite-Datenbank (`backend/jarvis.db`) wird beim ersten Start
automatisch erzeugt.

## 8. Agent starten

Der Agent ist ein **separater Prozess** und läuft im Projekt-Root (nicht
in `backend/`), weil er sowohl das `backend`- als auch das
`agent`-Package importiert. Öffne dafür ein **zweites Terminal**:

```powershell
cd jarvis
backend\venv\Scripts\activate
python -m agent.run_agent
```

Der Agent sendet ab jetzt regelmäßig einen Heartbeat und verarbeitet
neue Nachrichten, sobald sie im Backend als `pending` gespeichert
werden.

> Stelle sicher, dass Ollama läuft, **bevor** du Nachrichten schickst,
> die eine LLM-Antwort brauchen - ansonsten meldet der Agent
> `Local LLM is unavailable.` (die Nachricht bleibt dann als `failed`
> stehen, du kannst sie erneut senden, sobald Ollama läuft).

## 9. Frontend starten

Drittes Terminal:

```powershell
cd jarvis\frontend
npm install
npm run dev
```

Öffne [http://localhost:5173](http://localhost:5173) im Browser.

## 10. PWA verwenden

- Am Desktop: im Browser (Chrome/Edge) über das Adressleisten-Icon
  "App installieren" wählen, um JARVIS als eigenständiges Fenster zu
  nutzen.
- Am Smartphone: die URL im mobilen Browser öffnen und "Zum Startbildschirm
  hinzufügen" wählen. Dafür muss dein Handy dieselbe Adresse erreichen
  können wie dein PC (z. B. im gleichen WLAN, oder über ein Tunnel-Tool
  wie ngrok/Tailscale - das ist für eine spätere Version vorgesehen).
- Ist der PC offline, bleibt die PWA nutzbar: Nachrichten werden lokal
  in eine Warteschlange gelegt und automatisch gesendet, sobald wieder
  eine Verbindung zum Backend besteht.

## 11. Tests ausführen

```powershell
cd backend
venv\Scripts\activate
pytest
```

Alle Tests laufen gegen eine In-Memory-SQLite-Datenbank und beeinflussen
`jarvis.db` nicht.

## 12. Troubleshooting

| Problem | Lösung |
|---|---|
| `Local LLM is unavailable.` als Nachrichtenfehler | Prüfen, ob Ollama läuft (`ollama list`) und ob `LOCAL_LLM_BASE_URL`/`LOCAL_LLM_MODEL` in `.env` korrekt sind. |
| PWA zeigt dauerhaft "PC OFFLINE" | Prüfen, ob `python -m agent.run_agent` läuft und ob `AGENT_TOKEN` in `.env` mit dem Wert übereinstimmt, den der Agent verwendet (beide lesen dieselbe `.env`-Datei im Projekt-Root). |
| `401 Unauthorized` im Frontend | `frontend\.env` → `VITE_USER_TOKEN` muss exakt `USER_TOKEN` aus der Root-`.env` entsprechen. Nach Änderung: Frontend neu starten. |
| Nachrichten bleiben dauerhaft `pending` | Der Agent-Prozess läuft nicht oder erreicht das Backend nicht (`BACKEND_BASE_URL` prüfen). |
| `pip install` schlägt fehl | Sicherstellen, dass die virtuelle Umgebung aktiviert ist (`venv\Scripts\activate`) und Python 3.12+ verwendet wird. |
| CORS-Fehler im Browser | `CORS_ORIGINS` in `.env` muss die URL enthalten, unter der das Frontend läuft (Standard: `http://localhost:5173`). |

## 13. Projektstruktur

```text
jarvis/
├── backend/
│   ├── app/
│   │   ├── api/           # REST-Endpunkte (messages, tasks, memory, sync, agent)
│   │   ├── agent/         # JARVIS Agent Core (Pipeline: understand -> plan -> tools -> reply)
│   │   ├── database/      # SQLAlchemy Models + Session-Setup
│   │   ├── llm/           # LLMProvider-Abstraktion (aktuell nur LocalLLMProvider)
│   │   ├── memory/        # MemoryStore-Abstraktion
│   │   ├── tools/         # Tool-System + Sicherheitsmodell (SAFE/CONFIRM_REQUIRED/BLOCKED)
│   │   ├── auth.py        # Einfache Bearer-Token-Auth (USER_TOKEN / AGENT_TOKEN)
│   │   ├── config.py      # Settings aus .env
│   │   ├── schemas.py     # Pydantic Request/Response-Schemas
│   │   └── main.py        # FastAPI App
│   ├── tests/              # pytest-Tests
│   └── requirements.txt
│
├── agent/                   # Lokaler PC-Agent-Prozess (separat vom Backend)
│   ├── client.py            # HTTP-Client zum Backend (nur AGENT_TOKEN)
│   ├── sync_worker.py        # Poll-Loop: holt pending messages, verarbeitet sie lokal
│   └── run_agent.py          # Einstiegspunkt (Heartbeat + Sync-Worker)
│
├── frontend/
│   ├── src/
│   │   ├── components/      # Sidebar, ChatView, TasksView, MemoryView, StatusBadge
│   │   ├── services/api.ts   # Backend-Client inkl. Offline-Queue
│   │   ├── hooks/usePolling.ts
│   │   └── App.tsx
│   └── package.json
│
├── .env.example
├── .gitignore
└── README.md
```

## 14. Architektur

> Ausführlicher, aktueller Überblick über das Gesamtsystem (Prozesse,
> Nachrichtenfluss, Datenmodell, Sicherheitsmodell): [ARCHITECTURE.md](ARCHITECTURE.md)

```text
                    ┌──────────────────┐
                    │   📱 Handy/PWA   │
                    └────────┬─────────┘
                             │ HTTPS (USER_TOKEN)
                             ▼
                    ┌──────────────────┐
                    │  Backend (FastAPI)│
                    │  Messages/Tasks/  │
                    │  Memory/Sync-Queue│
                    └────────┬─────────┘
                             │ HTTPS (AGENT_TOKEN)
                             ▼
                    ┌──────────────────┐
                    │  PC-Agent-Prozess │
                    │  Agent Core       │
                    │  Tool-System      │
                    └────────┬─────────┘
                             │ HTTP (kein API-Key)
                             ▼
                    ┌──────────────────┐
                    │  Lokales LLM      │
                    │  (Ollama)         │
                    └──────────────────┘
```

Nachrichten-Fluss: Der Nutzer schreibt in der PWA → das Backend speichert
die Nachricht sofort als `pending` (die PWA blockiert nie auf eine
Antwort) → der PC-Agent pollt regelmäßig `/api/sync/pending`, holt neue
Nachrichten ab (dabei werden sie serverseitig auf `processing` gesetzt,
damit sie nicht doppelt verarbeitet werden) → der Agent führt die
JARVIS-Pipeline aus (Memory abrufen → LLM fragen, ob/welches Tool
gebraucht wird → Tool ausführen → Antwort formulieren) → das Ergebnis
geht per `/api/sync/complete` (oder `/api/sync/fail`) zurück ans Backend
→ die PWA zeigt die Antwort beim nächsten Poll an.

Ist der PC ausgeschaltet, bleiben Nachrichten einfach `pending`, bis der
Agent wieder online ist und pollt.

## 15. Roadmap / bekannte Einschränkungen von V1

Bewusst **nicht** in V1 enthalten (siehe Auftrag, Abschnitt "Keine
Fake-Features" - nichts davon ist vorgetäuscht, es ist als TODO markiert):

- **Browser-/GitHub-Automatisierung** (Web-Recherche, `git`/GitHub-Tools) -
  Dateisystem/Terminal/Programme sind seit Phase 5 implementiert, siehe
  Abschnitt 16 "Tool-Sicherheit".
- **Vector-Search / Embeddings** für Memory - aktuell einfache
  Keyword-Suche (`MemoryStore.search`), die Schnittstelle ist aber
  stabil und austauschbar.
- **Weitere LLM-Provider** (OpenAI, Anthropic, ...) - die
  `LLMProvider`-Abstraktion und die Factory (`app/llm/factory.py`) sind
  vorbereitet, es muss nur eine neue Klasse ergänzt werden.
- **Voice-Interface**, Desktop-UI, weitere Clients.
- **Push-Benachrichtigungen** an das Handy, wenn eine Nachricht fertig
  verarbeitet wurde (aktuell Browser-Notifications per Polling, siehe
  `useReminderNotifications.ts` - reines mobiles Push ist ein späterer Schritt).
- **Sicherer Wake-on-LAN-Gateway/Tunnel** für die PWA (das Magic-Packet
  selbst lässt sich schon heute per Skript verschicken, siehe Abschnitt
  18 "Wake-on-LAN"). Autostart via Windows-Aufgabenplanung ist bereits
  vorhanden (Abschnitt 19), aber nicht automatisch installiert.

Diese Punkte sind absichtlich für spätere Versionen zurückgestellt, um
eine kleine, tatsächlich funktionierende V1 zu priorisieren.

## 16. Tool-Sicherheit

Jedes Tool (`app/tools/*.py`) trägt eine Sicherheitsstufe:

| Stufe | Bedeutung | Beispiele |
|---|---|---|
| `SAFE` | läuft automatisch, ohne Rückfrage | `list_tasks`, `read_file`, `list_files`, `search_files`, `cpu_usage`, `ram_usage`, `disk_usage`, `network_status`, `list_running_applications`, `get_current_time`, `save_memory`, `search_memory` |
| `CONFIRM_REQUIRED` | pausiert die Pipeline; ein Mensch muss in der PWA bestätigen/ablehnen | `write_file`, `move_file`, `copy_file`, `delete_file`, `delete_task`, `run_command`, `open_application`, `close_application` |
| `BLOCKED` | (Framework vorhanden, aktuell nicht genutzt) | - |

**Confirmation-Flow:** Wählt das Modell ein `CONFIRM_REQUIRED`-Tool, pausiert
`JarvisAgent.run_pipeline` (`app/agent/core.py`) sofort - das Tool wird
*nicht* ausgeführt. Stattdessen entsteht ein `PendingAction`-Eintrag
(`app/database/models.py`), die Nachricht bleibt `processing`, und die PWA
zeigt eine Bestätigen/Abbrechen-Leiste (`ConfirmBar.tsx`). Erst nach
Bestätigung holt der Agent die Aktion über `GET /api/sync/confirmed-actions`
ab, führt sie lokal aus und setzt die Pipeline mit dem Ergebnis fort - auch
mehrfach verkettet, falls danach noch ein weiteres bestätigungspflichtiges
Tool nötig ist. Bei Ablehnung wird die Nachricht mit einer kurzen Absage
abgeschlossen, ohne dass irgendetwas ausgeführt wurde.

**Dateisystem-Sandbox:** Alle Datei- und Terminal-Tools lösen Pfade über
`resolve_allowed_path()` (`app/tools/paths.py`) auf - Symlinks/`..` werden
aufgelöst, danach muss der Pfad innerhalb einer der in `ALLOWED_DIRECTORIES`
konfigurierten Verzeichnisse liegen. Ist die Variable leer (Standard), ist
jeder Dateizugriff blockiert. `delete_file` löscht zusätzlich nur leere
Ordner (kein rekursives `rmtree` durch einen einzelnen Tool-Call möglich).

**Terminal-Denylist:** `run_command` und `open_application` prüfen den
Befehl zusätzlich gegen einen harten Denylist (`app/tools/command_safety.py`)
für offensichtlich katastrophale Muster (Laufwerk formatieren, `shutdown`,
Fork-Bomb, rekursives Löschen von `/` oder `~`, ...) - diese werden
abgelehnt, bevor sie überhaupt zur Bestätigung kommen. Jeder tatsächlich
ausgeführte Befehl wird mit Befehl, Arbeitsverzeichnis, stdout/stderr,
Exit-Code und Timeout-Status in `command_logs` protokolliert
(`app/tools/terminal_tools.py`).

## 17. Cloud-LLM-Fallback (optional)

**LOCAL FIRST, immer:** JARVIS nutzt standardmäßig ausschließlich das lokale
Modell. Ein Cloud-Fallback ist vorhanden, aber per Default deaktiviert und
kostet dich nichts, bis du ihn explizit aktivierst:

```env
CLOUD_LLM_ENABLED=true
CLOUD_LLM_BASE_URL=https://api.openai.com/v1
CLOUD_LLM_MODEL=gpt-4o-mini
CLOUD_LLM_API_KEY=dein-eigener-api-key
```

`CloudLLMProvider` (`app/llm/cloud_provider.py`) spricht das
OpenAI-kompatible Chat-Completions-Format, funktioniert also mit der
echten OpenAI-API und mit jedem kompatiblen Anbieter, wenn du
`CLOUD_LLM_BASE_URL` entsprechend änderst. Er wird **ausschließlich**
dann versucht, wenn das lokale Modell selbst nicht erreichbar ist
(`JarvisAgent._chat`, `app/agent/core.py`) - niemals, weil das
Cloud-Modell "besser" sein könnte. Ist er deaktiviert oder kein API-Key
gesetzt, verhält sich JARVIS exakt wie ohne diesen Abschnitt: Eine
Nachricht wird bei nicht erreichbarem lokalem LLM automatisch mit
Backoff wiederholt (siehe Abschnitt "Sync" oben) statt an die Cloud zu
gehen. Der API-Key steht ausschließlich in deiner lokalen `.env` und
wird nirgends hardcodiert oder geloggt.

> **Hinweis:** Dieser Fallback wurde mit Fake-Providern unit-getestet
> (`backend/tests/test_cloud_fallback.py`), aber nicht live gegen eine
> echte Cloud-API verifiziert - dafür bräuchte es deinen eigenen,
> echten API-Key. Prüfe das selbst, bevor du dich darauf verlässt.

## 18. Wake-on-LAN

**Wichtige Einschränkung:** Backend und Agent laufen in V1 auf demselben
PC, den du aufwecken willst. Ist dieser PC aus, sind Backend und Agent
also auch aus - sie können sich unmöglich selbst ein Wake-Signal
schicken. Ein Browser/die PWA kann außerdem grundsätzlich kein rohes
UDP-Magic-Packet senden (keine Web-API dafür, aus Sicherheitsgründen).
Deshalb gibt es hier bewusst **keinen** "PC aufwecken"-Button in der
PWA, der ins Leere greifen würde (siehe Projektauftrag: "Keine
Fake-Features").

Die tatsächliche V1-Umsetzung (Abschnitt 23 im Auftrag):

- `scripts/wake_pc.py` - ein eigenständiges, abhängigkeitsfreies Skript,
  das ein echtes WOL-Magic-Packet verschickt. Es muss von einem
  **anderen Gerät im selben lokalen Netzwerk** laufen (Laptop, Handy mit
  Termux/Pythonista, Raspberry Pi, ...), nicht vom JARVIS-PC selbst.
- Die **Settings-Seite** in der PWA (`SettingsView.tsx`) zeigt dir MAC-
  Adresse, Broadcast-Adresse und den fertigen Befehl zum Kopieren an -
  automatisch aus `WAKE_ON_LAN_MAC`/`WAKE_ON_LAN_BROADCAST`/
  `WAKE_ON_LAN_PORT` in `.env` befüllt (`GET /api/settings`, rein
  lesend).

Voraussetzungen, damit Wake-on-LAN auf deinem PC überhaupt funktioniert
(unabhängig von JARVIS, reine Windows-/BIOS-Sache):

1. **BIOS/UEFI:** "Wake on LAN" bzw. "Power On by PCI-E/PCI" aktivieren.
2. **Windows Geräte-Manager:** Netzwerkadapter → Eigenschaften →
   Energieverwaltung → "Gerät kann Computer aus dem Ruhezustand
   aktivieren" aktivieren, außerdem unter "Erweitert" "Wake on Magic
   Packet" aktivieren, falls vorhanden.
3. Der PC muss per **Kabel (Ethernet)** verbunden sein - die meisten
   WLAN-Adapter unterstützen Wake-on-LAN aus dem Ausschaltzustand nicht
   zuverlässig.

MAC-Adresse deines aktiven Adapters findest du mit:

```powershell
ipconfig /all
```

(„Physische Adresse" unter deinem aktiven Netzwerkadapter).

**Für später vorgesehen (nicht in V1):** ein sicherer Gateway/Tunnel
oder ein Relay-Dienst, über den die PWA selbst - auch von unterwegs -
ein Wake-Signal auslösen könnte, ohne eine unsichere öffentliche
UDP-Portfreigabe am Router einzurichten (siehe Projektauftrag Abschnitt
23: "keine unsichere öffentliche UDP-Portfreigabe als
Standardlösung").

## 19. Autostart (Windows)

JARVIS kann sich per **Windows-Aufgabenplanung** (Task Scheduler)
automatisch bei der Anmeldung starten - Backend und Agent zusammen,
über `scripts/start_jarvis.ps1`.

**Registrieren** (einmalig, nach dem normalen Setup aus Abschnitt 1-9):

```powershell
python scripts\autostart.py install
```

**Status prüfen** (rein lesend):

```powershell
python scripts\autostart.py status
```

**Wieder entfernen:**

```powershell
python scripts\autostart.py uninstall
```

Die eigentliche Aufgabe wird bei Anmeldung mit ~20 Sekunden Verzögerung
ausgelöst (damit der Desktop erst fertig geladen ist) und startet
Backend und Agent unsichtbar im Hintergrund; Logs landen in `logs/`
(`backend.log`, `agent.log`, jeweils mit `.err.log`-Pendant für
stderr). Diese Aufgabe läuft für deinen eigenen Benutzer und benötigt
**keine** Administratorrechte/UAC-Bestätigung zum Registrieren.

> **Wichtig:** Das Anlegen einer geplanten Aufgabe ist eine dauerhafte
> Systemänderung. `python scripts\autostart.py install` führt das
> tatsächlich aus. Auf diesem Rechner wurde die Aufgabe mit deiner
> ausdrücklichen Bestätigung bereits registriert und end-to-end
> verifiziert: `status` meldet sie als aktiv, und `start_jarvis.ps1`
> startet Backend und Agent nachweislich korrekt (per `/health`-Check
> und den Logs in `logs/` bestätigt). Die reinen Skript-Bausteine sind
> zusätzlich unit-getestet (`backend/tests/test_autostart.py`). Auf
> einem neuen Rechner führst du `install` selbst aus, sobald du es
> möchtest - ein UAC-Dialog erscheint dabei, den du bestätigen musst.

## 20. Security-Hardening-Pass

Systematische Durchsicht des gesamten Codes (Projektauftrag Abschnitt
37). Gefunden und behoben:

- **Timing-Angriff auf Tokens:** Der Vergleich der Bearer-Tokens nutzte
  `!=`, was die Antwortzeit minimal mit der Anzahl übereinstimmender
  Zeichen korrelieren lässt. Ersetzt durch `secrets.compare_digest`
  (`app/auth.py`), zeitkonstant.
- **Stille Platzhalter-Tokens:** Startet das Backend mit den
  Standardwerten aus `.env.example` (`change-me-user-token` /
  `change-me-agent-token`), gab es keinerlei Hinweis darauf. Jetzt eine
  laute Warnung beim Start (`app/main.py::_warn_if_default_tokens`).

Geprüft und für unbedenklich befunden:

- **Keine hardcodierten Secrets** im Code (durchsucht).
- **CORS** ist nicht auf `*` gesetzt (Standard: nur `localhost:5173`/
  `127.0.0.1:5173`), trotz `allow_credentials=True`.
- **Jeder API-Endpunkt** außer `/health` und `/` verlangt `require_user`
  oder `require_agent` - einzeln durchgegangen (`app/api/*.py`).
- **Keine XSS-Vektoren** im Frontend (kein `dangerouslySetInnerHTML`,
  `innerHTML` oder `eval` - React escaped Inhalte standardmäßig).
- **Kein Token-Leck** in Logs (Backend oder Frontend).
- **Kein Bypass der Tool-Bestätigung:** `tool.execute()` wird
  codebaseweit nur an zwei Stellen aufgerufen, beide hinter dem
  SAFE/CONFIRM_REQUIRED-Gate bzw. dem authentifizierten
  Confirm/Reject-Flow (siehe Abschnitt 16).
- `run_command`/`open_application` interpretieren den Befehlsstring
  absichtlich als Shell-Kommando (das ist die Funktion des Tools,
  nicht ein Bug) - abgesichert durch Bestätigungspflicht + Denylist,
  nicht durch Escaping.

Bekannt, bewusst nicht automatisch gefixt:

- `npm audit` meldet 3 Schwachstellen (2 moderate, 1 high) in
  `esbuild`/`vite`/`vite-plugin-pwa` - betrifft ausschließlich den
  Vite-**Dev-Server** (`npm run dev`), nicht den Produktions-Build.
  Der Fix (`npm audit fix --force`) wäre ein Breaking-Change auf Vite
  8; nicht ungefragt durchgeführt, da das Risiko für ein lokales
  Dev-Tool gering ist. Führe den Fix selbst aus, wenn du magst - teste
  danach `npm run dev` und `npm run build`.

`app/database/db.py::ensure_columns()` baut SQL-Statements per
f-string (SQLite unterstützt keine parametrisierten Identifier für
DDL). Das ist nur sicher, weil ausschließlich mit statischen,
hartkodierten Werten aus `run_migrations()` aufgerufen - im Code
explizit als Warnung dokumentiert, falls das mal geändert wird.
