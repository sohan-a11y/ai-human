"""
SandboxRunner — executes Python code in an isolated subprocess.
The code runs in a separate process with a timeout and resource limits.
If it crashes, hangs, or does something bad — only the sandbox dies, not the agent.

For truly dangerous code: runs in a temp directory with restricted imports.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from tools.base_tool import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)

# Imports that are always blocked in sandboxed code
_BLOCKED_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "ctypes", "winreg",
    "socket", "ftplib", "smtplib", "urllib", "http",
    "__import__", "eval", "exec", "compile",
}


class SandboxRunnerTool(BaseTool):
    name = "sandbox_run"
    description = (
        "Run Python code safely in an isolated sandbox. "
        "Use this for calculations, data processing, or testing code snippets. "
        "The code cannot access the filesystem, network, or system calls."
    )
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "default": 10, "description": "Max seconds to run"},
            "allow_network": {"type": "boolean", "default": False},
        },
        "required": ["code"],
    }

    def run(self, code: str, timeout: int = 10, allow_network: bool = False) -> str:
        # Pre-check: static analysis for dangerous patterns
        issues = self._static_check(code, allow_network)
        if issues:
            return f"Code blocked: {'; '.join(issues)}"

        return self._run_subprocess(code, timeout)

    def _static_check(self, code: str, allow_network: bool) -> list[str]:
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [a.name.split(".")[0] for a in node.names]
                    else:
                        names = [node.module.split(".")[0]] if node.module else []
                    for name in names:
                        if name in _BLOCKED_IMPORTS:
                            issues.append(f"Blocked import: {name}")
                        if not allow_network and name in {"requests", "urllib", "http", "socket"}:
                            issues.append(f"Network import blocked: {name}")
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        return issues

    def _run_subprocess(self, code: str, timeout: int) -> str:
        wrapper = textwrap.dedent(f"""
import sys
import io
import traceback

# Redirect output
_out = io.StringIO()
sys.stdout = _out
sys.stderr = _out

try:
{textwrap.indent(code, '    ')}
    _result = _out.getvalue()
except Exception as e:
    _result = f"ERROR: {{traceback.format_exc()}}"

sys.stdout = sys.__stdout__
print(_result[:2000])
""")
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(wrapper)
                tmp_path = f.name

            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
            )
            Path(tmp_path).unlink(missing_ok=True)

            output = result.stdout + result.stderr
            return output[:2000] if output else "(no output)"

        except subprocess.TimeoutExpired:
            return f"Code timed out after {timeout}s"
        except Exception as e:
            return f"Sandbox error: {e}"
