"""
WorkflowConverter — when the agent repeats the same sequence 3+ times,
it converts that sequence into a named Python tool automatically.
The tool is saved to tools/registry/ and hot-loaded into ToolRegistry.

This is the self-improvement loop: repetition → automation.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from llm.base import LLMProvider
from llm.message_builder import system_message, text_message
from core.workflow_recorder import Workflow, WorkflowRecorder
from utils.logger import get_logger

log = get_logger(__name__)

_REGISTRY_DIR = Path("tools/registry")

_TOOL_TEMPLATE = '''"""
Auto-generated tool from recorded workflow: {name}
Description: {description}
"""
from tools.base_tool import BaseTool


class {class_name}(BaseTool):
    name = "{tool_name}"
    description = "{description}"
    parameters = {{"type": "object", "properties": {{}}}}

    def run(self, **kwargs) -> str:
        from actions.executor import ActionExecutor
        executor = ActionExecutor()
        results = []
        steps = {steps_json}
        for step in steps:
            result = executor.execute(step["action"], step["args"])
            results.append(f"{{step['action']}}: {{result.message}}")
            if not result.success:
                return f"Failed at step {{step['action']}}: {{result.message}}"
        return "Workflow complete: " + "; ".join(results)
'''

_GENERATE_TOOL_PROMPT = """Convert this recorded workflow into a proper Python tool class.
The tool should be intelligent — use the context of what was done, not just replay steps.
Return ONLY the Python code, no explanation.

Workflow name: {name}
Description: {description}
Steps:
{steps}

Return a complete Python file with a class inheriting BaseTool."""


class WorkflowConverter:

    def __init__(self, llm: LLMProvider, recorder: WorkflowRecorder):
        self._llm = llm
        self._recorder = recorder
        self._action_history: list[tuple[str, dict]] = []
        self._pattern_counts: Counter = Counter()
        _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    def track_action(self, action: str, args: dict) -> None:
        """Call this every time an action executes — tracks patterns."""
        self._action_history.append((action, args))
        # Keep only last 100 actions
        if len(self._action_history) > 100:
            self._action_history = self._action_history[-100:]
        # Cap pattern counter to prevent unbounded growth
        if len(self._pattern_counts) > 500:
            top = self._pattern_counts.most_common(100)
            self._pattern_counts = Counter(dict(top))
        # Look for repeated sequences
        self._detect_patterns()

    def convert_workflow_to_tool(self, workflow: Workflow, use_llm: bool = True) -> str | None:
        """
        Convert a Workflow into a Python tool file in tools/registry/.
        Returns the tool name if successful.
        """
        tool_name = workflow.name.lower().replace(" ", "_").replace("-", "_")
        class_name = "".join(w.capitalize() for w in workflow.name.split())
        if not class_name.endswith("Tool"):
            class_name += "Tool"

        steps_json = json.dumps([
            {"action": s.action, "args": s.args}
            for s in workflow.steps
        ], indent=4)

        if use_llm and len(workflow.steps) > 1:
            code = self._generate_with_llm(workflow)
        else:
            code = _TOOL_TEMPLATE.format(
                name=workflow.name,
                description=workflow.description,
                class_name=class_name,
                tool_name=tool_name,
                steps_json=steps_json,
            )

        if not code:
            return None

        # Validate syntax
        try:
            import ast
            ast.parse(code)
        except SyntaxError as e:
            log.error(f"Generated tool has syntax error: {e}")
            return None

        # Save to registry
        out_path = _REGISTRY_DIR / f"{tool_name}.py"
        out_path.write_text(code, encoding="utf-8")
        log.info(f"Workflow converted to tool: {tool_name} -> {out_path}")
        return tool_name

    def _generate_with_llm(self, workflow: Workflow) -> str:
        steps_text = "\n".join(
            f"  {i+1}. {s.action}({s.args}) -> {s.result[:50]}"
            for i, s in enumerate(workflow.steps)
        )
        messages = [
            system_message("You write Python tool classes. Return only valid Python code."),
            text_message("user", _GENERATE_TOOL_PROMPT.format(
                name=workflow.name,
                description=workflow.description,
                steps=steps_text,
            )),
        ]
        try:
            raw = self._llm.generate(messages)
            raw = raw.strip().removeprefix("```python").removeprefix("```").removesuffix("```").strip()
            return raw
        except Exception as e:
            log.warning(f"LLM tool generation failed: {e}")
            return ""

    def _detect_patterns(self) -> None:
        """Detect repeated action sequences and auto-convert to tools."""
        if len(self._action_history) < 6:
            return
        # Look for sequences of 2-4 actions that appear 3+ times
        for seq_len in (2, 3, 4):
            if len(self._action_history) < seq_len * 3:
                continue
            recent = self._action_history[-30:]
            for i in range(len(recent) - seq_len + 1):
                seq = tuple(a for a, _ in recent[i:i+seq_len])
                key = "|".join(seq)
                self._pattern_counts[key] += 1
                if self._pattern_counts[key] == 3:
                    log.info(f"Repeated pattern detected ({seq_len} steps x3): {seq}")
                    # Start recording this as a workflow
                    wf_name = f"auto_{seq[0]}_{seq[-1]}"
                    steps_data = recent[i:i+seq_len]
                    from core.workflow_recorder import RecordedStep, Workflow
                    import uuid, time
                    wf = Workflow(
                        id=str(uuid.uuid4())[:8],
                        name=wf_name,
                        description=f"Auto-detected: {' → '.join(seq)}",
                        steps=[RecordedStep(action=a, args=args) for a, args in steps_data],
                    )
                    self._recorder._save(wf)
                    self.convert_workflow_to_tool(wf)
