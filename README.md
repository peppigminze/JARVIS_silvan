# JARVIS – V1 (Local-First Personal AI Agent)

JARVIS ist ein persönlicher AI-Assistent, der **primär lokal auf deinem
Windows-PC läuft**. Es wird keine kostenpflichtige API vorausgesetzt: das
Sprachmodell läuft über eine lokale LLM-Runtime (z. B. [Ollama](https://ollama.com)).

Dieses Repository enthält die erste funktionierende Version (V1):

- ein **FastAPI-Backend** (Chat, Tasks, Memory, Sync-Queue, Auth)
- einen **lokalen PC-Agent-Prozess**, der Nachrichten mit dem lokalen LLM
  und einem einfachen Tool-System verarbeitet
- eine **React/TypeScript PWA**, die auch dann nutzbar ist, wenn dein PC
  gerade ausgeschaltet ist (Nachrichten werden dann als `pending`
  gespeichert und automatisch verarbeitet, sobald der PC wieder online ist)

> **Was V1 NICHT kann (bewusst, siehe Abschnitt "Roadmap"):** Programme
> öffnen, Dateien bearbeiten, Terminal-Befehle ausführen, Browser/GitHub
> steuern. Das Framework dafür (Tool-Sicherheitsmodell) ist vorbereitet,
> aber es sind in V1 absichtlich noch keine gefährlichen Tools
> implementiert.

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

- **PC-Steuerung**: Dateien/Programme öffnen, Terminal-Befehle,
  Browser-/Git-/GitHub-Automatisierung. Das Sicherheitsmodell
  (`SAFE` / `CONFIRM_REQUIRED` / `BLOCKED`) in `app/tools/base.py` ist
  vorbereitet, aber es sind noch keine gefährlichen Tools registriert.
- **Vector-Search / Embeddings** für Memory - aktuell einfache
  Keyword-Suche (`MemoryStore.search`), die Schnittstelle ist aber
  stabil und austauschbar.
- **Weitere LLM-Provider** (OpenAI, Anthropic, ...) - die
  `LLMProvider`-Abstraktion und die Factory (`app/llm/factory.py`) sind
  vorbereitet, es muss nur eine neue Klasse ergänzt werden.
- **Voice-Interface**, Desktop-UI, weitere Clients.
- **Confirmation-UI** für `CONFIRM_REQUIRED`-Tools (aktuell werden
  solche Tools einfach nicht ausgeführt, statt automatisch zu laufen).
- **Push-Benachrichtigungen** an das Handy, wenn eine Nachricht fertig
  verarbeitet wurde (aktuell reines Polling alle paar Sekunden).

Diese Punkte sind absichtlich für spätere Versionen zurückgestellt, um
eine kleine, tatsächlich funktionierende V1 zu priorisieren.
