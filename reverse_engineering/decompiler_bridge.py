"""
Decompiler bridge — integrates with Ghidra (headless mode) and optionally
RetDec (open-source decompiler) to produce pseudo-C decompilation output.

Ghidra headless requires:
  - GHIDRA_HOME environment variable pointing to Ghidra installation
  - Java installed and on PATH

RetDec requires:
  - retdec-decompiler on PATH (pip install retdec-python OR standalone install)
"""

from __future__ import annotations
import os
import subprocess
import tempfile
import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class DecompileResult:
    file: str
    tool: str
    success: bool
    pseudo_c: str = ""
    functions: list[dict] = field(default_factory=list)
    error: str = ""


class GhidraDecompiler:
    """
    Runs Ghidra in headless mode, executes a PostScript to extract
    decompiled C output for every function in the binary.
    """

    # Ghidra PostScript that dumps decompiled C for all functions
    _GHIDRA_SCRIPT = '''
import ghidra.app.decompiler.DecompInterface as DecompInterface
import ghidra.util.task.ConsoleTaskMonitor as ConsoleTaskMonitor
import java.io.PrintWriter as PrintWriter
import sys

decompiler = DecompInterface()
decompiler.openProgram(currentProgram)
monitor = ConsoleTaskMonitor()

output = []
for func in currentProgram.getFunctionManager().getFunctions(True):
    result = decompiler.decompileFunction(func, 30, monitor)
    if result and result.decompileCompleted():
        code = result.getDecompiledFunction().getC()
        output.append({"name": func.getName(), "address": str(func.getEntryPoint()), "code": code})

import json
print("GHIDRA_OUTPUT_START")
print(json.dumps(output))
print("GHIDRA_OUTPUT_END")
'''

    def decompile(self, path: str, ghidra_home: str | None = None) -> DecompileResult:
        ghidra_home = ghidra_home or os.environ.get("GHIDRA_HOME", "")
        if not ghidra_home or not Path(ghidra_home).exists():
            return DecompileResult(
                file=path, tool="ghidra", success=False,
                error="Ghidra not found. Set GHIDRA_HOME env variable to Ghidra installation path."
            )

        analyzer = Path(ghidra_home) / "support" / "analyzeHeadless"
        if os.name == "nt":
            analyzer = analyzer.with_suffix(".bat")
        if not analyzer.exists():
            return DecompileResult(
                file=path, tool="ghidra", success=False,
                error=f"analyzeHeadless not found at {analyzer}"
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "ExtractDecompiled.py"
            script_file.write_text(self._GHIDRA_SCRIPT)
            project_dir = Path(tmpdir) / "ghidra_proj"
            project_dir.mkdir()

            cmd = [
                str(analyzer),
                str(project_dir), "TempProject",
                "-import", path,
                "-postScript", str(script_file),
                "-deleteProject",
                "-noanalysis" if False else "",
            ]
            cmd = [c for c in cmd if c]  # remove empty strings

            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300
                )
                output = proc.stdout

                # Parse the JSON block between markers
                if "GHIDRA_OUTPUT_START" in output:
                    start = output.index("GHIDRA_OUTPUT_START") + len("GHIDRA_OUTPUT_START")
                    end = output.index("GHIDRA_OUTPUT_END")
                    json_block = output[start:end].strip()
                    functions = json.loads(json_block)
                    pseudo_c = "\n\n".join(
                        f"// {f['name']} @ {f['address']}\n{f['code']}"
                        for f in functions
                    )
                    return DecompileResult(
                        file=path, tool="ghidra", success=True,
                        pseudo_c=pseudo_c, functions=functions
                    )
                else:
                    return DecompileResult(
                        file=path, tool="ghidra", success=False,
                        error=f"No output from Ghidra. stderr: {proc.stderr[:500]}"
                    )

            except subprocess.TimeoutExpired:
                return DecompileResult(
                    file=path, tool="ghidra", success=False,
                    error="Ghidra timed out after 300 seconds"
                )
            except Exception as e:
                return DecompileResult(
                    file=path, tool="ghidra", success=False, error=str(e)
                )


class RetDecDecompiler:
    """
    Uses RetDec (open-source decompiler) for decompilation.
    Requires retdec-decompiler on PATH.
    """

    def decompile(self, path: str) -> DecompileResult:
        try:
            # Check if retdec-decompiler is available
            check = subprocess.run(
                ["retdec-decompiler", "--version"],
                capture_output=True, text=True, timeout=10
            )
            if check.returncode != 0:
                raise FileNotFoundError("retdec-decompiler not found")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return DecompileResult(
                file=path, tool="retdec", success=False,
                error="RetDec not installed. See: https://github.com/avast/retdec"
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_base = Path(tmpdir) / "output"
            cmd = [
                "retdec-decompiler",
                "--output", str(out_base),
                path
            ]
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300
                )
                c_file = out_base.with_suffix(".c")
                if c_file.exists():
                    pseudo_c = c_file.read_text(errors="replace")
                    return DecompileResult(
                        file=path, tool="retdec", success=True,
                        pseudo_c=pseudo_c
                    )
                else:
                    return DecompileResult(
                        file=path, tool="retdec", success=False,
                        error=f"RetDec produced no output. stderr: {proc.stderr[:500]}"
                    )
            except subprocess.TimeoutExpired:
                return DecompileResult(
                    file=path, tool="retdec", success=False,
                    error="RetDec timed out after 300 seconds"
                )
            except Exception as e:
                return DecompileResult(
                    file=path, tool="retdec", success=False, error=str(e)
                )


class DecompilerBridge:
    """
    Auto-selects best available decompiler:
    1. Ghidra (if GHIDRA_HOME set)
    2. RetDec (if retdec-decompiler on PATH)
    3. Falls back to r2pipe's pdg (Ghidra plugin inside r2)
    """

    def decompile(self, path: str) -> DecompileResult:
        # Try Ghidra first
        if os.environ.get("GHIDRA_HOME"):
            result = GhidraDecompiler().decompile(path)
            if result.success:
                return result

        # Try RetDec
        result = RetDecDecompiler().decompile(path)
        if result.success:
            return result

        # Try r2pipe with Ghidra plugin (r2ghidra)
        return self._r2_ghidra(path)

    def _r2_ghidra(self, path: str) -> DecompileResult:
        """Use r2pipe with r2ghidra plugin (pdg command)."""
        try:
            import r2pipe
            r2 = r2pipe.open(path, flags=["-2"])
            r2.cmd("aaa")
            funcs = r2.cmdj("aflj") or []

            pseudo_c_parts = []
            functions = []
            for func in funcs[:50]:  # cap at 50 functions
                decompiled = r2.cmd(f"pdg @ {func['offset']}")
                if decompiled and "Cannot find" not in decompiled:
                    pseudo_c_parts.append(
                        f"// {func.get('name', 'unknown')} @ 0x{func['offset']:x}\n{decompiled}"
                    )
                    functions.append({
                        "name": func.get("name", "unknown"),
                        "address": hex(func["offset"]),
                        "code": decompiled,
                    })
            r2.quit()

            if pseudo_c_parts:
                return DecompileResult(
                    file=path, tool="r2ghidra", success=True,
                    pseudo_c="\n\n".join(pseudo_c_parts),
                    functions=functions
                )
            return DecompileResult(
                file=path, tool="r2ghidra", success=False,
                error="r2ghidra plugin not available. Install: r2pm -ci r2ghidra"
            )
        except ImportError:
            return DecompileResult(
                file=path, tool="none", success=False,
                error="No decompiler available. Install Ghidra, RetDec, or r2ghidra."
            )
        except Exception as e:
            return DecompileResult(
                file=path, tool="r2ghidra", success=False, error=str(e)
            )
