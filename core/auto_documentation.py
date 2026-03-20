"""
Auto-Documentation Loop — the AI Human continuously logs what it learns,
what tools it uses, what goals it achieves, and generates:

1. A living AGENT_LOG.md — chronological log of all agent activity
2. A KNOWLEDGE_BASE.md — structured documentation of learned facts
3. A TOOL_GUIDE.md — auto-generated guide of all available tools
4. Per-session session logs in data/session_logs/

This runs as a background thread and flushes every 60 seconds.
"""

from __future__ import annotations
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class LogEntry:
    timestamp: str
    entry_type: str   # "goal" | "action" | "result" | "learned" | "error" | "tool"
    content: str
    metadata: dict


class AutoDocumentation:
    """Continuously document agent activity and knowledge."""

    def __init__(
        self,
        docs_dir: str = "docs",
        logs_dir: str = "data/session_logs",
        flush_interval: int = 60,
    ):
        self._docs_dir = Path(docs_dir)
        self._logs_dir = Path(logs_dir)
        self._flush_interval = flush_interval
        self._docs_dir.mkdir(parents=True, exist_ok=True)
        self._logs_dir.mkdir(parents=True, exist_ok=True)

        self._buffer: deque[LogEntry] = deque(maxlen=10000)
        self._knowledge: dict[str, list[str]] = {}  # category -> list of facts
        self._session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start background documentation thread."""
        self._running = True
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self.flush()  # Final flush

    # ── Log recording ──────────────────────────────────────────────────────────

    def log_goal(self, goal: str, goal_id: str = "") -> None:
        self._add_entry("goal", f"**GOAL**: {goal}", {"goal_id": goal_id})

    def log_action(self, tool: str, args: dict, result: str) -> None:
        snippet = result[:200] + "..." if len(result) > 200 else result
        self._add_entry(
            "action",
            f"**TOOL**: `{tool}` → {snippet}",
            {"tool": tool, "args": str(args)[:200]},
        )

    def log_result(self, goal: str, success: bool, summary: str) -> None:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self._add_entry("result", f"{status}: {goal[:100]}\n  {summary[:300]}", {"success": success})

    def log_learned(self, fact: str, category: str = "general") -> None:
        self._add_entry("learned", f"**LEARNED** [{category}]: {fact}", {"category": category})
        with self._lock:
            if category not in self._knowledge:
                self._knowledge[category] = []
            if fact not in self._knowledge[category]:
                self._knowledge[category].append(fact)

    def log_error(self, error: str, context: str = "") -> None:
        self._add_entry("error", f"**ERROR**: {error[:300]}\n  Context: {context[:200]}", {})

    def log_tool_discovered(self, tool_name: str, description: str) -> None:
        self._add_entry("tool", f"**TOOL REGISTERED**: `{tool_name}` — {description[:200]}", {})

    # ── Flush to disk ──────────────────────────────────────────────────────────

    def flush(self) -> None:
        """Write buffered entries to log files."""
        with self._lock:
            entries = list(self._buffer)
            self._buffer.clear()
            knowledge_snapshot = dict(self._knowledge)

        if entries:
            self._append_agent_log(entries)
            self._append_session_log(entries)
        if knowledge_snapshot:
            self._write_knowledge_base(knowledge_snapshot)

    def generate_tool_guide(self, tools: list) -> None:
        """Auto-generate TOOL_GUIDE.md from registered tools."""
        lines = [
            "# AI Human Tool Guide",
            f"\n*Auto-generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
            f"**Total tools:** {len(tools)}\n",
            "---\n",
        ]
        # Group by module
        by_module: dict[str, list] = {}
        for tool in tools:
            module = getattr(tool, "__module__", "other") or "other"
            module_short = module.split(".")[-2] if "." in module else module
            if module_short not in by_module:
                by_module[module_short] = []
            by_module[module_short].append(tool)

        for module_name in sorted(by_module.keys()):
            lines.append(f"## {module_name.replace('_', ' ').title()}\n")
            for tool in by_module[module_name]:
                name = getattr(tool, "name", str(tool))
                desc = getattr(tool, "description", "")
                params = getattr(tool, "parameters", {})
                props = params.get("properties", {}) if isinstance(params, dict) else {}
                lines.append(f"### `{name}`\n")
                lines.append(f"{desc}\n")
                if props:
                    lines.append("**Parameters:**")
                    for param_name, param_info in props.items():
                        ptype = param_info.get("type", "any") if isinstance(param_info, dict) else "any"
                        pdesc = param_info.get("description", "") if isinstance(param_info, dict) else ""
                        lines.append(f"- `{param_name}` ({ptype}){': ' + pdesc if pdesc else ''}")
                    lines.append("")

        tool_guide_path = self._docs_dir / "TOOL_GUIDE.md"
        tool_guide_path.write_text("\n".join(lines), encoding="utf-8")

    # ── Internal ───────────────────────────────────────────────────────────────

    def _add_entry(self, entry_type: str, content: str, metadata: dict) -> None:
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            entry_type=entry_type,
            content=content,
            metadata=metadata,
        )
        with self._lock:
            self._buffer.append(entry)

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(self._flush_interval)
            try:
                self.flush()
            except Exception:
                pass

    def _append_agent_log(self, entries: list[LogEntry]) -> None:
        log_path = self._docs_dir / "AGENT_LOG.md"
        lines = []
        if not log_path.exists():
            lines.append("# AI Human Agent Log\n\nChronological record of all agent activity.\n\n---\n")

        for entry in entries:
            dt = entry.timestamp[:19].replace("T", " ")
            lines.append(f"\n**[{dt}]** {entry.content}")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _append_session_log(self, entries: list[LogEntry]) -> None:
        log_path = self._logs_dir / f"{self._session_id}.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(asdict(entry)) + "\n")

    def _write_knowledge_base(self, knowledge: dict[str, list[str]]) -> None:
        kb_path = self._docs_dir / "KNOWLEDGE_BASE.md"
        lines = [
            "# AI Human Knowledge Base",
            f"\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
            f"**Total facts:** {sum(len(v) for v in knowledge.values())}\n",
            "---\n",
        ]
        for category in sorted(knowledge.keys()):
            facts = knowledge[category]
            lines.append(f"## {category.replace('_', ' ').title()}\n")
            for fact in facts[-50:]:  # last 50 facts per category
                lines.append(f"- {fact}")
            lines.append("")

        kb_path.write_text("\n".join(lines), encoding="utf-8")

    def get_recent_log(self, n: int = 50) -> str:
        """Return last N log entries as formatted text."""
        with self._lock:
            recent = list(self._buffer)[-n:]
        lines = []
        for entry in recent:
            dt = entry.timestamp[:19].replace("T", " ")
            lines.append(f"[{dt}] {entry.content}")
        return "\n".join(lines) if lines else "No recent activity"

    def summarize_session(self) -> str:
        """Generate a summary of the current session."""
        with self._lock:
            all_entries = list(self._buffer)

        goals = [e for e in all_entries if e.entry_type == "goal"]
        results = [e for e in all_entries if e.entry_type == "result"]
        learned = [e for e in all_entries if e.entry_type == "learned"]
        errors = [e for e in all_entries if e.entry_type == "error"]
        successes = [e for e in results if e.metadata.get("success")]

        lines = [
            f"Session: {self._session_id}",
            f"Goals attempted: {len(goals)}",
            f"Results recorded: {len(results)} ({len(successes)} succeeded)",
            f"Facts learned: {len(learned)}",
            f"Errors encountered: {len(errors)}",
        ]
        if learned:
            lines.append(f"Recent learnings: {', '.join(e.content[:50] for e in learned[-3:])}")
        return "\n".join(lines)
