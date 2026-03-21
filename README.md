<div align="center">

<h1>🤖 AI Human</h1>

<h3>The World's First Fully Autonomous AI Agent That Operates Your Computer Like a Human Worker — Runs 100% Offline on 4GB RAM</h3>

<p>
  <a href="https://github.com/yourusername/ai-human/stargazers"><img src="https://img.shields.io/github/stars/yourusername/ai-human?style=for-the-badge&logo=github&color=gold" alt="Stars"></a>
  <a href="https://github.com/yourusername/ai-human/network/members"><img src="https://img.shields.io/github/forks/yourusername/ai-human?style=for-the-badge&logo=github&color=blue" alt="Forks"></a>
  <a href="https://github.com/yourusername/ai-human/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/yourusername/ai-human/releases"><img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python"></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/LLM-Ollama%20%7C%20Claude%20%7C%20GPT--4%20%7C%20Any-purple?style=for-the-badge" alt="LLM">
  <img src="https://img.shields.io/badge/Hardware-4GB%20RAM%20Minimum-orange?style=for-the-badge" alt="4GB RAM">
</p>

<p>
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-why-ai-human">Why AI Human</a> •
  <a href="#-capabilities">Capabilities</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-llm-providers">LLM Providers</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

**⚡ Nothing like this has existed before in AI history.**

AI Human is not a chatbot. It is not a simple script. It is a fully autonomous digital worker that **sees your screen**, **understands what it sees**, **plans multi-step actions**, **executes them with mouse and keyboard**, **learns from every mistake**, and **improves itself over time — including rewriting its own code.**

It works on a $200 laptop. No internet required. No cloud subscription. Completely free.

</div>

---

## 🔥 Why AI Human Is Different From Everything Else

| Feature | **AI Human** | OpenAI Computer Use | Claude Computer Use | AutoGPT | MetaGPT |
|---|:---:|:---:|:---:|:---:|:---:|
| Works offline / no internet | ✅ | ❌ | ❌ | ❌ | ❌ |
| Runs on 4GB RAM | ✅ | ❌ | ❌ | ❌ | ❌ |
| Operates real computer (mouse + keyboard) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Modifies its own source code | ✅ | ❌ | ❌ | ❌ | ❌ |
| Creates new tools at runtime | ✅ | ❌ | ❌ | ❌ | ❌ |
| Learns autonomously while idle | ✅ | ❌ | ❌ | ❌ | ❌ |
| Free & open source | ✅ | ❌ | ❌ | ✅ | ✅ |
| Works with ANY LLM provider | ✅ | ❌ | ❌ | Partial | ❌ |
| Self-heals on failure | ✅ | ❌ | ❌ | Partial | ❌ |
| Peer network (agents share knowledge) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Mobile companion app | ✅ | ❌ | ❌ | ❌ | ❌ |
| Voice-controlled ("Hey AI") | ✅ | ❌ | ❌ | ❌ | ❌ |

> **OpenAI Computer Use costs money, requires internet, and can't learn. AI Human runs free, offline, and gets smarter every day.**

---

## ⚡ What AI Human Can Do Right Now

Tell it a goal in plain English. It does the rest.

```
"Check my emails, summarize the important ones, and draft replies for anything urgent."

"Research competitors in my market, write a report, and save it to my Desktop."

"Find all Python files modified this week, run the tests, and commit the passing ones to GitHub."

"Monitor my screen and alert me if my build breaks."

"Every Monday at 9am: generate a weekly report, email it to my team, and archive last week's."
```

It **sees your screen**, **clicks**, **types**, **opens apps**, **writes code**, **reads files**, **sends emails**, **browses the web**, **manages databases** — everything a human assistant would do.

---

## 🧠 The Capabilities That Have Never Existed Together Before

### 1. Self-Modifying AI — It Rewrites Its Own Code
Tell it to customize itself. It reads its own source files, modifies the code, validates with AST, takes a snapshot, restarts, and auto-rolls back if something breaks. No human in the loop.

### 2. Self-Creating Tools — It Builds Its Own Capabilities
Encounter a task no existing tool handles? The agent generates a new Python tool on the fly, security-validates it, hot-reloads it, and uses it — all in the same session.

### 3. Self-Healing — It Never Gives Up
On failure: diagnoses the error → searches the web for solutions → applies the fix → retries. It keeps trying until it succeeds or escalates to you.

### 4. Runs on 4GB RAM — True Democratization of AI
Auto-detects your hardware. Selects the best model that fits. TinyLlama 1.1B on 4GB. Mistral 7B on 16GB. No manual configuration needed.

### 5. Fully Offline — Your Data Never Leaves Your Machine
All computation happens locally via Ollama. No API keys. No subscriptions. No cloud. Your files, emails, and actions stay on your computer.

### 6. Learns While You Sleep
When idle for 5+ minutes, it autonomously researches knowledge gaps, analyzes past failures, extracts lessons, and stores everything in its permanent vector memory. It wakes up smarter than when it went idle.

### 7. Peer Network — A Swarm of AI Workers
Run AI Human on multiple machines. They discover each other via mDNS, share learned knowledge, and delegate tasks. One agent handles email; another writes code; another monitors the market.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Windows 10 or 11
- 4GB RAM minimum (8GB+ recommended)
- [Ollama](https://ollama.com) for offline use (optional if using Claude/OpenAI API)

### Install

```bash
git clone https://github.com/yourusername/ai-human.git
cd ai-human
pip install -r requirements.txt
cp .env.example .env
```

### Configure (choose one)

**Option A — Free, Fully Offline (no API key needed):**
```env
LLM_PROVIDER=ollama
# LLM_MODEL is auto-selected based on your hardware
```
Then install Ollama from https://ollama.com and run `ollama serve`. AI Human pulls the right model automatically.

**Option B — Claude API:**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**Option C — OpenAI:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Run

```bash
python launcher.py                                       # recommended (auto-restart + watchdog)
python launcher.py --goal "Check my emails and summarize"  # with a starting goal
python main.py --check                                   # hardware report (what model will it use?)
python main.py --no-ui                                   # headless terminal mode
```

Open `http://localhost:8080` in your browser for the live dashboard.

---

## 🔌 LLM Providers

Works with every major LLM provider. Switch anytime by changing one line in `.env`.

| Provider | Offline | Vision | Cost | Setup |
|---|:---:|:---:|---|---|
| **Ollama** (local) | ✅ | llava, moondream | Free | Install Ollama, run `ollama serve` |
| **LM Studio** (local) | ✅ | Via loaded model | Free | Load any GGUF model |
| **Anthropic** (Claude) | ❌ | Claude Sonnet/Opus | Pay per token | Set `ANTHROPIC_API_KEY` |
| **OpenAI** (GPT-4) | ❌ | GPT-4o | Pay per token | Set `OPENAI_API_KEY` |
| **Any OpenAI-compatible** | Depends | Depends | Varies | Set `CUSTOM_BASE_URL` + `CUSTOM_MODEL` |

---

## 💻 Hardware Auto-Detection

AI Human detects your hardware and selects the best model automatically. No configuration needed.

| Your Hardware | Text Model | Vision Model | What It Can Do |
|---|---|---|---|
| 4 GB RAM (CPU only) | TinyLlama 1.1B | Moondream 1.8B | Full automation, all tools |
| 6–15 GB RAM | Llama 3.2 3B | LLaVA 7B | Faster reasoning, richer responses |
| 16+ GB RAM | Mistral 7B | LLaVA 13B | Near-GPT-4 quality locally |
| 8+ GB VRAM (GPU) | Llama 3.1 8B | LLaVA 13B | Full speed, near-instant responses |

Run `python main.py --check` to see your hardware tier and what will be used.

---

## 🛠️ Built-in Tools (100+)

### Core Computer Control
- **Mouse & keyboard**: click, type, drag, scroll, hotkeys
- **Window management**: open, close, focus, resize any app
- **File system**: read, write, search, organize, bulk-rename
- **Terminal**: execute commands securely (no shell injection)
- **Screen capture**: real-time perception + change detection

### Web & Research
- **Web search**: DuckDuckGo (no API key needed)
- **Browser automation**: Playwright + Chrome/Edge extension
- **Web scraping**: fetch and clean any URL content
- **Research pipeline**: search → fetch → LLM summarize → memory

### Productivity
- **Email**: read, send, search (Gmail, Outlook, IMAP/SMTP)
- **Calendar**: Google Calendar integration
- **Documents**: read PDF, Excel, Word, PowerPoint
- **Git**: clone, commit, push, PR creation via GitHub CLI
- **Databases**: SQLite, PostgreSQL, MySQL queries

### AI & Generation
- **Image generation**: DALL-E → Stable Diffusion → ComfyUI → Pollinations.ai (free fallback)
- **Ask any AI**: query ChatGPT via browser when needed
- **Code execution**: sandboxed Python subprocess runner
- **Multi-language**: 100+ languages via Google Translate / Argos (offline)

### System & Automation
- **PowerShell**: run scripts and commands
- **Windows Registry**: read/write with safety guards
- **Windows Task Scheduler**: create and manage scheduled tasks
- **Services**: list, start, stop Windows services
- **Process manager**: list, kill, start processes

### Reverse Engineering
- **Binary analysis**: Radare2 disassembly, function detection
- **Decompiler**: Ghidra → RetDec → r2ghidra auto-select
- **String extraction**: URLs, IPs, API endpoints, credentials
- **RE report**: full Markdown + JSON analysis with threat indicators

### Skill Packs (Auto-Loaded)
Excel · VS Code · Windows Explorer · PowerShell · Email · Database · Clipboard · Archives · Network · Task Manager · Registry · Scheduler · Text Processing

---

## 🏗️ Architecture

```
launcher.py          ← Watchdog: restarts on crash, injects version, handles self-updates
  main.py            ← Entry point: wires all subsystems via AgentWiring
    core/
      agent.py       ← AgentOrchestrator: perceive → think → act → learn loop
      wiring.py      ← Clean public API for attaching subsystems
      event_bus.py   ← Thread-safe publish/subscribe between all modules
      nl_scheduler.py         ← Natural language → ParsedSchedule
      learning_loop.py        ← Autonomous idle-time research
      self_corrector.py       ← Failure diagnosis and recovery
      self_updater.py         ← Self-modification with snapshot + rollback
      peer_network.py         ← mDNS peer discovery and knowledge sharing
      credential_manager.py   ← Fernet AES-128-CBC encrypted vault
      performance_dashboard.py← JSONL metrics + Markdown reports
      auto_documentation.py   ← Background: AGENT_LOG.md, KNOWLEDGE_BASE.md
    llm/
      base.py        ← LLMProvider ABC
      factory.py     ← Hardware detection + auto model selection
      anthropic_provider.py / openai_provider.py / ollama_provider.py / lmstudio_provider.py
    memory/
      vector_store.py  ← ChromaDB PersistentClient (unlimited)
      episodic.py      ← Every action + outcome stored forever
      semantic.py      ← Learned facts and knowledge
    perception/
      screen_capture.py  ← Fast multi-monitor screenshots (mss)
      vision_analyzer.py ← Screenshot → Vision LLM → natural language
      uia_detector.py    ← Windows UI Automation (exact element positions)
      ocr_engine.py      ← Tesseract fallback
      screen_diff.py     ← Detect what changed after an action
      stress_detector.py ← Typing errors + mouse jitter → 5-level stress score
      screen_recorder.py ← MP4 recording of all agent actions
    actions/
      executor.py    ← Mouse, keyboard, file, process (no shell=True)
    tools/
      registry.py    ← Auto-discovers tools from built_in/, skills/, registry/
      built_in/      ← Core tools (always available)
      registry/      ← AI-created tools (hot-reload)
    skills/          ← Skill packs (auto-loaded)
    safety/
      broker.py          ← Risk scoring 0-10 + confirmation dialogs
      risk_classifier.py ← Rule-based action risk classification
      audit_log.py       ← Every action attempt logged to data/audit/
    remote/
      server.py          ← FastAPI dashboard port 8080 (auth + rate limiting)
      mobile_bridge.py   ← WebSocket bridge to mobile app port 8081
    audio/
      wake_word.py   ← OpenWakeWord → Vosk → faster-whisper auto-select
      stt.py         ← Speech-to-text (offline)
      tts.py         ← Text-to-speech (pyttsx3, offline)
    avatar/
      app.py         ← Tkinter floating face UI
    reverse_engineering/
      binary_analyzer.py    ← Radare2 disassembly + function detection
      string_extractor.py   ← ASCII + UTF-16LE + categorization
      decompiler_bridge.py  ← Ghidra → RetDec → r2ghidra
      re_reporter.py        ← Markdown + JSON threat report
    plugins/
      marketplace.py ← Plugin system with AST security scanning
```

---

## 🔄 Core Loop: Perceive → Think → Act → Learn

```
┌─────────────────────────────────────────────────────────────┐
│                     AgentOrchestrator                       │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │ PERCEIVE │──▶│  THINK   │──▶│   ACT    │──▶│  LEARN  │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│       │               │               │               │     │
│  Screenshot      Memory recall    Safety check    Store     │
│  Vision LLM      LLM reasoning    Execute action  Episodic  │
│  UIA elements    Tool selection   Mouse/keyboard  On fail:  │
│  Screen diff     JSON plan        File/process    Diagnose  │
│                                                   Research  │
│                                                   Retry     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Security Model

AI Human has broad system access. Multiple layers protect against misuse:

### Safety Broker
Every action is risk-scored 0–10 before execution:
- **Score < 7** → Executed immediately
- **Score 7–8** → Confirmation dialog shown to user
- **Score 9–10** → Hard blocked, never executed

### Credential Vault
API keys and passwords encrypted with Fernet (AES-128-CBC + HMAC-SHA256, PBKDF2 200,000 iterations). Set `AI_HUMAN_VAULT_PASS` as environment variable.

### Other Protections
- No `shell=True` anywhere in subprocess calls
- CORS restricted to localhost only
- AI-generated tool code scanned for dangerous patterns before execution
- Full audit log of all action attempts in `data/audit/`
- Registry writes blocked for critical system paths

See [SECURITY.md](SECURITY.md) for the complete security model and responsible disclosure.

---

## 📱 Mobile Companion App

Control AI Human from your phone (React Native + Expo):

```bash
cd mobile_app
npm install
npx expo start
```

Scan the QR code with Expo Go. Features: send goals, live status, screenshot stream, push notifications.

---

## 🎙️ Voice Control

1. Say **"Hey AI"** (customizable wake word)
2. Speak your goal naturally
3. Agent transcribes offline with faster-whisper, executes, and speaks back via pyttsx3

Fully offline. No cloud STT service required.

---

## 🧬 Self-Modification

```
User: "customize yourself to send me a daily summary by email"
  ↓
Agent reads its own scheduler.py and email_skill.py
  ↓
LLM writes the modification
  ↓
AST validation (syntax + security check)
  ↓
Snapshot saved (rollback point)
  ↓
Agent restarts via launcher watchdog
  ↓
If crash within 5 minutes → auto-rollback to snapshot
```

---

## 📅 Natural Language Scheduling

```
"every Monday at 9am: generate weekly report and email the team"
"tomorrow at 3pm: remind me to call the client"
"every hour: check if the server is responding"
"in 30 minutes: save and close all open documents"
```

The NL parser converts natural language to exact cron-style schedules. No syntax to learn.

---

## 🌐 Peer Network

Run AI Human on multiple machines on the same network:
- Instances discover each other via mDNS/Bonjour automatically
- Share learned knowledge across machines
- Delegate tasks to whichever peer is available
- One agent handles email, another writes code, another monitors systems

---

## 🔧 Adding Custom Tools

**Method 1: Manual (permanent)**
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
Auto-discovered at startup. No registration needed.

**Method 2: Hot-Reload**
Drop a `.py` file into `tools/registry/`. Call `hot_reload()` — no restart needed.

**Method 3: Let the AI build it**
Give the agent a goal it can't handle. It writes the tool, validates it, and uses it — all in the same session.

---

## ⚙️ CLI Reference

```
python main.py [OPTIONS]

  --goal "..."         Set initial goal
  --no-ui              Headless terminal mode
  --check              Hardware report and exit
  --no-proactive       Disable background screen watching
  --no-remote          Disable web dashboard (port 8080)
  --no-mobile          Disable mobile companion server (port 8081)
  --no-wake-word       Disable "Hey AI" voice activation
  --no-learning        Disable autonomous learning loop
  --no-stress          Disable user stress detection
  --no-peers           Disable peer network discovery
  --no-recording       Disable screen recording
  --lang LANG          UI language (e.g. fr, es, ja, zh)
  --wake-word WORD     Custom wake word (default: "hey ai")
  --remote-port PORT   Web dashboard port (default: 8080)
  --mobile-port PORT   Mobile bridge port (default: 8081)
  --peer-port PORT     Peer network port (default: 8090)
```

---

## 🔍 Troubleshooting

**Ollama not found** — Install from https://ollama.com and keep `ollama serve` running.

**Vision model not available** — Set `VISION_MODEL` and `VISION_PROVIDER` in `.env`. Agent falls back to OCR automatically.

**ChromaDB errors** — Delete `data/chroma/` to reset memory database.

**High CPU usage** — Increase `LOOP_INTERVAL_SECONDS` in `.env`. Use `--no-proactive` and `--no-learning`.

**Module import errors** — Run `pip install -r requirements.txt`. Some features need optional packages (see comments in requirements.txt).

**Permission errors (registry, services, UIA)** — Run terminal as Administrator.

---

## 🤝 Contributing

We welcome contributions of all kinds: new tools, new LLM providers, bug fixes, documentation, translations.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code conventions, and security coding rules.

**Good first issues:**
- New skill pack for a popular app
- New LLM provider integration
- UI improvements to the web dashboard
- Additional language support
- Documentation and examples

---

## 🔒 Security

Found a vulnerability? Please read [SECURITY.md](SECURITY.md) and disclose responsibly — **do not open public issues for security vulnerabilities**.

---

## 📄 License

MIT — see [LICENSE](LICENSE)

Free to use, modify, and distribute. Commercial use allowed.

---

<div align="center">

**If AI Human saved you time or blew your mind, please give it a ⭐**

*The star helps others discover it — and every star motivates us to keep building.*

**[⭐ Star this repo](https://github.com/yourusername/ai-human)** · **[🐛 Report a bug](https://github.com/yourusername/ai-human/issues)** · **[💡 Request a feature](https://github.com/yourusername/ai-human/issues)**

---

*Built by humans. Runs without them.*

</div>
