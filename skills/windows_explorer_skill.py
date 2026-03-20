"""Windows Explorer / file system skill pack."""

from tools.base_tool import BaseTool


class FindFilesTool(BaseTool):
    name = "find_files"
    description = "Search for files by name pattern, extension, or content."
    parameters = {"type": "object", "properties": {
        "directory": {"type": "string"}, "pattern": {"type": "string", "default": "*"},
        "content_search": {"type": "string", "default": ""},
        "max_results": {"type": "integer", "default": 20},
    }, "required": ["directory"]}

    def run(self, directory: str, pattern: str = "*", content_search: str = "", max_results: int = 20) -> str:
        from pathlib import Path
        try:
            results = []
            base = Path(directory)
            for f in base.rglob(pattern):
                if f.is_file():
                    if content_search:
                        try:
                            if content_search.lower() in f.read_text(encoding="utf-8", errors="ignore").lower():
                                results.append(str(f))
                        except Exception:
                            pass
                    else:
                        results.append(str(f))
                if len(results) >= max_results:
                    break
            return "\n".join(results) if results else "No files found"
        except Exception as e:
            return f"Error: {e}"


class OrganizeFilesTool(BaseTool):
    name = "organize_files"
    description = "Move files in a directory into subfolders organized by extension."
    parameters = {"type": "object", "properties": {"directory": {"type": "string"}}, "required": ["directory"]}

    def run(self, directory: str) -> str:
        from pathlib import Path
        import shutil
        moved = []
        base = Path(directory)
        ext_map = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
            "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
            "Audio": [".mp3", ".wav", ".flac", ".aac"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".xml"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
        }
        try:
            for file in base.iterdir():
                if not file.is_file():
                    continue
                ext = file.suffix.lower()
                for folder, exts in ext_map.items():
                    if ext in exts:
                        dest_dir = base / folder
                        dest_dir.mkdir(exist_ok=True)
                        shutil.move(str(file), str(dest_dir / file.name))
                        moved.append(f"{file.name} → {folder}/")
                        break
            return f"Moved {len(moved)} files:\n" + "\n".join(moved[:20])
        except Exception as e:
            return f"Error: {e}"


class BulkRenameTool(BaseTool):
    name = "bulk_rename"
    description = "Rename multiple files matching a pattern."
    parameters = {"type": "object", "properties": {
        "directory": {"type": "string"},
        "pattern": {"type": "string", "description": "glob pattern e.g. *.txt"},
        "find": {"type": "string"}, "replace": {"type": "string"},
    }, "required": ["directory", "pattern", "find", "replace"]}

    def run(self, directory: str, pattern: str, find: str, replace: str) -> str:
        from pathlib import Path
        renamed = []
        for f in Path(directory).glob(pattern):
            new_name = f.name.replace(find, replace)
            if new_name != f.name:
                f.rename(f.parent / new_name)
                renamed.append(f"{f.name} → {new_name}")
        return f"Renamed {len(renamed)} files:\n" + "\n".join(renamed[:20])
