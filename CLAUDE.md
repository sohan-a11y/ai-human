# CLAUDE.md

## Project

AI Human: autonomous AI agent that operates a Windows computer like a human worker.
Root directory: this folder.

## Build / Run

```bash
pip install -r requirements.txt
python launcher.py          # recommended (watchdog + auto-restart)
python main.py --check      # hardware report
python main.py --no-ui      # headless mode
python main.py --goal "..." # with initial goal
```

## Test

No automated test suite yet. Manual testing only.
Run `python main.py --check` to verify hardware detection works.

## Architecture

- `main.py` — entry point, wires all subsystems via `core/wiring.py` AgentWiring
- `core/agent.py` — AgentOrchestrator, main perceive-think-act-learn loop
- `core/wiring.py` — clean public API for attaching subsystems (use `agent.attach()`)
- `llm/` — multi-provider LLM abstraction (base.py ABC, factory.py auto-selection)
- `memory/` — ChromaDB vector store (episodic + semantic)
- `tools/registry.py` — auto-discovers tools from `tools/built_in/`, `skills/`, `tools/registry/`
- `safety/broker.py` — risk scoring (0-10) + confirmation dialogs

## Key API Signatures

```python
# SemanticMemory — ALWAYS use these exact parameter names:
semantic.store(text: str, source: str = "", tags: list[str] | None = None) -> str

# EpisodicMemory:
episodic.store(perception: str, action: str, outcome: str, goal: str = "") -> None

# AgentOrchestrator public properties:
agent.goal          # current goal (read-only)
agent.state         # AgentState enum (read-only)
agent.running       # bool (read-only)
agent.tools         # ToolRegistry (read-only)
agent.semantic      # SemanticMemory (read-only)
agent.episodic      # EpisodicMemory (read-only)
agent.context_window  # list[dict] (read/write)
agent.attach(name, component)  # attach optional subsystem
```

## Coding Conventions

- All tools inherit from `tools/base_tool.py` BaseTool
- Tool `run()` methods return `str`, never raise exceptions (catch and return error message)
- Config is pydantic-settings, reads from `.env` — add new fields to `config.py` Config class
- Never use `shell=True` in subprocess calls
- Never access `agent._private` from outside — use properties or `AgentWiring`
- EventBus has `publish()` method, NOT `emit()`
