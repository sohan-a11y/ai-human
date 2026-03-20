"""
VersionManager — manages snapshots of the AI Human codebase.
Before any self-modification, a full copy of current code is saved.
If the new version fails, rollback restores the previous copy exactly.

Version storage:
  versions/
    v_20250310_153042/     ← timestamped snapshots
      ... (full code copy)
    current -> symlink or text file pointing to active version
    rollback.json          ← rollback instructions
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from utils.logger import get_logger

log = get_logger(__name__)

_ROOT = Path(__file__).parent.parent
_VERSIONS_DIR = _ROOT / "versions"

# Folders/files to exclude from version snapshots (data, logs, etc.)
_EXCLUDE = {
    "versions", "data", "__pycache__", ".git",
    "*.pyc", "*.log", "*.jsonl",
}


class VersionManager:

    def __init__(self):
        _VERSIONS_DIR.mkdir(exist_ok=True)

    def snapshot(self) -> str:
        """
        Create a timestamped snapshot of the current codebase.
        Returns the version ID (e.g. 'v_20250310_153042').
        """
        version_id = f"v_{time.strftime('%Y%m%d_%H%M%S')}"
        dest = _VERSIONS_DIR / version_id

        log.info(f"Creating snapshot: {version_id}")
        self._copy_codebase(_ROOT, dest)

        # Write version manifest
        (dest / "VERSION.json").write_text(json.dumps({
            "id": version_id,
            "created": time.time(),
            "created_human": time.strftime("%Y-%m-%d %H:%M:%S"),
        }), encoding="utf-8")

        self._set_current(version_id)
        log.info(f"Snapshot saved: {dest}")
        return version_id

    def rollback(self, version_id: str) -> bool:
        """
        Restore a previous version by copying it back to the root.
        Returns True on success.
        """
        source = _VERSIONS_DIR / version_id
        if not source.exists():
            log.error(f"Version not found: {version_id}")
            return False

        log.warning(f"ROLLING BACK to {version_id}")
        self._copy_codebase(source, _ROOT, overwrite=True)
        self._set_current(version_id)
        log.info("Rollback complete")
        return True

    def list_versions(self) -> list[dict]:
        versions = []
        for d in sorted(_VERSIONS_DIR.iterdir()):
            if d.is_dir() and d.name.startswith("v_"):
                manifest = d / "VERSION.json"
                if manifest.exists():
                    versions.append(json.loads(manifest.read_text()))
        return versions

    def get_previous_version(self) -> str | None:
        versions = self.list_versions()
        if len(versions) >= 2:
            return versions[-2]["id"]
        return None

    def _set_current(self, version_id: str) -> None:
        (_VERSIONS_DIR / "current.txt").write_text(version_id, encoding="utf-8")

    def get_current(self) -> str:
        f = _VERSIONS_DIR / "current.txt"
        return f.read_text().strip() if f.exists() else "unknown"

    def _copy_codebase(self, src: Path, dst: Path, overwrite: bool = False) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if self._should_exclude(item):
                continue
            target = dst / item.name
            if item.is_dir():
                if target.exists() and overwrite:
                    shutil.rmtree(target)
                shutil.copytree(item, target, ignore=shutil.ignore_patterns(*_EXCLUDE), dirs_exist_ok=True)
            else:
                if overwrite or not target.exists():
                    shutil.copy2(item, target)

    def _should_exclude(self, path: Path) -> bool:
        name = path.name
        if name in _EXCLUDE:
            return True
        if name.startswith(".") and name not in (".env",):
            return True
        if name.endswith((".pyc", ".log", ".jsonl")):
            return True
        return False
