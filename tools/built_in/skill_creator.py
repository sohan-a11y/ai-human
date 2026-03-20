"""
SkillCreator — the LLM creates its own tools at runtime.

Flow:
  1. Agent decides it needs a tool that doesn't exist
  2. Calls skill_creator with a natural language description
  3. LLM generates a BaseTool subclass
  4. Syntax validated via AST
  5. Saved to tools/registry/ (hot-reload directory)
  6. ToolRegistry.hot_reload() called — tool is immediately available
  7. Agent can use the new tool in the same conversation

The agent becomes self-extending — it can build any tool it needs.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from tools.base_tool import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)

_REGISTRY_DIR = Path(__file__).parent.parent / "registry"

_GENERATE_PROMPT = """You are a Python tool generator for an AI agent system.
Generate a complete Python file containing a BaseTool subclass.

Requirements:
- Import BaseTool: `from tools.base_tool import BaseTool`
- Subclass BaseTool with a unique `name`, `description`, and `parameters` (JSON Schema dict)
- Implement `def run(self, **kwargs) -> str:` that executes the tool logic
- Return results as strings
- Handle errors gracefully with try/except
- Use only Python stdlib or common packages (requests, psutil, Pillow, etc.)
- Keep it self-contained in a single file
- Add a docstring at the top explaining what it does
- Do NOT use shell=True in subprocess calls
- The class name should be PascalCase ending with "Tool"

Return ONLY the Python code, no markdown fences, no explanation.

Example:
```
\"\"\"Tool that counts words in a file.\"\"\"
from tools.base_tool import BaseTool

class WordCountTool(BaseTool):
    name = "word_count"
    description = "Count the number of words in a text file."
    parameters = {"type": "object", "properties": {
        "path": {"type": "string", "description": "Path to the text file"},
    }, "required": ["path"]}

    def run(self, path: str) -> str:
        try:
            text = open(path, encoding="utf-8").read()
            count = len(text.split())
            return f"Word count: {count}"
        except Exception as e:
            return f"Error: {e}"
```
"""


class SkillCreatorTool(BaseTool):
    name = "skill_creator"
    description = (
        "Create a new tool/skill at runtime from a natural language description. "
        "The tool will be generated, validated, and immediately available for use. "
        "Use this when you need a capability that no existing tool provides."
    )
    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Short snake_case name for the tool (e.g. 'csv_merger')",
            },
            "description": {
                "type": "string",
                "description": "Detailed description of what the tool should do, its inputs, and expected outputs",
            },
            "examples": {
                "type": "string",
                "description": "Optional usage examples to guide generation",
                "default": "",
            },
        },
        "required": ["tool_name", "description"],
    }

    # Injected by AgentOrchestrator after creation
    _llm = None
    _registry = None

    def run(self, tool_name: str, description: str, examples: str = "") -> str:
        if not self._llm:
            return "Error: SkillCreator not initialized — LLM not attached."

        # Check if tool already exists
        if self._registry and self._registry.get(tool_name):
            return f"Tool '{tool_name}' already exists. Use a different name."

        # Sanitize tool name
        tool_name = re.sub(r"[^a-z0-9_]", "_", tool_name.lower().strip())
        if not tool_name:
            return "Error: Invalid tool name."

        file_name = f"{tool_name}.py"
        file_path = _REGISTRY_DIR / file_name

        if file_path.exists():
            return f"File '{file_name}' already exists in registry. Pick a different name."

        # Generate the tool code via LLM
        try:
            from llm.message_builder import system_message, text_message

            prompt = (
                f"Create a tool with:\n"
                f"- name: \"{tool_name}\"\n"
                f"- Purpose: {description}\n"
            )
            if examples:
                prompt += f"- Usage examples: {examples}\n"

            messages = [
                system_message(_GENERATE_PROMPT),
                text_message("user", prompt),
            ]

            raw_code = self._llm.generate(messages, max_tokens=2048)

            # Strip markdown fences if present
            raw_code = raw_code.strip()
            raw_code = re.sub(r"^```(?:python)?\s*\n?", "", raw_code)
            raw_code = re.sub(r"\n?```\s*$", "", raw_code)
            raw_code = raw_code.strip()

        except Exception as e:
            log.error(f"LLM generation failed: {e}")
            return f"Error generating tool code: {e}"

        # Validate syntax
        try:
            ast.parse(raw_code)
        except SyntaxError as e:
            log.error(f"Generated code has syntax error: {e}")
            return f"Generated code has syntax error: {e}\n\nCode:\n{raw_code[:500]}"

        # Validate it contains a BaseTool subclass
        if "BaseTool" not in raw_code or "def run" not in raw_code:
            return "Generated code does not contain a valid BaseTool subclass."

        # Security checks — block dangerous patterns
        dangerous = ["os.system(", "subprocess.call(", "shell=True", "eval(", "exec(", "__import__"]
        for pattern in dangerous:
            if pattern in raw_code:
                return f"Generated code contains blocked pattern: '{pattern}'. Regenerate with safer approach."

        # Save to registry
        _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        file_path.write_text(raw_code, encoding="utf-8")
        log.info(f"Skill created: {file_path}")

        # Hot-reload the registry
        if self._registry:
            self._registry.hot_reload()
            # Verify it loaded
            loaded = self._registry.get(tool_name)
            if loaded:
                return (
                    f"Tool '{tool_name}' created and loaded successfully!\n"
                    f"Description: {loaded.description}\n"
                    f"File: {file_path}\n"
                    f"You can now use it by calling tool '{tool_name}'."
                )
            else:
                return (
                    f"Tool file saved to {file_path} but failed to load. "
                    f"Check the file for import errors."
                )

        return f"Tool '{tool_name}' saved to {file_path}. Call hot_reload() to activate."


class SkillListTool(BaseTool):
    name = "skill_list_created"
    description = "List all AI-created tools in the registry directory."
    parameters = {"type": "object", "properties": {}}

    def run(self) -> str:
        files = list(_REGISTRY_DIR.glob("*.py"))
        files = [f for f in files if not f.name.startswith("_")]
        if not files:
            return "No AI-created tools yet. Use 'skill_creator' to make one."
        lines = [f"AI-created tools ({len(files)}):"]
        for f in sorted(files):
            lines.append(f"  - {f.stem}")
        return "\n".join(lines)


class SkillDeleteTool(BaseTool):
    name = "skill_delete"
    description = "Delete an AI-created tool from the registry."
    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "description": "Name of the tool to delete"},
        },
        "required": ["tool_name"],
    }

    def run(self, tool_name: str) -> str:
        file_path = _REGISTRY_DIR / f"{tool_name}.py"
        if not file_path.exists():
            return f"Tool '{tool_name}' not found in registry."
        file_path.unlink()
        return f"Tool '{tool_name}' deleted. It will be gone after next hot_reload()."
