"""PE file parser — extracts imports, exports, sections, headers from .exe/.dll files."""

from __future__ import annotations
from pathlib import Path


class PEParser:

    def parse(self, path: str) -> dict:
        try:
            import pefile
            pe = pefile.PE(path)
            result = {
                "file": Path(path).name,
                "machine": hex(pe.FILE_HEADER.Machine),
                "is_dll": bool(pe.FILE_HEADER.Characteristics & 0x2000),
                "is_exe": bool(pe.FILE_HEADER.Characteristics & 0x0002),
                "timestamp": pe.FILE_HEADER.TimeDateStamp,
                "sections": [],
                "imports": [],
                "exports": [],
            }
            for section in pe.sections:
                result["sections"].append({
                    "name": section.Name.decode(errors="replace").strip("\x00"),
                    "virtual_size": hex(section.Misc_VirtualSize),
                    "raw_size": section.SizeOfRawData,
                    "entropy": round(section.get_entropy(), 2),
                })
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    dll_name = entry.dll.decode(errors="replace")
                    funcs = []
                    for imp in entry.imports:
                        if imp.name:
                            funcs.append(imp.name.decode(errors="replace"))
                    result["imports"].append({"dll": dll_name, "functions": funcs[:20]})
            if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
                for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if exp.name:
                        result["exports"].append(exp.name.decode(errors="replace"))
            return result
        except ImportError:
            return {"error": "pefile not installed. Run: pip install pefile"}
        except Exception as e:
            return {"error": str(e)}
