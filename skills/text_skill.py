"""Text Manipulation skill pack — regex, formatting, diff, encoding, conversion."""

from tools.base_tool import BaseTool


class RegexReplaceTool(BaseTool):
    name = "regex_replace"
    description = "Find and replace text in a file using regex patterns."
    parameters = {"type": "object", "properties": {
        "file_path": {"type": "string"},
        "pattern": {"type": "string", "description": "Regex pattern to find"},
        "replacement": {"type": "string", "description": "Replacement string (supports \\1, \\2 groups)"},
        "count": {"type": "integer", "default": 0, "description": "Max replacements (0 = all)"},
    }, "required": ["file_path", "pattern", "replacement"]}

    def run(self, file_path: str, pattern: str, replacement: str, count: int = 0) -> str:
        import re
        try:
            content = open(file_path, encoding="utf-8").read()
            new_content, n = re.subn(pattern, replacement, content, count=count)
            if n == 0:
                return "No matches found."
            open(file_path, "w", encoding="utf-8").write(new_content)
            return f"Replaced {n} occurrence(s)."
        except re.error as e:
            return f"Regex error: {e}"
        except Exception as e:
            return f"Error: {e}"


class RegexFindTool(BaseTool):
    name = "regex_find"
    description = "Find all regex matches in a file or text."
    parameters = {"type": "object", "properties": {
        "text": {"type": "string", "description": "Text to search (or file path if is_file=true)"},
        "pattern": {"type": "string", "description": "Regex pattern"},
        "is_file": {"type": "boolean", "default": False},
        "max_matches": {"type": "integer", "default": 50},
    }, "required": ["text", "pattern"]}

    def run(self, text: str, pattern: str, is_file: bool = False, max_matches: int = 50) -> str:
        import re
        try:
            content = open(text, encoding="utf-8").read() if is_file else text
            matches = list(re.finditer(pattern, content))
            if not matches:
                return "No matches found."
            lines = [f"Found {len(matches)} matches:"]
            for i, m in enumerate(matches[:max_matches]):
                groups = m.groups()
                if groups:
                    lines.append(f"  [{i}] {m.group()} → groups: {groups}")
                else:
                    lines.append(f"  [{i}] {m.group()}")
            return "\n".join(lines)
        except re.error as e:
            return f"Regex error: {e}"
        except Exception as e:
            return f"Error: {e}"


class TextFormatTool(BaseTool):
    name = "text_format"
    description = "Format text: JSON prettify, XML prettify, minify, sort lines, deduplicate."
    parameters = {"type": "object", "properties": {
        "file_path": {"type": "string"},
        "operation": {"type": "string", "enum": [
            "json_prettify", "json_minify", "xml_prettify",
            "sort_lines", "sort_lines_reverse", "deduplicate",
            "trim_whitespace", "remove_blank_lines", "lowercase", "uppercase"
        ]},
    }, "required": ["file_path", "operation"]}

    def run(self, file_path: str, operation: str) -> str:
        try:
            content = open(file_path, encoding="utf-8").read()
            original_len = len(content)

            if operation == "json_prettify":
                import json
                data = json.loads(content)
                content = json.dumps(data, indent=2, ensure_ascii=False)
            elif operation == "json_minify":
                import json
                data = json.loads(content)
                content = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            elif operation == "xml_prettify":
                import xml.dom.minidom
                dom = xml.dom.minidom.parseString(content)
                content = dom.toprettyxml(indent="  ")
            elif operation == "sort_lines":
                content = "\n".join(sorted(content.splitlines()))
            elif operation == "sort_lines_reverse":
                content = "\n".join(sorted(content.splitlines(), reverse=True))
            elif operation == "deduplicate":
                seen = set()
                unique = []
                for line in content.splitlines():
                    if line not in seen:
                        seen.add(line)
                        unique.append(line)
                content = "\n".join(unique)
            elif operation == "trim_whitespace":
                content = "\n".join(line.rstrip() for line in content.splitlines())
            elif operation == "remove_blank_lines":
                content = "\n".join(line for line in content.splitlines() if line.strip())
            elif operation == "lowercase":
                content = content.lower()
            elif operation == "uppercase":
                content = content.upper()
            else:
                return f"Unknown operation: {operation}"

            open(file_path, "w", encoding="utf-8").write(content)
            return f"Done. {original_len} → {len(content)} chars."
        except Exception as e:
            return f"Error: {e}"


class TextDiffTool(BaseTool):
    name = "text_diff"
    description = "Compare two text files and show differences (unified diff)."
    parameters = {"type": "object", "properties": {
        "file1": {"type": "string"},
        "file2": {"type": "string"},
        "context_lines": {"type": "integer", "default": 3},
    }, "required": ["file1", "file2"]}

    def run(self, file1: str, file2: str, context_lines: int = 3) -> str:
        import difflib
        try:
            lines1 = open(file1, encoding="utf-8").readlines()
            lines2 = open(file2, encoding="utf-8").readlines()
            diff = difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2, n=context_lines)
            result = "".join(diff)
            return result[:5000] if result else "Files are identical."
        except Exception as e:
            return f"Error: {e}"


class TextEncodingTool(BaseTool):
    name = "text_encoding"
    description = "Convert file encoding (e.g. UTF-8 to Latin-1) or detect encoding."
    parameters = {"type": "object", "properties": {
        "file_path": {"type": "string"},
        "action": {"type": "string", "enum": ["detect", "convert"], "default": "detect"},
        "target_encoding": {"type": "string", "default": "utf-8"},
    }, "required": ["file_path"]}

    def run(self, file_path: str, action: str = "detect", target_encoding: str = "utf-8") -> str:
        try:
            raw = open(file_path, "rb").read()
            if action == "detect":
                # Try common encodings
                for enc in ["utf-8", "utf-8-sig", "ascii", "latin-1", "cp1252", "utf-16"]:
                    try:
                        raw.decode(enc)
                        return f"Detected encoding: {enc} ({len(raw)} bytes)"
                    except (UnicodeDecodeError, Exception):
                        continue
                return "Could not detect encoding."
            elif action == "convert":
                # Detect source encoding first
                text = None
                source_enc = "unknown"
                for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252", "utf-16"]:
                    try:
                        text = raw.decode(enc)
                        source_enc = enc
                        break
                    except Exception:
                        continue
                if text is None:
                    return "Could not decode file."
                open(file_path, "w", encoding=target_encoding).write(text)
                return f"Converted from {source_enc} to {target_encoding}."
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Error: {e}"


class TextStatsTool(BaseTool):
    name = "text_stats"
    description = "Get statistics about a text file — lines, words, chars, unique words."
    parameters = {"type": "object", "properties": {
        "file_path": {"type": "string"},
    }, "required": ["file_path"]}

    def run(self, file_path: str) -> str:
        try:
            content = open(file_path, encoding="utf-8").read()
            lines = content.splitlines()
            words = content.split()
            unique = set(w.lower() for w in words)
            blank = sum(1 for l in lines if not l.strip())
            return (
                f"Lines: {len(lines)} ({blank} blank)\n"
                f"Words: {len(words)} ({len(unique)} unique)\n"
                f"Characters: {len(content)}\n"
                f"Size: {len(content.encode('utf-8')):,} bytes\n"
                f"Avg words/line: {len(words) / max(len(lines), 1):.1f}"
            )
        except Exception as e:
            return f"Error: {e}"
