"""
Binary analyzer using r2pipe (Radare2) for disassembly, function detection,
control-flow analysis, and basic static analysis of executables.
Falls back gracefully if radare2 is not installed.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Function:
    offset: int
    name: str
    size: int
    instructions: list[dict] = field(default_factory=list)


@dataclass
class AnalysisResult:
    file: str
    arch: str
    bits: int
    os: str
    entry_point: int
    functions: list[Function]
    strings: list[dict]
    imports: list[str]
    symbols: list[dict]
    raw: dict


class BinaryAnalyzer:
    """Static binary analysis via Radare2 (r2pipe)."""

    def analyze(self, path: str, deep: bool = False) -> AnalysisResult:
        """
        Analyze a binary file.
        deep=True runs full function analysis (slower).
        deep=False runs quick analysis (aaa vs aaaa).
        """
        try:
            import r2pipe
        except ImportError:
            return self._error_result(path, "r2pipe not installed. Run: pip install r2pipe  (also needs radare2 installed)")

        try:
            r2 = r2pipe.open(path, flags=["-2"])  # -2 suppresses stderr
            r2.cmd("aaa" if not deep else "aaaa")  # analyze

            info = r2.cmdj("ij") or {}
            bin_info = info.get("bin", {})
            core_info = info.get("core", {})

            # Functions
            funcs_raw = r2.cmdj("aflj") or []
            functions = []
            for f in funcs_raw[:100]:  # cap at 100 for performance
                func = Function(
                    offset=f.get("offset", 0),
                    name=f.get("name", "unknown"),
                    size=f.get("size", 0),
                )
                # Disassemble first 40 instructions of each function
                disasm = r2.cmdj(f"pdfj @ {f['offset']}") or {}
                ops = disasm.get("ops", [])[:40]
                func.instructions = [
                    {
                        "addr": op.get("offset"),
                        "mnem": op.get("disasm", ""),
                        "type": op.get("type", ""),
                    }
                    for op in ops
                ]
                functions.append(func)

            # Strings
            strings_raw = r2.cmdj("izj") or []
            strings = [
                {
                    "offset": s.get("vaddr", s.get("paddr", 0)),
                    "length": s.get("length", 0),
                    "section": s.get("section", ""),
                    "value": s.get("string", ""),
                }
                for s in strings_raw[:500]
            ]

            # Imports
            imports_raw = r2.cmdj("iij") or []
            imports = [imp.get("name", "") for imp in imports_raw if imp.get("name")]

            # Symbols
            syms_raw = r2.cmdj("isj") or []
            symbols = [
                {
                    "name": s.get("name", ""),
                    "type": s.get("type", ""),
                    "offset": s.get("vaddr", 0),
                }
                for s in syms_raw[:200]
            ]

            entry_points = r2.cmdj("iej") or []
            entry = entry_points[0].get("vaddr", 0) if entry_points else 0

            r2.quit()

            return AnalysisResult(
                file=path,
                arch=bin_info.get("arch", "unknown"),
                bits=bin_info.get("bits", 0),
                os=bin_info.get("os", "unknown"),
                entry_point=entry,
                functions=functions,
                strings=strings,
                imports=imports,
                symbols=symbols,
                raw={"bin": bin_info, "core": core_info},
            )

        except Exception as e:
            return self._error_result(path, str(e))

    def disassemble_range(self, path: str, offset: int, n_instructions: int = 50) -> list[dict]:
        """Disassemble N instructions starting at offset."""
        try:
            import r2pipe
            r2 = r2pipe.open(path, flags=["-2"])
            ops = r2.cmdj(f"pdj {n_instructions} @ {offset}") or []
            r2.quit()
            return [{"addr": op.get("offset"), "mnem": op.get("disasm", "")} for op in ops]
        except Exception as e:
            return [{"error": str(e)}]

    def find_suspicious_functions(self, result: AnalysisResult) -> list[dict]:
        """
        Heuristically flag suspicious functions:
        - Very large functions (>500 instructions) — potential packed code
        - Functions with many system call mnemonics
        - Functions named 'fcn.' (unnamed — stripped binary)
        """
        suspicious = []
        syscall_keywords = {"int ", "syscall", "sysenter", "CreateRemoteThread",
                            "VirtualAllocEx", "WriteProcessMemory", "ShellExecute"}

        for func in result.functions:
            reasons = []
            if len(func.instructions) >= 40:  # we cap at 40 so this means it hit the cap
                reasons.append("large_function")
            if func.name.startswith("fcn."):
                reasons.append("unnamed_function")
            mnemonics = " ".join(i.get("mnem", "") for i in func.instructions)
            for kw in syscall_keywords:
                if kw.lower() in mnemonics.lower():
                    reasons.append(f"uses_{kw.replace(' ', '_')}")

            if reasons:
                suspicious.append({
                    "name": func.name,
                    "offset": hex(func.offset),
                    "size": func.size,
                    "reasons": reasons,
                })
        return suspicious

    def _error_result(self, path: str, error: str) -> AnalysisResult:
        return AnalysisResult(
            file=path, arch="", bits=0, os="", entry_point=0,
            functions=[], strings=[], imports=[], symbols=[],
            raw={"error": error},
        )
