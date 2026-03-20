# AI Human

**An autonomous AI agent that operates your computer like a human worker.**

AI Human uses large language models (local or cloud) to understand goals in plain language,
plan multi-step actions, and execute them — clicking, typing, writing code, browsing the web,
reading emails, managing files, and more — with no supervision required.

It perceives the screen, reasons about what to do, takes action, learns from failures, and
improves itself continuously. Runs fully offline on 4GB RAM or scales up to cloud LLMs.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [LLM Providers](#llm-providers)
- [Hardware Tiers](#hardware-tiers)
- [CLI Options](#cli-options)
- [Architecture](#architecture)
- [Core Loop](#core-loop)
- [Built-in Tools](#built-in-tools)
- [Skill Packs](#skill-packs)
- [Self-Creating Tools](#self-creating-tools)
- [Security Model](#security-model)
- [Web Dashboard](#web-dashboard)
- [Mobile App](#mobile-app)
- [Voice Control](#voice-control)
- [Autonomous Learning](#autonomous-learning)
- [Peer Network](#peer-network)
- [Scheduling Tasks](#scheduling-tasks)
- [Self-Modification](#self-modification)
- [Adding Custom Tools](#adding-custom-tools)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Category | Capabilities |
|---|---|
| **Multi-LLM** | Claude, GPT-4, Ollama (local), LM Studio, any OpenAI-compatible API |
| **Low-end hardware** | Runs on 4GB RAM with TinyLlama 1.1B — auto-selects model for your hardware |
| **Self-correcting** | On failure: diagnoses, searches for solution, learns, retries |
| **Self-rebuilding** | Agent can modify its own code, snapshot for rollback, auto-restart via watchdog |
| **Unlimited memory** | ChromaDB vector store — remembers everything, recalls by semantic similarity |
| **Computer control** | Mouse, keyboard, window management, file operations, terminal commands |
| **Web automation** | Playwright browser + Chrome/Edge extension for reliable DOM interaction |
| **60+ tools** | Web search, email, databases, archives, git, image gen, documents, and more |
| **Self-creating tools** | Agent can generate new tools at runtime from natural language descriptions |
| **Voice** | Wake word detection ("Hey AI"), speech-to-text, text-to-speech |
| **Multi-language** | Goals in any language — auto-translated via Google Translate or offline Argos |
| **Mobile app** | React Native companion — control the agent from your phone |
| **Web dashboard** | FastAPI status panel at localhost:8080 with SSE live updates |
| **Peer network** | Multiple instances share knowledge and delegate tasks via mDNS |
| **Learning** | Autonomous research during idle time — continuously builds knowledge |
| **Screen recording** | Records all agent actions to MP4 for review |
| **Scheduling** | Cron-style or natural language schedules ("every Monday at 9am") |
| **Image generation** | DALL-E, Stable Diffusion, Replicate, or free Pollinations.ai |

---

## Requirements

### Minimum (CPU-only, 4GB RAM)
- Python 3.10+
- Windows 10 or 11
- Ollama (for local models, auto-downloads on first run)

### Recommended (8GB+ RAM)
- Python 3.10+
- Windows 10 or 11
- Ollama with Llama 3.2 3B or Mistral 7B

### For GPU acceleration
- NVIDIA GPU with 8+ GB VRAM
- Ollama with Llama 3.1 8B

### Optional dependencies
- Tesseract OCR (for OCR fallback when no vision model available)
- Chrome/Edge browser (for Playwright web automation)
- Git (for git_tool)
- Node.js 18+ (for mobile companion app)

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/anthropics/ai-human.git
cd ai-human
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` — at minimum set `LLM_PROVIDER`:

**Local offline (no API key needed):**
```env
LLM_PROVIDER=ollama
LLM_MODEL=          # leave blank for auto-detect based on your hardware
```

**Claude API:**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**OpenAI:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 3. Install Ollama (for local models)

Download from https://ollama.com, then:
```bash
ollama serve   # keep running in background
```

AI Human auto-pulls the right model for your hardware on first run.

### 4. Run

```bash
python launcher.py                                    # recommended (watchdog + auto-restart)
python launcher.py --goal "Check emails and summarize" # with initial goal
python launcher.py --no-ui                             # headless terminal mode
python main.py --check                                 # hardware report
```

---

## LLM Providers

| Provider | Setup | Vision | Offline | Cost |
|----------|-------|--------|---------|------|
| **Ollama** | Install Ollama, run `ollama serve` | llava, moondream | Yes | Free |
| **LM Studio** | Install LM Studio, load a model | Via loaded model | Yes | Free |
| **Anthropic** | Set `ANTHROPIC_API_KEY` in .env | Claude Sonnet/Opus | No | Pay per token |
| **OpenAI** | Set `OPENAI_API_KEY` in .env | GPT-4o | No | Pay per token |
| **Custom** | Set `CUSTOM_BASE_URL` and `CUSTOM_MODEL` | Depends | Depends | Varies |

Provider is set via `LLM_PROVIDER` in `.env`. If `LLM_MODEL` is left blank, the system
auto-selects the best model based on your hardware (see Hardware Tiers).

---

## Hardware Tiers

AI Human auto-detects your hardware and selects the right model:

| Tier | RAM | Text Model | Vision Model |
|------|-----|-----------|--------------|
| **Low** | < 6 GB | tinyllama:1.1b | moondream:1.8b |
| **Medium** | 6-15 GB | llama3.2:3b | llava:7b |
| **High** | 16+ GB | mistral:7b | llava:13b |
| **GPU** | 8+ GB VRAM | llama3.1:8b | llava:13b |

Run `python main.py --check` to see your hardware tier and recommended models.

---

## CLI Options

```
python main.py [OPTIONS]

Options:
  --goal "..."         Set initial goal
  --no-ui              Headless terminal mode
  --check              Hardware report and exit
  --no-proactive       Disable background screen watching
  --no-remote          Disable web control panel (port 8080)
  --no-mobile          Disable mobile companion server (port 8081)
  --no-monitor         Disable OS event monitoring
  --no-wake-word       Disable "Hey AI" voice activation
  --no-learning        Disable autonomous learning loop
  --no-stress          Disable user stress detection
  --no-peers           Disable peer network discovery
  --no-recording       Disable screen recording
  --remote-port PORT   Web dashboard port (default: 8080)
  --mobile-port PORT   Mobile bridge port (default: 8081)
  --peer-port PORT     Peer network port (default: 8090)
  --lang LANG          UI language code (e.g. fr, es, ja)
  --wake-word WORD     Custom wake word (default: "hey ai")
```

---

## Architecture

```
launcher.py             Watchdog: restarts on crash, handles self-updates
  main.py               Entry point: wires all subsystems
    core/
      agent.py           Main perceive-think-act-learn loop
      wiring.py          Subsystem attachment (clean public API)
      event_bus.py       Thread-safe event queue
      scheduler.py       Cron-style task scheduling
      learning_loop.py   Autonomous idle-time research
      self_corrector.py  Failure diagnosis and recovery
      self_updater.py    Self-modification with rollback
      multi_agent.py     Parallel worker agents
      peer_network.py    mDNS peer discovery
    llm/
      base.py            LLMProvider ABC (all providers implement this)
      factory.py         Hardware detection + provider selection
      anthropic_provider.py
      openai_provider.py
      ollama_provider.py
      lmstudio_provider.py
    memory/
      vector_store.py    ChromaDB embedded client
      episodic.py        Every action + outcome stored forever
      semantic.py        Learned facts and knowledge
    perception/
      screen_capture.py  Fast screenshots via mss (multi-monitor)
      vision_analyzer.py Screenshot -> LLM -> natural language description
      uia_detector.py    Windows UI Automation (exact element positions)
      ocr_engine.py      Pytesseract fallback
      screen_diff.py     Detect what changed after an action
    actions/
      executor.py        Mouse, keyboard, file, process execution
    tools/
      registry.py        Auto-discovers and loads all tools
      built_in/          11 built-in tools (web, git, browser, docs...)
      registry/          AI-created tools (hot-reload at runtime)
    skills/              10 skill packs (60+ tools total)
    safety/
      broker.py          Risk scoring + confirmation dialogs
      risk_classifier.py Rule-based action risk classification
      audit_log.py       Every action attempt logged
    remote/
      server.py          FastAPI dashboard (port 8080)
      mobile_bridge.py   WebSocket bridge to mobile app (port 8081)
    audio/
      tts.py             Text-to-speech (pyttsx3, offline)
      stt.py             Speech-to-text (faster-whisper, offline)
      wake_word.py       "Hey AI" detection
    avatar/
      app.py             Tkinter floating face UI
```

---

## Core Loop

The agent runs a continuous **perceive-think-act-learn** cycle:

1. **Perceive** — Captures a screenshot, analyzes it with the vision LLM (or OCR fallback),
   detects UI elements via Windows UI Automation API (exact pixel positions)

2. **Think** — Recalls past experiences and knowledge from ChromaDB memory,
   builds a context message, asks the LLM "what should I do next?"

3. **Act** — Parses the LLM's JSON response, checks it through the Safety Broker
   (risk score 0-10), executes via ActionExecutor (mouse/keyboard/file/process)

4. **Learn** — Stores the action + outcome in episodic memory. On failure,
   invokes SelfCorrector to diagnose, research, and suggest a fix

---

## Built-in Tools

These are always available (loaded from `tools/built_in/`):

| Tool | Description |
|------|-------------|
| `web_search` | DuckDuckGo search (no API key needed) |
| `web_fetch` | Fetch and clean URL content (BeautifulSoup) |
| `ask_ai` | Ask ChatGPT via Playwright browser |
| `playwright_browser` | Full browser automation (Chromium) |
| `browser_extension_bridge` | WebSocket bridge to Chrome/Edge extension |
| `document_reader` | Read PDF, Excel, Word, PowerPoint files |
| `git_tool` | Git operations (clone, pull, commit, push, status) |
| `image_gen` | Image generation (DALL-E, Stable Diffusion, Pollinations.ai) |
| `sandbox_runner` | Execute Python code in sandboxed subprocess |
| `system_info` | CPU, RAM, disk, running processes |
| `integrations` | Gmail, Google Calendar API |
| `skill_creator` | Generate new tools at runtime from descriptions |
| `skill_list_created` | List AI-created tools |
| `skill_delete` | Delete an AI-created tool |

---

## Skill Packs

Loaded automatically from `skills/`:

### Excel (`skills/excel_skill.py`)
| Tool | Description |
|------|-------------|
| `excel_read_cells` | Read cells or ranges from Excel files |
| `excel_write_cell` | Write a value to a specific cell |
| `excel_formula` | Write formulas to cells |

### VS Code (`skills/vscode_skill.py`)
| Tool | Description |
|------|-------------|
| `vscode_open` | Open file/folder in VS Code |
| `vscode_run_task` | Run a VS Code task |
| `vscode_terminal_read` | Read VS Code terminal output |
| `vscode_install_extension` | Install a VS Code extension |

### Windows Explorer (`skills/windows_explorer_skill.py`)
| Tool | Description |
|------|-------------|
| `find_files` | Search files by name, extension, or content |
| `organize_files` | Auto-organize files into folders by type |
| `bulk_rename` | Rename multiple files with pattern matching |

### PowerShell (`skills/powershell_skill.py`)
| Tool | Description |
|------|-------------|
| `powershell_run` | Execute PowerShell commands |
| `powershell_script` | Run multi-line PowerShell scripts |
| `service_manager` | List, start, stop, restart Windows services |
| `env_var` | Get/set environment variables |

### Email (`skills/email_skill.py`)
| Tool | Description |
|------|-------------|
| `email_send` | Send email via SMTP (Gmail, Outlook, custom) |
| `email_read` | Read emails from IMAP inbox |
| `email_search` | Search emails by subject, sender, date |

Set `EMAIL_USER` and `EMAIL_PASS` in `.env` to use.

### Database (`skills/database_skill.py`)
| Tool | Description |
|------|-------------|
| `sqlite_query` | Execute SQL on SQLite databases |
| `sqlite_info` | Show tables and schema |
| `postgres_query` | Query PostgreSQL databases |
| `mysql_query` | Query MySQL databases |

### Clipboard (`skills/clipboard_skill.py`)
| Tool | Description |
|------|-------------|
| `clipboard_get` | Get current clipboard content |
| `clipboard_set` | Set clipboard content |
| `clipboard_history` | View/manage clipboard history |
| `clipboard_watch` | Monitor clipboard for changes |

### Archive (`skills/archive_skill.py`)
| Tool | Description |
|------|-------------|
| `archive_create` | Create zip or tar.gz archives |
| `archive_extract` | Extract archives |
| `archive_list` | List archive contents |

### Network (`skills/network_skill.py`)
| Tool | Description |
|------|-------------|
| `ping` | Ping a host |
| `port_scan` | Scan ports on a host |
| `dns_lookup` | DNS lookup (A, AAAA, MX, NS, TXT) |
| `download_file` | Download a file from URL |
| `http_request` | Make HTTP requests (GET, POST, PUT, DELETE) |
| `network_info` | Show local network configuration |

### Task Manager (`skills/task_manager_skill.py`)
| Tool | Description |
|------|-------------|
| `process_list` | List processes with CPU/memory usage |
| `process_kill` | Kill a process by PID or name |
| `system_resources` | Show CPU, RAM, disk, network usage |
| `start_process` | Start a new process |

### Windows Registry (`skills/registry_skill.py`)
| Tool | Description |
|------|-------------|
| `registry_read` | Read registry keys and values |
| `registry_write` | Write registry values (with safety blocks) |
| `registry_search` | Search registry by pattern |

### Windows Scheduler (`skills/scheduler_skill.py`)
| Tool | Description |
|------|-------------|
| `win_task_list` | List Windows Task Scheduler tasks |
| `win_task_create` | Create scheduled tasks |
| `win_task_delete` | Delete scheduled tasks |
| `win_task_run` | Manually run a task |
| `win_task_info` | Get task details |

### Text Manipulation (`skills/text_skill.py`)
| Tool | Description |
|------|-------------|
| `regex_replace` | Find/replace with regex in files |
| `regex_find` | Find all regex matches |
| `text_format` | JSON/XML prettify, sort lines, deduplicate |
| `text_diff` | Unified diff between two files |
| `text_encoding` | Detect/convert file encoding |
| `text_stats` | Word count, line count, file statistics |

---

## Self-Creating Tools

The agent can generate its own tools at runtime. When it encounters a task that no
existing tool handles, it calls the `skill_creator` tool:

1. Agent describes what it needs (e.g., "I need a CSV merger tool")
2. LLM generates a complete `BaseTool` subclass
3. Code is validated (AST syntax check + security scan)
4. Saved to `tools/registry/` and hot-reloaded immediately
5. Agent uses the new tool in the same conversation

Dangerous patterns (`eval`, `exec`, `shell=True`, `os.system`) are blocked in generated code.

AI-created tools persist across restarts. Manage them with `skill_list_created` and `skill_delete`.

---

## Security Model

AI Human has broad system access. Security is enforced at multiple layers:

### Safety Broker
Every action is risk-scored 0-10 before execution:
- Score < 7: Executed immediately
- Score 7-8: Confirmation dialog shown to user
- Score 9-10: Hard blocked, never executed

Configure thresholds in `.env`:
```env
SAFETY_CONFIRM_THRESHOLD=7
SAFETY_BLOCK_THRESHOLD=9
```

### Credential Vault
API keys and passwords are stored in an encrypted vault (Fernet: AES-128-CBC + HMAC-SHA256,
PBKDF2 key derivation with 200,000 iterations).

Set `AI_HUMAN_VAULT_PASS` as an environment variable (never as CLI argument).

### Remote Access
Generate tokens for the web dashboard and mobile app:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add to `.env`:
```env
REMOTE_API_TOKEN=<your_token>
MOBILE_API_TOKEN=<your_token>
```

### Other Protections
- No `shell=True` in subprocess calls
- CORS restricted to localhost
- Generated tool code scanned for dangerous patterns
- Full audit log of all action attempts in `data/audit/`
- Registry write blocks for critical system paths

See [SECURITY.md](SECURITY.md) for the full security model and vulnerability disclosure.

---

## Web Dashboard

Access at `http://localhost:8080` while the agent is running.

Features:
- Live agent status and current goal
- Send new goals
- View live screenshot
- Server-sent events (SSE) stream for real-time updates
- Schedule management
- Memory browser

Disable with `--no-remote`.

---

## Mobile App

Control AI Human from your phone (React Native + Expo):

1. Agent starts the WebSocket server on port 8081 automatically
2. Set up the mobile app:
   ```bash
   cd mobile_app
   npm install
   npx expo start
   ```
3. Scan the QR code with the Expo Go app
4. Enter your PC's local IP address when prompted

Features: send goals, view status, live screenshot stream, push notifications.

Disable with `--no-mobile`.

---

## Voice Control

AI Human supports voice activation:

1. **Wake Word**: Say "Hey AI" (customizable with `--wake-word`)
2. **Speech-to-Text**: Uses faster-whisper (offline) to transcribe your goal
3. **Text-to-Speech**: Agent speaks status updates via pyttsx3

Requires a microphone. Disable with `--no-wake-word`.

---

## Autonomous Learning

When idle for 5+ minutes, AI Human autonomously:
- Researches knowledge gaps via web search
- Analyzes past failures and extracts lessons
- Explores its own capabilities with practice tasks
- Stores all learnings in semantic memory

This runs in a background thread and does not interfere with active goals.
Disable with `--no-learning`.

---

## Peer Network

Multiple AI Human instances on the same network can:
- Discover each other via mDNS/Bonjour
- Share learned knowledge
- Delegate tasks to peers

Enable by running AI Human on multiple machines on the same LAN.
Default port: 8090 (configure with `--peer-port`). Disable with `--no-peers`.

---

## Scheduling Tasks

### From Code
```python
scheduler.add_task("Check emails", {"type": "every_day", "value": "09:00"})
```

### From Headless Mode
```
Goal > schedule every day at 9am: check emails and summarize
```

### Schedule Types
- `every_day "HH:MM"` — daily at specific time
- `every_hour` — every hour
- `interval <seconds>` — every N seconds
- `once <datetime>` — one-time execution
- `cron <expression>` — standard cron syntax

---

## Self-Modification

The agent can modify its own source code:
1. User says "customize yourself to do X"
2. Agent takes a code snapshot (rollback point)
3. LLM reads relevant files and writes modifications
4. Changes are AST-validated for syntax
5. Agent restarts via the watchdog launcher
6. If the new version crashes within 5 minutes, the launcher auto-rolls back

---

## Adding Custom Tools

### Method 1: Manual

Create a file in `tools/built_in/` or `skills/`:

```python
# tools/built_in/my_tool.py
from tools.base_tool import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful for the agent."
    parameters = {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input text"},
        },
        "required": ["input"],
    }

    def run(self, input: str) -> str:
        return f"Result: {input}"
```

Tools are auto-discovered at startup. No registration code needed.

### Method 2: Hot-Reload

Drop a `.py` file into `tools/registry/`. The agent can call `hot_reload()` to pick it up
without restarting.

### Method 3: AI-Generated

The agent creates its own tools via the `skill_creator` tool. Just give it a goal that
requires a new capability and it will build the tool itself.

---

## Troubleshooting

### Ollama not found
Install from https://ollama.com and ensure `ollama serve` is running in the background.

### Vision model not available
Set `VISION_MODEL` and `VISION_PROVIDER` in `.env`. For Ollama: `llava:7b` or `moondream`.
The agent falls back to OCR if no vision model is configured.

### ChromaDB errors
Delete `data/chroma/` to reset the database (note: this clears all memory).

### High CPU usage
Increase `LOOP_INTERVAL_SECONDS` in `.env` (default: 3). Use `--no-proactive` to disable
background screen watching. Use `--no-learning` to disable idle research.

### Module import errors
Ensure all dependencies are installed: `pip install -r requirements.txt`.
Some features require optional packages (see comments in requirements.txt).

### Avatar window doesn't appear
Set `SHOW_AVATAR=true` in `.env`. If tkinter is not available, the agent falls back to
headless terminal mode automatically.

### Permission errors (UIA, services, registry)
Some tools require administrator privileges. Run your terminal as Administrator.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code structure, and PR guidelines.

---

## Reporting Security Issues

See [SECURITY.md](SECURITY.md) — **do not open public issues for security vulnerabilities**.

---

## Documentation

Detailed project documentation: [_project_docs/00_INDEX.md](_project_docs/00_INDEX.md)

---

## License

MIT — see [LICENSE](LICENSE)
