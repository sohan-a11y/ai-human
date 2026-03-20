"""
Reverse Engineering Reporter — combines output from PEParser, BinaryAnalyzer,
StringExtractor, and DecompilerBridge into a comprehensive Markdown report.
Also produces a JSON export for programmatic use.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from dataclasses import asdict


class REReporter:
    """Aggregate all RE analysis results into a Markdown + JSON report."""

    def generate(
        self,
        path: str,
        pe_result: dict | None = None,
        analysis_result=None,           # BinaryAnalyzer.AnalysisResult
        strings: list | None = None,    # list[ExtractedString]
        decompile_result=None,          # DecompilerBridge.DecompileResult
        output_dir: str = "data/re_reports",
    ) -> str:
        """
        Generate and save report. Returns path to the saved Markdown file.
        """
        report_dir = Path(output_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        file_name = Path(path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = report_dir / f"{file_name}_{timestamp}.md"
        json_path = report_dir / f"{file_name}_{timestamp}.json"

        md = self._build_markdown(path, pe_result, analysis_result, strings, decompile_result)
        json_data = self._build_json(path, pe_result, analysis_result, strings, decompile_result)

        md_path.write_text(md, encoding="utf-8")
        json_path.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")

        return str(md_path)

    def _build_markdown(self, path, pe_result, analysis_result, strings, decompile_result) -> str:
        lines = []
        fname = Path(path).name

        lines.append(f"# Reverse Engineering Report: `{fname}`")
        lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append(f"**File:** `{path}`\n")
        lines.append("---\n")

        # ── PE HEADER SECTION ──────────────────────────────────────────────────
        if pe_result and "error" not in pe_result:
            lines.append("## PE File Header\n")
            lines.append(f"| Property | Value |")
            lines.append("|---|---|")
            lines.append(f"| Machine | `{pe_result.get('machine', '?')}` |")
            lines.append(f"| Is DLL | `{pe_result.get('is_dll', '?')}` |")
            lines.append(f"| Is EXE | `{pe_result.get('is_exe', '?')}` |")
            lines.append(f"| Timestamp | `{pe_result.get('timestamp', '?')}` |")
            lines.append("")

            sections = pe_result.get("sections", [])
            if sections:
                lines.append("### Sections\n")
                lines.append("| Name | Virtual Size | Raw Size | Entropy |")
                lines.append("|---|---|---|---|")
                for s in sections:
                    entropy = s.get("entropy", 0)
                    flag = " ⚠️ HIGH" if entropy > 7.0 else (" ⚠️ PACKED?" if entropy > 6.5 else "")
                    lines.append(f"| `{s['name']}` | {s.get('virtual_size','?')} | {s.get('raw_size','?')} | {entropy}{flag} |")
                lines.append("")

            imports = pe_result.get("imports", [])
            if imports:
                lines.append("### Imports\n")
                for imp in imports:
                    lines.append(f"**{imp['dll']}**")
                    funcs = imp.get("functions", [])
                    if funcs:
                        lines.append(", ".join(f"`{f}`" for f in funcs[:15]))
                    lines.append("")

            exports = pe_result.get("exports", [])
            if exports:
                lines.append("### Exports\n")
                lines.append(", ".join(f"`{e}`" for e in exports[:30]))
                lines.append("")

        elif pe_result and "error" in pe_result:
            lines.append(f"## PE Analysis\n\n> {pe_result['error']}\n")

        # ── BINARY ANALYSIS SECTION ────────────────────────────────────────────
        if analysis_result:
            lines.append("## Binary Analysis (Radare2)\n")
            lines.append(f"| Property | Value |")
            lines.append("|---|---|")
            lines.append(f"| Architecture | `{analysis_result.arch}` |")
            lines.append(f"| Bits | `{analysis_result.bits}` |")
            lines.append(f"| OS | `{analysis_result.os}` |")
            lines.append(f"| Entry Point | `{hex(analysis_result.entry_point)}` |")
            lines.append(f"| Functions Found | `{len(analysis_result.functions)}` |")
            lines.append("")

            if analysis_result.functions:
                lines.append("### Top Functions\n")
                lines.append("| Name | Offset | Size |")
                lines.append("|---|---|---|")
                for f in analysis_result.functions[:20]:
                    lines.append(f"| `{f.name}` | `{hex(f.offset)}` | {f.size} bytes |")
                lines.append("")

            # Suspicious functions
            try:
                from reverse_engineering.binary_analyzer import BinaryAnalyzer
                suspicious = BinaryAnalyzer().find_suspicious_functions(analysis_result)
                if suspicious:
                    lines.append("### ⚠️ Suspicious Functions\n")
                    for sf in suspicious:
                        reasons = ", ".join(sf["reasons"])
                        lines.append(f"- `{sf['name']}` @ {sf['offset']} — **{reasons}**")
                    lines.append("")
            except Exception:
                pass

        # ── STRINGS SECTION ────────────────────────────────────────────────────
        if strings:
            interesting = [s for s in strings if s.category != "other"]
            lines.append(f"## Extracted Strings\n")
            lines.append(f"**Total strings:** {len(strings)}  ")
            lines.append(f"**Interesting strings:** {len(interesting)}\n")

            # Group by category
            from collections import defaultdict
            groups: dict[str, list] = defaultdict(list)
            for s in interesting:
                groups[s.category].append(s)

            category_labels = {
                "url": "URLs",
                "ip": "IP Addresses",
                "email": "Email Addresses",
                "path_win": "Windows Paths",
                "path_unix": "Unix Paths",
                "registry": "Registry Keys",
                "api": "Suspicious API Calls",
                "credential_hint": "⚠️ Credential Hints",
            }

            for cat, label in category_labels.items():
                items = groups.get(cat, [])
                if items:
                    lines.append(f"### {label}\n")
                    for s in items[:20]:
                        lines.append(f"- `[0x{s.offset:08X}]` `{s.value[:120]}`")
                    lines.append("")

        # ── DECOMPILATION SECTION ──────────────────────────────────────────────
        if decompile_result:
            lines.append(f"## Decompiled Output ({decompile_result.tool})\n")
            if decompile_result.success:
                lines.append(f"```c\n{decompile_result.pseudo_c[:8000]}")
                if len(decompile_result.pseudo_c) > 8000:
                    lines.append("// ... (truncated — see JSON report for full output)")
                lines.append("```\n")
            else:
                lines.append(f"> Decompilation failed: {decompile_result.error}\n")

        # ── THREAT SUMMARY ────────────────────────────────────────────────────
        lines.append("## Threat Indicators Summary\n")
        indicators = self._compute_threat_indicators(pe_result, analysis_result, strings)
        if indicators:
            for indicator in indicators:
                lines.append(f"- {indicator}")
        else:
            lines.append("- No obvious threat indicators detected.")
        lines.append("")

        lines.append("---")
        lines.append("*Report generated by AI Human Reverse Engineering Module*")

        return "\n".join(lines)

    def _build_json(self, path, pe_result, analysis_result, strings, decompile_result) -> dict:
        data: dict = {"file": path, "generated_at": datetime.now().isoformat()}
        if pe_result:
            data["pe"] = pe_result
        if analysis_result:
            data["binary_analysis"] = {
                "arch": analysis_result.arch,
                "bits": analysis_result.bits,
                "os": analysis_result.os,
                "entry_point": hex(analysis_result.entry_point),
                "function_count": len(analysis_result.functions),
                "functions": [
                    {"name": f.name, "offset": hex(f.offset), "size": f.size}
                    for f in analysis_result.functions
                ],
                "imports": analysis_result.imports,
            }
        if strings:
            data["strings"] = {
                "total": len(strings),
                "interesting": [
                    {"offset": hex(s.offset), "encoding": s.encoding,
                     "category": s.category, "value": s.value}
                    for s in strings if s.category != "other"
                ],
            }
        if decompile_result:
            data["decompilation"] = {
                "tool": decompile_result.tool,
                "success": decompile_result.success,
                "pseudo_c": decompile_result.pseudo_c if decompile_result.success else None,
                "error": decompile_result.error if not decompile_result.success else None,
            }
        data["threat_indicators"] = self._compute_threat_indicators(
            pe_result, analysis_result, strings
        )
        return data

    def _compute_threat_indicators(self, pe_result, analysis_result, strings) -> list[str]:
        indicators = []

        # PE-based
        if pe_result and "error" not in pe_result:
            for section in pe_result.get("sections", []):
                if section.get("entropy", 0) > 7.0:
                    indicators.append(
                        f"⚠️ HIGH entropy section `{section['name']}` ({section['entropy']}) — possible packing/encryption"
                    )
            imports = pe_result.get("imports", [])
            dangerous_imports = {
                "CreateRemoteThread", "VirtualAllocEx", "WriteProcessMemory",
                "URLDownloadToFile", "ShellExecuteA", "WinExec", "RegSetValueEx",
                "InternetOpenA", "InternetConnectA",
            }
            found_dangerous = []
            for imp in imports:
                for func in imp.get("functions", []):
                    if func in dangerous_imports:
                        found_dangerous.append(func)
            if found_dangerous:
                indicators.append(
                    f"⚠️ Dangerous API imports: {', '.join(f'`{f}`' for f in found_dangerous[:10])}"
                )

        # String-based
        if strings:
            cred_hints = [s for s in strings if s.category == "credential_hint"]
            if cred_hints:
                indicators.append(
                    f"⚠️ {len(cred_hints)} credential-related strings found (passwords, tokens, etc.)"
                )
            urls = [s for s in strings if s.category == "url"]
            if urls:
                indicators.append(
                    f"ℹ️ {len(urls)} URLs found — may indicate C2 communication or download"
                )
            ips = [s for s in strings if s.category == "ip"]
            if ips:
                indicators.append(
                    f"ℹ️ {len(ips)} hardcoded IP addresses found"
                )

        return indicators

    def quick_summary(self, path: str) -> str:
        """Run all analysis tools and return a summary string (for agent use)."""
        from reverse_engineering.pe_parser import PEParser
        from reverse_engineering.string_extractor import StringExtractor

        pe = PEParser().parse(path)
        strings = StringExtractor().extract(path)

        summary_parts = [f"RE Summary for {Path(path).name}:"]

        if "error" not in pe:
            summary_parts.append(
                f"PE: machine={pe.get('machine')}, dll={pe.get('is_dll')}, "
                f"sections={len(pe.get('sections', []))}, "
                f"imports from {len(pe.get('imports', []))} DLLs"
            )
            high_entropy = [s for s in pe.get("sections", []) if s.get("entropy", 0) > 6.5]
            if high_entropy:
                summary_parts.append(f"HIGH ENTROPY sections: {[s['name'] for s in high_entropy]}")

        interesting = [s for s in strings if s.category != "other"]
        summary_parts.append(f"Strings: {len(strings)} total, {len(interesting)} interesting")

        creds = [s for s in strings if s.category == "credential_hint"]
        if creds:
            summary_parts.append(f"CREDENTIAL HINTS: {len(creds)} found!")

        urls = [s for s in strings if s.category == "url"]
        if urls:
            summary_parts.append(f"URLs: {[s.value for s in urls[:5]]}")

        return "\n".join(summary_parts)
