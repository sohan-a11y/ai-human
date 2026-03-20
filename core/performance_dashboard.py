"""
Performance Dashboard — tracks and reports on AI Human's performance metrics.

Metrics tracked:
  - Tasks completed / failed / in-progress
  - Success rate over time
  - Average task duration
  - Tool usage frequency
  - Memory (ChromaDB) growth
  - CPU/RAM usage during tasks
  - Self-correction events
  - Knowledge items learned
  - Goals achieved per day

Data stored in: data/metrics.jsonl (append-only event log)
Reports generated as Markdown or returned as dict.
"""

from __future__ import annotations
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional


_METRICS_FILE = Path("data/metrics.jsonl")


@dataclass
class TaskEvent:
    event_type: str      # "task_start" | "task_complete" | "task_fail" | "correction" | "learned"
    timestamp: float
    task_id: str
    goal: str = ""
    duration_seconds: float = 0.0
    tool_used: str = ""
    error: str = ""
    correction_attempt: int = 0
    knowledge_type: str = ""
    cpu_percent: float = 0.0
    ram_mb: float = 0.0


class PerformanceDashboard:
    """Track and report on agent performance metrics."""

    def __init__(self, metrics_file: str = "data/metrics.jsonl"):
        self._file = Path(metrics_file)
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._active_tasks: dict[str, float] = {}  # task_id -> start_time

    # ── Event Recording ────────────────────────────────────────────────────────

    def record_task_start(self, task_id: str, goal: str) -> None:
        self._active_tasks[task_id] = time.time()
        self._write_event(TaskEvent(
            event_type="task_start",
            timestamp=time.time(),
            task_id=task_id,
            goal=goal[:200],
        ))

    def record_task_complete(self, task_id: str, goal: str = "") -> None:
        duration = time.time() - self._active_tasks.pop(task_id, time.time())
        cpu, ram = self._get_system_stats()
        self._write_event(TaskEvent(
            event_type="task_complete",
            timestamp=time.time(),
            task_id=task_id,
            goal=goal[:200],
            duration_seconds=round(duration, 2),
            cpu_percent=cpu,
            ram_mb=ram,
        ))

    def record_task_fail(self, task_id: str, goal: str = "", error: str = "") -> None:
        duration = time.time() - self._active_tasks.pop(task_id, time.time())
        self._write_event(TaskEvent(
            event_type="task_fail",
            timestamp=time.time(),
            task_id=task_id,
            goal=goal[:200],
            duration_seconds=round(duration, 2),
            error=error[:300],
        ))

    def record_tool_use(self, tool_name: str, task_id: str = "") -> None:
        self._write_event(TaskEvent(
            event_type="tool_use",
            timestamp=time.time(),
            task_id=task_id,
            tool_used=tool_name,
        ))

    def record_correction(self, task_id: str, attempt: int, goal: str = "") -> None:
        self._write_event(TaskEvent(
            event_type="correction",
            timestamp=time.time(),
            task_id=task_id,
            goal=goal[:200],
            correction_attempt=attempt,
        ))

    def record_learned(self, knowledge_type: str, summary: str = "") -> None:
        self._write_event(TaskEvent(
            event_type="learned",
            timestamp=time.time(),
            task_id="",
            goal=summary[:200],
            knowledge_type=knowledge_type,
        ))

    # ── Reports ────────────────────────────────────────────────────────────────

    def get_summary(self, days: int = 7) -> dict:
        """Return a summary dict covering the last N days."""
        since = time.time() - days * 86400
        events = self._load_events(since=since)

        completed = [e for e in events if e["event_type"] == "task_complete"]
        failed = [e for e in events if e["event_type"] == "task_fail"]
        corrections = [e for e in events if e["event_type"] == "correction"]
        learned = [e for e in events if e["event_type"] == "learned"]
        tool_uses = [e for e in events if e["event_type"] == "tool_use"]

        total_tasks = len(completed) + len(failed)
        success_rate = (len(completed) / total_tasks * 100) if total_tasks > 0 else 0

        durations = [e.get("duration_seconds", 0) for e in completed if e.get("duration_seconds")]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Tool frequency
        tool_freq: dict[str, int] = defaultdict(int)
        for e in tool_uses:
            tool_freq[e.get("tool_used", "unknown")] += 1

        # Daily breakdown
        daily: dict[str, dict] = {}
        for e in completed + failed:
            day = datetime.fromtimestamp(e["timestamp"]).strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"completed": 0, "failed": 0}
            if e["event_type"] == "task_complete":
                daily[day]["completed"] += 1
            else:
                daily[day]["failed"] += 1

        return {
            "period_days": days,
            "tasks_completed": len(completed),
            "tasks_failed": len(failed),
            "success_rate_percent": round(success_rate, 1),
            "avg_task_duration_seconds": round(avg_duration, 1),
            "self_corrections": len(corrections),
            "knowledge_items_learned": len(learned),
            "total_tool_uses": len(tool_uses),
            "top_tools": sorted(tool_freq.items(), key=lambda x: x[1], reverse=True)[:10],
            "daily_breakdown": daily,
        }

    def generate_report(self, days: int = 7) -> str:
        """Generate a Markdown performance report."""
        summary = self.get_summary(days)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# AI Human Performance Dashboard",
            f"\n**Generated:** {now}  **Period:** Last {days} days\n",
            "---\n",
            "## Key Metrics\n",
            "| Metric | Value |",
            "|---|---|",
            f"| Tasks Completed | **{summary['tasks_completed']}** |",
            f"| Tasks Failed | {summary['tasks_failed']} |",
            f"| Success Rate | **{summary['success_rate_percent']}%** |",
            f"| Avg Task Duration | {summary['avg_task_duration_seconds']}s |",
            f"| Self-Corrections | {summary['self_corrections']} |",
            f"| Knowledge Items Learned | {summary['knowledge_items_learned']} |",
            f"| Total Tool Uses | {summary['total_tool_uses']} |",
            "",
        ]

        if summary["top_tools"]:
            lines.append("## Top Tools Used\n")
            lines.append("| Tool | Uses |")
            lines.append("|---|---|")
            for tool, count in summary["top_tools"]:
                lines.append(f"| `{tool}` | {count} |")
            lines.append("")

        if summary["daily_breakdown"]:
            lines.append("## Daily Breakdown\n")
            lines.append("| Date | Completed | Failed |")
            lines.append("|---|---|---|")
            for day in sorted(summary["daily_breakdown"].keys(), reverse=True):
                d = summary["daily_breakdown"][day]
                lines.append(f"| {day} | {d['completed']} | {d['failed']} |")
            lines.append("")

        # Growth trend
        all_events = self._load_events()
        if all_events:
            first_event_ts = all_events[0]["timestamp"]
            days_running = (time.time() - first_event_ts) / 86400
            all_completed = [e for e in all_events if e["event_type"] == "task_complete"]
            lines.append("## All-Time Stats\n")
            lines.append(f"- Running for: **{days_running:.1f} days**")
            lines.append(f"- Total tasks completed ever: **{len(all_completed)}**")
            lines.append(f"- Total knowledge items: **{len([e for e in all_events if e['event_type'] == 'learned'])}**")
            lines.append("")

        lines.append("---")
        lines.append("*Performance data stored in data/metrics.jsonl*")
        return "\n".join(lines)

    def save_report(self, output_path: str = "data/performance_report.md", days: int = 7) -> str:
        report = self.generate_report(days=days)
        Path(output_path).write_text(report, encoding="utf-8")
        return output_path

    # ── Internal ───────────────────────────────────────────────────────────────

    def _write_event(self, event: TaskEvent) -> None:
        with open(self._file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def _load_events(self, since: float = 0.0) -> list[dict]:
        if not self._file.exists():
            return []
        events = []
        try:
            with open(self._file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                        if e.get("timestamp", 0) >= since:
                            events.append(e)
                    except Exception:
                        pass
        except Exception:
            pass
        return events

    def _get_system_stats(self) -> tuple[float, float]:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().used / 1024 / 1024
            return cpu, ram
        except ImportError:
            return 0.0, 0.0
