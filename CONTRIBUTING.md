# Contributing to AI Human

Thank you for helping make AI Human better! This guide covers how to contribute code,
report bugs, and propose features.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your change: `git checkout -b feature/your-feature-name`
4. **Set up the environment:**
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your settings
   ```

## Types of Contributions

### Bug Reports
Open a GitHub Issue with:
- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (from `data/logs/`)

### Feature Requests
Open a GitHub Issue tagged `enhancement` with:
- Use case and motivation
- Proposed interface / behavior
- Any known limitations

### Code Contributions
- Keep PRs focused — one feature or fix per PR
- Follow the existing code style (no formatter enforced, but be consistent)
- Add docstrings to new public classes and methods
- Test your changes manually before submitting

## Security Contributions

**Do NOT open public issues for security vulnerabilities.**
See [SECURITY.md](SECURITY.md) for the responsible disclosure process.

When adding new features:
- Never use `shell=True` in subprocess calls with user-controlled input
- Never use `eval()` or `exec()` with external data
- Validate all file paths against allowed directories
- Use `secrets.compare_digest()` for token comparison (not `==`)
- Add new API endpoints with `Depends(verify_token)`

## Code Structure

```
ai-human/
├── core/          # Agent brain: orchestrator, scheduler, memory, learning
├── llm/           # LLM provider abstraction (Anthropic, OpenAI, Ollama...)
├── memory/        # ChromaDB vector store, episodic + semantic memory
├── perception/    # Screen capture, OCR, UIA, screen diff, stress detection
├── actions/       # ActionExecutor — mouse, keyboard, file, process operations
├── tools/         # Tools the agent can call (built-in + skill packs)
├── audio/         # TTS, STT, wake word detection
├── remote/        # FastAPI web dashboard + mobile bridge
├── safety/        # SafetyBroker — risk scoring and action blocking
├── plugins/       # Plugin marketplace and loading
├── skills/        # Skill packs (Excel, VSCode, Windows Explorer...)
├── reverse_engineering/  # Binary analysis tools (PE parser, strings, decompiler)
├── providers/     # LLM provider implementations
├── utils/         # Logging, hardware detection, helpers
├── mobile_app/    # React Native companion app
└── browser_extension/   # Chrome/Edge extension for browser control
```

## Adding a New Tool

1. Create a file in `tools/built_in/` or `skills/`
2. Subclass `BaseTool` from `tools/base_tool.py`
3. Define `name`, `description`, `parameters`, and `run()`
4. The tool is auto-discovered at startup

Example:
```python
from tools.base_tool import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful."
    parameters = {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "What to process"},
        },
        "required": ["input"],
    }

    def run(self, input: str) -> str:
        return f"Processed: {input}"
```

## Adding a New LLM Provider

1. Create a file in `providers/`
2. Subclass `LLMProvider` from `llm/base.py`
3. Implement `generate()`, `stream()`, `embed()`, `supports_vision()`, `context_window`, `model_name`
4. Register it in `llm/factory.py`

## Pull Request Checklist

- [ ] Code runs without errors
- [ ] No `shell=True` with user input
- [ ] No hardcoded secrets or absolute paths
- [ ] New tools have `name`, `description`, `parameters`, `run()`
- [ ] New API endpoints are protected with `verify_token`
- [ ] `.gitignore` is not modified to include sensitive files
- [ ] PR description explains the change and motivation

## License

By contributing, you agree that your contributions are licensed under the MIT License.
