"""Archive skill pack — create, extract, list zip/tar/gz archives."""

from tools.base_tool import BaseTool


class ArchiveCreateTool(BaseTool):
    name = "archive_create"
    description = "Create a zip or tar.gz archive from files or directories."
    parameters = {"type": "object", "properties": {
        "output": {"type": "string", "description": "Output archive path (e.g. backup.zip, archive.tar.gz)"},
        "sources": {"type": "string", "description": "Comma-separated list of files/directories to include"},
        "format": {"type": "string", "enum": ["zip", "tar.gz", "tar"], "default": "zip"},
    }, "required": ["output", "sources"]}

    def run(self, output: str, sources: str, format: str = "zip") -> str:
        from pathlib import Path
        import zipfile
        import tarfile

        source_list = [s.strip() for s in sources.split(",")]
        try:
            if format == "zip":
                with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
                    count = 0
                    for src in source_list:
                        p = Path(src)
                        if p.is_file():
                            zf.write(p, p.name)
                            count += 1
                        elif p.is_dir():
                            for f in p.rglob("*"):
                                if f.is_file():
                                    zf.write(f, f.relative_to(p.parent))
                                    count += 1
                return f"Created {output} with {count} files."
            else:
                mode = "w:gz" if format == "tar.gz" else "w"
                with tarfile.open(output, mode) as tf:
                    count = 0
                    for src in source_list:
                        p = Path(src)
                        tf.add(p, arcname=p.name)
                        if p.is_dir():
                            count += sum(1 for _ in p.rglob("*") if _.is_file())
                        else:
                            count += 1
                return f"Created {output} with {count} files."
        except Exception as e:
            return f"Error: {e}"


class ArchiveExtractTool(BaseTool):
    name = "archive_extract"
    description = "Extract a zip, tar, or tar.gz archive to a directory."
    parameters = {"type": "object", "properties": {
        "archive": {"type": "string", "description": "Path to the archive file"},
        "destination": {"type": "string", "default": ".", "description": "Directory to extract to"},
    }, "required": ["archive"]}

    def run(self, archive: str, destination: str = ".") -> str:
        from pathlib import Path
        import zipfile
        import tarfile

        try:
            Path(destination).mkdir(parents=True, exist_ok=True)
            if archive.endswith(".zip"):
                with zipfile.ZipFile(archive, "r") as zf:
                    zf.extractall(destination)
                    return f"Extracted {len(zf.namelist())} files to {destination}"
            elif archive.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar")):
                with tarfile.open(archive, "r:*") as tf:
                    members = tf.getmembers()
                    tf.extractall(destination, filter="data")
                    return f"Extracted {len(members)} entries to {destination}"
            else:
                return f"Unsupported archive format: {archive}"
        except Exception as e:
            return f"Error: {e}"


class ArchiveListTool(BaseTool):
    name = "archive_list"
    description = "List contents of a zip or tar archive without extracting."
    parameters = {"type": "object", "properties": {
        "archive": {"type": "string"},
        "max_entries": {"type": "integer", "default": 50},
    }, "required": ["archive"]}

    def run(self, archive: str, max_entries: int = 50) -> str:
        import zipfile
        import tarfile
        try:
            if archive.endswith(".zip"):
                with zipfile.ZipFile(archive, "r") as zf:
                    infos = zf.infolist()
                    lines = [f"Archive: {archive} ({len(infos)} entries)"]
                    for info in infos[:max_entries]:
                        size = f"{info.file_size:,}" if info.file_size else "dir"
                        lines.append(f"  {info.filename} ({size} bytes)")
                    return "\n".join(lines)
            elif archive.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar")):
                with tarfile.open(archive, "r:*") as tf:
                    members = tf.getmembers()
                    lines = [f"Archive: {archive} ({len(members)} entries)"]
                    for m in members[:max_entries]:
                        lines.append(f"  {m.name} ({m.size:,} bytes)")
                    return "\n".join(lines)
            return f"Unsupported format: {archive}"
        except Exception as e:
            return f"Error: {e}"
