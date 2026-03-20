"""
ToolRegistry — discovers, loads, and indexes all tools.
Built-in tools load from tools/built_in/
Skill packs load from skills/
AI-created tools load from tools/registry/
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
from pathlib import Path

from tools.base_tool import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)

_ROOT = Path(__file__).parent.parent


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._tool_sources: dict[str, str] = {}  # tool_name → source file
        self._load_built_in()
        self._load_skills()
        self._load_user_created()

    def _load_built_in(self) -> None:
        built_in_dir = Path(__file__).parent / "built_in"
        for py_file in built_in_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            self._load_file(py_file)

    def _load_skills(self) -> None:
        """Load all skill packs from the skills/ directory."""
        skills_dir = _ROOT / "skills"
        if not skills_dir.exists():
            return
        for py_file in skills_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            self._load_file(py_file)

    def _load_user_created(self) -> None:
        registry_dir = Path(__file__).parent / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        for py_file in registry_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            self._load_file(py_file)

    def _load_file(self, path: Path) -> None:
        # Use parent dir name as namespace prefix to prevent module collisions
        module_name = f"_aitool_{path.parent.name}_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool and obj.name:
                    instance = obj()
                    # Warn on name collision (user-created tools override silently)
                    if instance.name in self._tools:
                        prev_source = self._tool_sources.get(instance.name, "unknown")
                        log.info(f"Tool '{instance.name}' from {path.name} overrides {prev_source}")
                    self._tools[instance.name] = instance
                    self._tool_sources[instance.name] = str(path.name)
                    log.debug(f"Loaded tool: {instance.name} ({path.name})")
        except Exception as e:
            log.warning(f"Failed to load tool from {path}: {e}")

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def tool_count(self) -> int:
        return len(self._tools)

    def describe_all(self) -> str:
        """Returns a formatted list of available tools for the LLM system prompt."""
        lines = [f"Available tools ({len(self._tools)}):"]
        for tool in self._tools.values():
            lines.append(f"  - {tool.name}: {tool.description}")
        return "\n".join(lines)

    def run(self, name: str, **kwargs) -> str:
        tool = self.get(name)
        if tool is None:
            return f"Tool '{name}' not found."
        try:
            return tool.run(**kwargs)
        except Exception as e:
            return f"Tool '{name}' error: {e}"

    def hot_reload(self) -> None:
        """Re-scan and load any newly added tool files and skills."""
        self._load_skills()
        self._load_user_created()
