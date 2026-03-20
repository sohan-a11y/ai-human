"""Windows Task Scheduler skill pack — create, list, delete scheduled tasks."""

import subprocess
from tools.base_tool import BaseTool


class ScheduledTaskListTool(BaseTool):
    name = "win_task_list"
    description = "List Windows Task Scheduler tasks. Can filter by name or folder."
    parameters = {"type": "object", "properties": {
        "folder": {"type": "string", "default": "\\", "description": "Task folder path (default: root)"},
        "filter_name": {"type": "string", "default": "", "description": "Filter by task name"},
    }, "required": []}

    def run(self, folder: str = "\\", filter_name: str = "") -> str:
        try:
            cmd = ["schtasks", "/Query", "/FO", "TABLE", "/NH"]
            if folder != "\\":
                cmd.extend(["/TN", folder])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            output = result.stdout.strip()
            if filter_name:
                lines = [l for l in output.split("\n") if filter_name.lower() in l.lower()]
                return "\n".join(lines) if lines else f"No tasks matching '{filter_name}'"
            return output[:5000] if output else "No scheduled tasks found."
        except Exception as e:
            return f"Error: {e}"


class ScheduledTaskCreateTool(BaseTool):
    name = "win_task_create"
    description = "Create a Windows scheduled task to run a program on a schedule."
    parameters = {"type": "object", "properties": {
        "name": {"type": "string", "description": "Task name (e.g. MyBackup)"},
        "command": {"type": "string", "description": "Program/script to run"},
        "schedule_type": {"type": "string", "enum": ["DAILY", "WEEKLY", "MONTHLY", "ONCE", "ONSTART", "ONLOGON"],
                         "description": "When to run"},
        "start_time": {"type": "string", "default": "09:00", "description": "Start time (HH:MM)"},
        "start_date": {"type": "string", "default": "", "description": "Start date (MM/DD/YYYY) for ONCE"},
        "days": {"type": "string", "default": "", "description": "Days for WEEKLY (MON,TUE,WED...)"},
        "interval": {"type": "integer", "default": 1, "description": "Interval (every N days/weeks/months)"},
    }, "required": ["name", "command", "schedule_type"]}

    def run(self, name: str, command: str, schedule_type: str,
            start_time: str = "09:00", start_date: str = "",
            days: str = "", interval: int = 1) -> str:
        try:
            cmd = [
                "schtasks", "/Create", "/F",
                "/TN", name,
                "/TR", command,
                "/SC", schedule_type,
                "/ST", start_time,
            ]
            if schedule_type == "ONCE" and start_date:
                cmd.extend(["/SD", start_date])
            if schedule_type == "WEEKLY" and days:
                cmd.extend(["/D", days])
            if interval > 1:
                cmd.extend(["/MO", str(interval)])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            output = (result.stdout + result.stderr).strip()
            return output if output else "Task created successfully."
        except Exception as e:
            return f"Error: {e}"


class ScheduledTaskDeleteTool(BaseTool):
    name = "win_task_delete"
    description = "Delete a Windows scheduled task by name."
    parameters = {"type": "object", "properties": {
        "name": {"type": "string", "description": "Task name to delete"},
    }, "required": ["name"]}

    def run(self, name: str) -> str:
        try:
            result = subprocess.run(
                ["schtasks", "/Delete", "/TN", name, "/F"],
                capture_output=True, text=True, timeout=15
            )
            output = (result.stdout + result.stderr).strip()
            return output if output else f"Task '{name}' deleted."
        except Exception as e:
            return f"Error: {e}"


class ScheduledTaskRunTool(BaseTool):
    name = "win_task_run"
    description = "Manually run a Windows scheduled task immediately."
    parameters = {"type": "object", "properties": {
        "name": {"type": "string", "description": "Task name to run"},
    }, "required": ["name"]}

    def run(self, name: str) -> str:
        try:
            result = subprocess.run(
                ["schtasks", "/Run", "/TN", name],
                capture_output=True, text=True, timeout=15
            )
            output = (result.stdout + result.stderr).strip()
            return output if output else f"Task '{name}' started."
        except Exception as e:
            return f"Error: {e}"


class ScheduledTaskInfoTool(BaseTool):
    name = "win_task_info"
    description = "Get detailed info about a Windows scheduled task."
    parameters = {"type": "object", "properties": {
        "name": {"type": "string"},
    }, "required": ["name"]}

    def run(self, name: str) -> str:
        try:
            result = subprocess.run(
                ["schtasks", "/Query", "/TN", name, "/V", "/FO", "LIST"],
                capture_output=True, text=True, timeout=15
            )
            return result.stdout[:3000] if result.stdout else result.stderr
        except Exception as e:
            return f"Error: {e}"
