"""VS Code skill pack — control VS Code via CLI and file system."""

from tools.base_tool import BaseTool


class VSCodeOpenFileTool(BaseTool):
    name = "vscode_open"
    description = "Open a file or folder in VS Code."
    parameters = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}

    def run(self, path: str) -> str:
        import subprocess
        try:
            subprocess.Popen(["code", path], shell=False)
            return f"Opened in VS Code: {path}"
        except Exception as e:
            return f"Error: {e}"


class VSCodeRunTaskTool(BaseTool):
    name = "vscode_run_task"
    description = "Run a VS Code task (from tasks.json) via the CLI."
    parameters = {"type": "object", "properties": {
        "workspace": {"type": "string"}, "task": {"type": "string"},
    }, "required": ["workspace", "task"]}

    def run(self, workspace: str, task: str) -> str:
        import subprocess
        try:
            result = subprocess.run(
                ["code", "--folder-uri", workspace, "--run-task", task],
                capture_output=True, text=True, timeout=60, shell=False
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error: {e}"


class VSCodeReadTerminalTool(BaseTool):
    name = "vscode_terminal_read"
    description = "Read the VS Code terminal output by checking the most recent log file."
    parameters = {"type": "object", "properties": {"workspace": {"type": "string"}}, "required": ["workspace"]}

    def run(self, workspace: str) -> str:
        from pathlib import Path
        log_dir = Path(workspace) / ".vscode" / "logs"
        if not log_dir.exists():
            return "No VS Code logs found"
        logs = sorted(log_dir.rglob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        if logs:
            return logs[0].read_text(encoding="utf-8", errors="replace")[-2000:]
        return "No log files found"


class VSCodeExtensionTool(BaseTool):
    name = "vscode_install_extension"
    description = "Install a VS Code extension by ID."
    parameters = {"type": "object", "properties": {"extension_id": {"type": "string"}}, "required": ["extension_id"]}

    def run(self, extension_id: str) -> str:
        import subprocess
        try:
            result = subprocess.run(
                ["code", "--install-extension", extension_id],
                capture_output=True, text=True, timeout=60, shell=False
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error: {e}"
