"""PowerShell / CMD skill pack — run scripts, manage services, system commands."""

import subprocess
from tools.base_tool import BaseTool


class PowerShellRunTool(BaseTool):
    name = "powershell_run"
    description = "Execute a PowerShell command and return output. Use for system administration tasks."
    parameters = {"type": "object", "properties": {
        "command": {"type": "string", "description": "PowerShell command to execute"},
        "timeout": {"type": "integer", "default": 30, "description": "Timeout in seconds"},
    }, "required": ["command"]}

    def run(self, command: str, timeout: int = 30) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout.strip()
            if result.stderr.strip():
                output += f"\nSTDERR: {result.stderr.strip()}"
            return output[:5000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"


class PowerShellScriptTool(BaseTool):
    name = "powershell_script"
    description = "Execute a multi-line PowerShell script from a file or inline."
    parameters = {"type": "object", "properties": {
        "script": {"type": "string", "description": "Multi-line PowerShell script content"},
        "timeout": {"type": "integer", "default": 60},
    }, "required": ["script"]}

    def run(self, script: str, timeout: int = 60) -> str:
        import tempfile
        from pathlib import Path
        try:
            tmp = Path(tempfile.mktemp(suffix=".ps1"))
            tmp.write_text(script, encoding="utf-8")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(tmp)],
                capture_output=True, text=True, timeout=timeout
            )
            tmp.unlink(missing_ok=True)
            output = result.stdout.strip()
            if result.stderr.strip():
                output += f"\nSTDERR: {result.stderr.strip()}"
            return output[:5000] if output else "(no output)"
        except Exception as e:
            return f"Error: {e}"


class ServiceManagerTool(BaseTool):
    name = "service_manager"
    description = "List, start, stop, or restart Windows services."
    parameters = {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["list", "status", "start", "stop", "restart"],
                   "description": "Action to perform"},
        "service_name": {"type": "string", "default": "", "description": "Service name (required for start/stop/restart/status)"},
    }, "required": ["action"]}

    def _sanitize_name(self, name: str) -> str:
        """Sanitize service name to prevent PowerShell injection."""
        import re
        # Allow only alphanumeric, hyphens, underscores, dots, spaces
        return re.sub(r"[^a-zA-Z0-9\-_. ]", "", name)

    def run(self, action: str, service_name: str = "") -> str:
        try:
            if action == "list":
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-Service | Select-Object Status, Name, DisplayName | Format-Table -AutoSize | Out-String -Width 200"],
                    capture_output=True, text=True, timeout=15
                )
                return r.stdout[:5000]
            if not service_name:
                return "Service name required for this action."
            safe_name = self._sanitize_name(service_name)
            if not safe_name:
                return "Invalid service name."
            cmd_map = {
                "status": f"Get-Service '{safe_name}' | Format-List *",
                "start": f"Start-Service '{safe_name}' -PassThru",
                "stop": f"Stop-Service '{safe_name}' -PassThru",
                "restart": f"Restart-Service '{safe_name}' -PassThru",
            }
            cmd = cmd_map.get(action, "")
            if not cmd:
                return f"Unknown action: {action}"
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=15
            )
            return (r.stdout + r.stderr).strip()[:3000]
        except Exception as e:
            return f"Error: {e}"


class EnvironmentVariableTool(BaseTool):
    name = "env_var"
    description = "Get or set environment variables."
    parameters = {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["get", "set", "list"]},
        "name": {"type": "string", "default": ""},
        "value": {"type": "string", "default": ""},
        "scope": {"type": "string", "enum": ["process", "user", "machine"], "default": "process"},
    }, "required": ["action"]}

    def run(self, action: str, name: str = "", value: str = "", scope: str = "process") -> str:
        import os
        import re
        try:
            if action == "list":
                items = sorted(os.environ.items())
                return "\n".join(f"{k}={v[:100]}" for k, v in items[:50])
            if action == "get":
                return os.environ.get(name, f"'{name}' not set")
            if action == "set":
                if scope == "process":
                    os.environ[name] = value
                    return f"Set {name} in current process"
                # Sanitize name and value to prevent PowerShell injection
                safe_name = re.sub(r"[^a-zA-Z0-9_]", "", name)
                safe_value = value.replace("'", "''")  # Escape single quotes for PS
                if not safe_name:
                    return "Invalid environment variable name."
                cmd = f"[Environment]::SetEnvironmentVariable('{safe_name}', '{safe_value}', '{scope.capitalize()}')"
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True, text=True, timeout=10
                )
                return f"Set {safe_name} at {scope} level. {r.stderr}" if r.stderr else f"Set {safe_name} at {scope} level."
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {e}"
