# AI Human — Setup Guide

## Requirements
- Python 3.10 or newer
- Windows 10/11 (Linux/macOS possible but untested)

---

## Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2 — Choose your LLM provider

### Option A: Ollama (recommended — free, offline, works on low-end hardware)

1. Download Ollama: https://ollama.com/download
2. Install and run it (it starts automatically)
3. The system will **auto-detect your hardware** and pull the right model for you

Or pull manually:
```bash
# 4 GB RAM machine (minimum)
ollama pull tinyllama:1.1b
ollama pull moondream:1.8b

# 8 GB RAM machine (recommended)
ollama pull llama3.2:3b
ollama pull llava:7b

# 16 GB RAM machine (best quality)
ollama pull mistral:7b
ollama pull llava:13b
```

### Option B: LM Studio (GUI-based local models)

1. Download LM Studio: https://lmstudio.ai
2. Download any GGUF model inside LM Studio
3. Start the local server (port 1234)
4. Set `LLM_PROVIDER=lmstudio` in your `.env`

### Option C: Claude API (cloud)

1. Get API key: https://console.anthropic.com
2. Set in `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
3. Set `LLM_PROVIDER=anthropic`

### Option D: OpenAI API (cloud)

1. Set `OPENAI_API_KEY=sk-...` in `.env`
2. Set `LLM_PROVIDER=openai`

### Option E: Any OpenAI-compatible API

Any server that speaks `/v1/chat/completions`:
```env
LLM_PROVIDER=custom
CUSTOM_BASE_URL=http://your-server:port
CUSTOM_API_KEY=your-key
CUSTOM_MODEL=your-model-name
```

---

## Step 3 — Configure

```bash
copy .env.example .env
```

Edit `.env` — minimum required:
```env
LLM_PROVIDER=ollama   # or anthropic, openai, lmstudio, custom
```

---

## Step 4 — Check your hardware

```bash
python main.py --check
```

Output example:
```
  Hardware Report
  CPU    : Intel Core i5-8250U
  RAM    : 8.0 GB
  VRAM   : 0.0 GB (no GPU)
  Tier   : MEDIUM

  Recommended models (Ollama):
    Text   : llama3.2:3b
    Vision : llava:7b
    Context: 4096 tokens

  Install with:
    ollama pull llama3.2:3b
    ollama pull llava:7b
```

---

## Step 5 — Run

```bash
# With avatar UI (default)
python main.py

# Headless / terminal mode
python main.py --no-ui

# Give it a goal immediately
python main.py --goal "open Notepad and write Hello World"
```

---

## Hardware Tiers

| Tier | RAM | GPU | Best model |
|------|-----|-----|------------|
| Low | 4 GB | No | TinyLlama 1.1B |
| Medium | 8 GB | No | Llama 3.2 3B |
| High | 16 GB | No | Mistral 7B |
| GPU | Any | 8 GB VRAM | Llama 3.1 8B |

The system **automatically selects the right model** based on your hardware.
You can override this by setting `LLM_MODEL=` in `.env`.

---

## Troubleshooting

**"Ollama not found"**
→ Install from https://ollama.com and make sure it's running

**"Vision model not available"**
→ The agent will fall back to OCR text extraction automatically

**"ChromaDB error"**
→ Delete `data/chroma/` folder and restart

**High CPU usage**
→ Increase `LOOP_INTERVAL_SECONDS=5` in `.env`
→ Use a smaller model

**Safety dialog keeps appearing**
→ Lower `SAFETY_CONFIRM_THRESHOLD=8` to require confirmation less often
