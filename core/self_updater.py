"""
SelfUpdater — the AI can modify, upgrade, or customize its own code.

Full cycle:
  1. User says "customize yourself to do X"
  2. Agent calls self_update action with a description
  3. SelfUpdater takes a snapshot of current code (rollback point)
  4. LLM reads relevant files and writes modified versions
  5. Syntax validation on all changed files
  6. Write a restart signal file
  7. Current process exits → Launcher picks up and starts new version
  8. New version runs for 5 minutes — if it crashes → Launcher rolls back
  9. Rollback restores old code and restarts

This makes the AI genuinely self-modifying and self-healing.
"""

from __future__ import annotations

import ast
import json
import os
import sys
import time
from pathlib import Path

from llm.base import LLMProvider
from llm.message_builder import system_message, text_message
from core.version_manager import VersionManager
from utils.logger import get_logger

log = get_logger(__name__)

_ROOT = Path(__file__).parent.parent
_SIGNAL_FILE = _ROOT / "data" / "restart_signal.json"

_MODIFY_SYSTEM = """You are modifying the AI Human agent's own Python source code.
You will be given:
- The user's customization request
- The current content of relevant files

Return a JSON object where keys are relative file paths and values are the complete new file content:
{
  "core/agent.py": "...complete new content...",
  "prompts/system_prompt.py": "...complete new content..."
}

Rules:
- Only modify files that need to change for this customization
- Return COMPLETE file contents, not diffs or snippets
- Keep all existing functionality unless explicitly asked to remove it
- Write clean, working Python code
- Return only the JSON, no explanation
"""


class SelfUpdater:

    def __init__(self, llm: LLMProvider):
        self._llm = llm
        self._versions = VersionManager()

    def update(self, request: str, relevant_files: list[str] | None = None) -> dict:
        """
        Main entry point. Applies a customization request to the codebase.

        Returns:
          {"success": True, "version_id": "v_...", "changes": [...], "restart_in": 300}
          {"success": False, "error": "..."}
        """
        log.info(f"Self-update requested: {request}")

        # Step 1: Snapshot current state
        version_id = self._versions.snapshot()
        log.info(f"Snapshot created: {version_id}")

        # Step 2: Identify files to modify
        if not relevant_files:
            relevant_files = self._identify_relevant_files(request)

        # Step 3: Read current contents
        file_contents = {}
        for rel_path in relevant_files:
            full = _ROOT / rel_path
            if full.exists():
                file_contents[rel_path] = full.read_text(encoding="utf-8")

        # Step 4: Ask LLM to write modified versions
        modifications = self._generate_modifications(request, file_contents)
        if not modifications:
            return {"success": False, "error": "LLM did not return valid file modifications"}

        # Step 5: Validate syntax of all modified Python files
        errors = self._validate_syntax(modifications)
        if errors:
            log.error(f"Syntax errors in generated code: {errors}")
            return {"success": False, "error": f"Syntax error: {errors}"}

        # Step 6: Write modified files
        changed = []
        for rel_path, content in modifications.items():
            full = _ROOT / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            changed.append(rel_path)
            log.info(f"Modified: {rel_path}")

        # Step 7: Write restart signal for launcher
        signal = {
            "action": "restart",
            "new_version": None,  # run from root (modifications are in-place)
            "previous_version": version_id,
            "wait_seconds": 300,          # 5 minutes
            "max_startup_errors": 3,
            "triggered_at": time.time(),
            "reason": request,
        }
        _SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SIGNAL_FILE.write_text(json.dumps(signal, indent=2), encoding="utf-8")

        log.info(f"Restart signal written. Shutting down in 3 seconds...")

        # Step 8: Schedule shutdown so launcher can restart
        def _shutdown():
            time.sleep(3)
            os._exit(0)  # Hard exit — launcher will restart

        import threading
        threading.Thread(target=_shutdown, daemon=True).start()

        return {
            "success": True,
            "version_id": version_id,
            "changes": changed,
            "restart_in": 3,
            "message": f"Applied {len(changed)} changes. Restarting in 3 seconds. Previous version saved as {version_id}.",
        }

    def rollback_to_previous(self) -> bool:
        """Manually rollback to the last known good version."""
        prev = self._versions.get_previous_version()
        if not prev:
            log.error("No previous version to rollback to")
            return False
        return self._versions.rollback(prev)

    def _identify_relevant_files(self, request: str) -> list[str]:
        """Use LLM to figure out which files are relevant to the request."""
        try:
            # Get all Python files
            all_py = [str(p.relative_to(_ROOT)).replace("\\", "/")
                      for p in _ROOT.rglob("*.py")
                      if "versions" not in str(p) and "__pycache__" not in str(p)]

            messages = [
                system_message("You are a code navigation assistant. Return only a JSON list of file paths."),
                text_message("user",
                    f"Given this customization request:\n\"{request}\"\n\n"
                    f"Which of these files likely need to be modified?\n"
                    f"Files:\n{chr(10).join(all_py)}\n\n"
                    f"Return a JSON array of file paths, max 5 files. Return only JSON."),
            ]
            raw = self._llm.generate(messages)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            files = json.loads(raw)
            return [f for f in files if isinstance(f, str)]
        except Exception as e:
            log.warning(f"Could not identify relevant files: {e}")
            # Default to common modification targets
            return ["core/agent.py", "prompts/system_prompt.py"]

    def _generate_modifications(self, request: str, current_files: dict) -> dict | None:
        """Ask LLM to write the modified file contents."""
        try:
            files_text = "\n\n".join(
                f"=== {path} ===\n{content}" for path, content in current_files.items()
            )
            messages = [
                system_message(_MODIFY_SYSTEM),
                text_message("user",
                    f"Customization request: {request}\n\n"
                    f"Current file contents:\n{files_text}"),
            ]
            raw = self._llm.generate(messages, max_tokens=4096)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(raw)
            return result if isinstance(result, dict) else None
        except Exception as e:
            log.error(f"Modification generation failed: {e}")
            return None

    def _validate_syntax(self, files: dict) -> list[str]:
        """AST-parse all Python files to catch syntax errors before applying."""
        errors = []
        for path, content in files.items():
            if not path.endswith(".py"):
                continue
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"{path}: {e}")
        return errors
