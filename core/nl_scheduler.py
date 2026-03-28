"""
Natural Language Scheduler — parse human time expressions into scheduled tasks.

Examples:
  "every day at 9am"                → daily at 09:00
  "tomorrow at 3pm"                 → once, tomorrow 15:00
  "every Monday at 8:30am"          → weekly, Monday 08:30
  "in 2 hours"                      → once, now + 2h
  "every 30 minutes"                → interval 30min
  "every weekday at 6pm"            → Mon-Fri at 18:00
  "first of every month at noon"    → monthly on day 1 at 12:00
  "next Friday at 2pm"              → once, next Friday 14:00

Requires: dateparser (pip install dateparser)
Falls back to regex-based parsing if dateparser not available.
"""

from __future__ import annotations
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ParsedSchedule:
    raw: str
    type: str           # "once" | "interval" | "daily" | "weekly" | "monthly" | "cron"
    run_at: Optional[datetime] = None
    interval_seconds: Optional[int] = None
    weekday: Optional[int] = None   # 0=Mon, 6=Sun
    day_of_month: Optional[int] = None
    hour: Optional[int] = None
    minute: Optional[int] = None
    weekdays: list[int] = field(default_factory=list)  # for "weekday" schedules
    cron_expr: Optional[str] = None
    confidence: float = 1.0
    error: Optional[str] = None

    def to_cron_expression(self) -> str:
        """Convert to cron expression string."""
        if self.cron_expr:
            return self.cron_expr
        h = self.hour if self.hour is not None else "*"
        m = self.minute if self.minute is not None else "0"
        if self.type == "daily":
            return f"{m} {h} * * *"
        if self.type == "weekly" and self.weekday is not None:
            return f"{m} {h} * * {self.weekday}"
        if self.type == "monthly" and self.day_of_month is not None:
            return f"{m} {h} {self.day_of_month} * *"
        if self.type == "interval" and self.interval_seconds:
            mins = self.interval_seconds // 60
            if mins >= 60:
                return f"0 */{mins // 60} * * *"
            return f"*/{mins} * * * *"
        return "0 * * * *"


# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns for fallback parsing
# ─────────────────────────────────────────────────────────────────────────────

_WEEKDAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2,
    "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

def _parse_time(text: str) -> tuple[int, int] | None:
    """Parse time like '3pm', '9:30am', '14:00', 'noon', 'midnight'."""
    text = text.strip().lower()
    if text == "noon":
        return (12, 0)
    if text == "midnight":
        return (0, 0)
    # 12-hour with am/pm
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
    if m:
        h, mn, period = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if period == "pm" and h != 12:
            h += 12
        elif period == "am" and h == 12:
            h = 0
        return (h, mn)
    # 24-hour
    m = re.match(r"(\d{1,2}):(\d{2})", text)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None


def _next_weekday(weekday: int) -> datetime:
    """Get next occurrence of a weekday (0=Mon)."""
    now = datetime.now()
    days_ahead = weekday - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return now + timedelta(days=days_ahead)


class NLScheduler:
    """Parse natural language time expressions into structured schedules."""

    def parse(self, text: str) -> ParsedSchedule:
        """Parse a natural language schedule expression."""
        text_lower = text.lower().strip()

        # Try dateparser first (more powerful)
        result = self._try_dateparser(text, text_lower)
        if result:
            return result

        # Fallback: regex-based parsing
        return self._regex_parse(text, text_lower)

    def _try_dateparser(self, original: str, text_lower: str) -> ParsedSchedule | None:
        try:
            import dateparser
        except ImportError:
            return None

        try:
            # Check for recurring patterns first (dateparser is for one-time)
            if any(kw in text_lower for kw in ["every", "each", "daily", "weekly", "monthly", "hourly"]):
                return None  # handle with regex

            parsed_dt = dateparser.parse(
                original,
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                }
            )
            if parsed_dt:
                return ParsedSchedule(
                    raw=original,
                    type="once",
                    run_at=parsed_dt,
                    hour=parsed_dt.hour,
                    minute=parsed_dt.minute,
                    confidence=0.9,
                )
        except Exception:
            pass
        return None

    def _regex_parse(self, original: str, text: str) -> ParsedSchedule:
        # ── INTERVAL ──────────────────────────────────────────────────────
        # "every 30 minutes", "every 2 hours", "every 5 seconds"
        m = re.search(r"every\s+(\d+)\s+(second|minute|hour|day)s?", text)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            mult = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}[unit]
            return ParsedSchedule(
                raw=original, type="interval",
                interval_seconds=n * mult, confidence=0.95
            )

        # "every hour", "hourly"
        if re.search(r"\bevery hour\b|\bhourly\b", text):
            return ParsedSchedule(raw=original, type="interval", interval_seconds=3600)

        # ── WEEKDAY SCHEDULE ──────────────────────────────────────────────
        # "every Monday at 9am", "each Tuesday at 3:30pm", "every Friday at noon"
        for day_name, day_num in _WEEKDAY_MAP.items():
            if re.search(rf"\b{day_name}\b", text):
                time_part = re.search(r"at\s+([\d:apmnoighdt\s]+(?:am|pm)?)", text)
                h, mn = (9, 0)
                if time_part:
                    parsed = _parse_time(time_part.group(1))
                    if parsed:
                        h, mn = parsed
                return ParsedSchedule(
                    raw=original, type="weekly",
                    weekday=day_num, hour=h, minute=mn, confidence=0.9
                )

        # "every weekday at 6pm" (Mon-Fri)
        if re.search(r"\bweekday\b", text):
            time_part = re.search(r"at\s+([\d:apmnoighdt\s]+(?:am|pm)?)", text)
            h, mn = (9, 0)
            if time_part:
                parsed = _parse_time(time_part.group(1))
                if parsed:
                    h, mn = parsed
            return ParsedSchedule(
                raw=original, type="weekly",
                weekdays=[0, 1, 2, 3, 4], hour=h, minute=mn,
                cron_expr=f"{mn} {h} * * 1-5", confidence=0.9
            )

        # ── DAILY ─────────────────────────────────────────────────────────
        # "every day at 9am", "daily at noon"
        if re.search(r"\bevery day\b|\bdaily\b", text):
            time_part = re.search(r"at\s+([\d:apmnoighdt\s]+)", text)
            h, mn = (9, 0)
            if time_part:
                parsed = _parse_time(time_part.group(1).strip())
                if parsed:
                    h, mn = parsed
            return ParsedSchedule(
                raw=original, type="daily", hour=h, minute=mn, confidence=0.95
            )

        # ── MONTHLY ───────────────────────────────────────────────────────
        # "first of every month at noon", "1st of month at 8am"
        m = re.search(r"(\d+)(?:st|nd|rd|th)?\s+of\s+(?:every\s+)?month", text)
        if m or re.search(r"\bmonthly\b", text):
            day_num = int(m.group(1)) if m else 1
            time_part = re.search(r"at\s+([\d:apmnoighdt\s]+)", text)
            h, mn = (9, 0)
            if time_part:
                parsed = _parse_time(time_part.group(1).strip())
                if parsed:
                    h, mn = parsed
            return ParsedSchedule(
                raw=original, type="monthly",
                day_of_month=day_num, hour=h, minute=mn, confidence=0.9
            )

        # ── ONCE — RELATIVE ───────────────────────────────────────────────
        # "in 2 hours", "in 30 minutes", "in 1 hour 30 minutes"
        m = re.search(r"in\s+(\d+)\s+(second|minute|hour|day)s?", text)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            delta = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}[unit]
            run_at = datetime.now() + timedelta(seconds=n * delta)
            return ParsedSchedule(
                raw=original, type="once", run_at=run_at,
                hour=run_at.hour, minute=run_at.minute, confidence=0.9
            )

        # "tomorrow at 3pm"
        if "tomorrow" in text:
            time_part = re.search(r"at\s+([\d:apmnoighdt\s]+)", text)
            h, mn = (9, 0)
            if time_part:
                parsed = _parse_time(time_part.group(1).strip())
                if parsed:
                    h, mn = parsed
            run_at = datetime.now().replace(hour=h, minute=mn, second=0, microsecond=0) + timedelta(days=1)
            return ParsedSchedule(
                raw=original, type="once", run_at=run_at,
                hour=h, minute=mn, confidence=0.9
            )

        # "next Friday at 2pm"
        m = re.search(r"next\s+(\w+)", text)
        if m and m.group(1).lower() in _WEEKDAY_MAP:
            day_num = _WEEKDAY_MAP[m.group(1).lower()]
            time_part = re.search(r"at\s+([\d:apmnoighdt\s]+)", text)
            h, mn = (9, 0)
            if time_part:
                parsed = _parse_time(time_part.group(1).strip())
                if parsed:
                    h, mn = parsed
            base = _next_weekday(day_num)
            run_at = base.replace(hour=h, minute=mn, second=0, microsecond=0)
            return ParsedSchedule(
                raw=original, type="once", run_at=run_at,
                hour=h, minute=mn, confidence=0.85
            )

        # ── CRON EXPRESSION ───────────────────────────────────────────────
        # "0 9 * * 1-5" — pass through directly
        if re.match(r"^[\d\*/,\-]+ [\d\*/,\-]+ [\d\*/,\-]+ [\d\*/,\-]+ [\d\*/,\-]+$", text.strip()):
            return ParsedSchedule(
                raw=original, type="cron", cron_expr=text.strip(), confidence=1.0
            )

        # Fallback
        return ParsedSchedule(
            raw=original, type="once",
            error=f"Could not parse schedule expression: '{original}'. "
                  "Try: 'every day at 9am', 'in 2 hours', 'every Monday at 3pm'",
            confidence=0.0
        )

    def describe(self, schedule: ParsedSchedule) -> str:
        """Return human-readable description of a parsed schedule."""
        if schedule.error:
            return f"Parse error: {schedule.error}"
        if schedule.type == "once":
            if schedule.run_at:
                return f"Once at {schedule.run_at.strftime('%Y-%m-%d %H:%M')}"
            return "Once (time unclear)"
        if schedule.type == "interval":
            secs = schedule.interval_seconds or 0
            if secs >= 3600:
                return f"Every {secs // 3600} hour(s)"
            if secs >= 60:
                return f"Every {secs // 60} minute(s)"
            return f"Every {secs} second(s)"
        if schedule.type == "daily":
            return f"Every day at {schedule.hour:02d}:{schedule.minute:02d}"
        if schedule.type == "weekly":
            if schedule.weekdays:
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_names = ", ".join(days[d] for d in schedule.weekdays)
                return f"Every {day_names} at {schedule.hour:02d}:{schedule.minute:02d}"
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_name = days[schedule.weekday] if schedule.weekday is not None else "?"
            return f"Every {day_name} at {schedule.hour:02d}:{schedule.minute:02d}"
        if schedule.type == "monthly":
            return f"Monthly on day {schedule.day_of_month} at {schedule.hour:02d}:{schedule.minute:02d}"
        if schedule.type == "cron":
            return f"Cron: {schedule.cron_expr}"
        return "Unknown schedule"
