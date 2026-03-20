"""
Plugin Marketplace — install, update, and remove community skill packs.
Skills are Python files that add new tools to the agent.

Installation sources:
  1. Local .py file
  2. URL (direct download)
  3. GitHub repo (downloads all tools/*.py files)

All plugins are validated before installation (AST safety check).
Installed plugins go to tools/registry/ and are hot-loaded.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path

from utils.logger import get_logger

log = get_logger(__name__)

_PLUGINS_DIR = Path("plugins/installed")
_REGISTRY_DIR = Path("tools/registry")
_MANIFEST_FILE = Path("plugins/manifest.json")

# SECURITY: comprehensive block list for plugin code scanning
# Uses AST analysis — not just string matching — to detect obfuscated imports
_BLOCKED_STRINGS = {
    "os.system", "subprocess.call", "subprocess.Popen", "subprocess.run",
    "eval(", "exec(", "__import__", "ctypes", "winreg", "socket.connect",
    "urllib.request", "requests.get", "requests.post", "open(",
}
_BLOCKED_IMPORTS = {
    "ctypes", "winreg", "subprocess", "socket", "pty", "os",
    "sys", "shutil", "importlib",
}


class PluginMarketplace:

    def __init__(self):
        _PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        self._manifest: dict = self._load_manifest()

    def install_from_file(self, path: str, name: str = "") -> dict:
        """Install a plugin from a local .py file."""
        src = Path(path)
        if not src.exists():
            return {"success": False, "error": f"File not found: {path}"}
        return self._install_file(src, name or src.stem)

    def install_from_url(self, url: str, name: str = "") -> dict:
        """Download and install a plugin from a URL."""
        try:
            import requests
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            plugin_name = name or url.split("/")[-1].replace(".py", "")
            tmp = _PLUGINS_DIR / f"{plugin_name}_download.py"
            tmp.write_text(resp.text, encoding="utf-8")
            result = self._install_file(tmp, plugin_name)
            tmp.unlink(missing_ok=True)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def install_from_github(self, repo: str, subfolder: str = "tools") -> dict:
        """Install all tool files from a GitHub repo subfolder.
        repo: 'owner/repo-name'
        """
        try:
            import requests
            api_url = f"https://api.github.com/repos/{repo}/contents/{subfolder}"
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            files = [f for f in resp.json() if f["name"].endswith(".py")]
            results = []
            for f in files:
                dl = requests.get(f["download_url"], timeout=15)
                plugin_name = f["name"].replace(".py", "")
                tmp = _PLUGINS_DIR / f["name"]
                tmp.write_text(dl.text, encoding="utf-8")
                r = self._install_file(tmp, plugin_name)
                results.append(r)
                tmp.unlink(missing_ok=True)
            success = sum(1 for r in results if r.get("success"))
            return {"success": True, "installed": success, "total": len(files), "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def uninstall(self, plugin_name: str) -> dict:
        """Remove an installed plugin."""
        registry_file = _REGISTRY_DIR / f"{plugin_name}.py"
        if registry_file.exists():
            registry_file.unlink()
        if plugin_name in self._manifest:
            del self._manifest[plugin_name]
            self._save_manifest()
        return {"success": True, "message": f"Removed: {plugin_name}"}

    def list_installed(self) -> list[dict]:
        return list(self._manifest.values())

    def _install_file(self, src: Path, name: str) -> dict:
        code = src.read_text(encoding="utf-8")

        # Safety validation
        issues = self._validate(code)
        if issues:
            return {"success": False, "error": f"Safety check failed: {'; '.join(issues)}"}

        # Detect tool names defined in file
        tool_names = self._extract_tool_names(code)

        # Copy to registry
        dest = _REGISTRY_DIR / f"{name}.py"
        shutil.copy2(src, dest)

        # Record in manifest
        self._manifest[name] = {
            "name": name,
            "file": str(dest),
            "tools": tool_names,
            "hash": hashlib.md5(code.encode()).hexdigest(),
        }
        self._save_manifest()
        log.info(f"Plugin installed: {name} ({tool_names})")
        return {"success": True, "name": name, "tools": tool_names}

    def _validate(self, code: str) -> list[str]:
        issues = []
        # AST parse check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]
        # AST-level import analysis (catches obfuscated imports)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mods = [alias.name.split(".")[0] for alias in node.names]
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module.split(".")[0])
                for mod in mods:
                    if mod in _BLOCKED_IMPORTS:
                        issues.append(f"Blocked import: {mod}")
            # Detect dynamic __import__ calls
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in ("eval", "exec", "__import__", "compile"):
                    issues.append(f"Blocked builtin call: {func.id}()")
        # String search for blocked patterns
        for blocked in _BLOCKED_STRINGS:
            if blocked in code:
                issues.append(f"Blocked pattern: {blocked}")
        return issues

    def _extract_tool_names(self, code: str) -> list[str]:
        names = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "name":
                                    if isinstance(item.value, ast.Constant):
                                        names.append(item.value.value)
        except Exception:
            pass
        return names

    def _load_manifest(self) -> dict:
        if _MANIFEST_FILE.exists():
            try:
                return json.loads(_MANIFEST_FILE.read_text())
            except Exception:
                pass
        return {}

    def _save_manifest(self) -> None:
        _MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MANIFEST_FILE.write_text(json.dumps(self._manifest, indent=2), encoding="utf-8")
