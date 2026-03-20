"""
Rule-based risk classifier. Scores actions 0-10 before they execute.
Fast: no LLM call needed for common cases.
"""

from __future__ import annotations

import re

# (pattern, score, reason)
_RULES: list[tuple[str, int, str]] = [
    # Catastrophic — always block
    (r"(format|rm\s+-rf|deltree|rmdir.*\/s).*[cC]:", 10, "Disk format or recursive delete on system drive"),
    (r"(system32|windows\\system|boot\.ini|ntldr)", 10, "Windows system file modification"),
    (r"reg\s+(delete|add).*(HKLM|HKEY_LOCAL_MACHINE)", 10, "System registry modification"),
    (r"(bcdedit|diskpart|fdisk|mkfs)", 10, "Disk/boot configuration change"),

    # Very high risk
    (r"delete_file.*\.(exe|dll|sys)", 9, "Deleting executable or system file"),
    (r"run_command.*powershell.*(-enc|-encodedcommand|-e )", 9, "Encoded PowerShell (often malicious)"),

    # High risk — require confirmation
    (r"delete_file", 7, "File deletion"),
    (r"run_command.*(install|uninstall|setup|msiexec)", 7, "Software install/uninstall"),
    (r"write_file.*(startup|autorun|shell:startup)", 7, "Writing to startup location"),
    (r"run_command.*(reg |registry)", 7, "Registry command"),

    # Medium — confirm if threshold set low
    (r"run_command", 5, "Shell command execution"),
    (r"open_app", 4, "Opening application"),
    (r"write_file", 4, "Writing file"),

    # Low risk
    (r"click|move|scroll|drag", 1, "UI interaction"),
    (r"type|hotkey|key", 1, "Keyboard input"),
    (r"read_file|screenshot|clipboard_copy|wait", 0, "Read-only operation"),
]


def classify(action_name: str, args: dict) -> tuple[int, str]:
    """
    Returns (risk_score 0-10, reason string).
    Combines action name + serialized args for pattern matching.
    """
    combined = f"{action_name} {str(args)}".lower()
    for pattern, score, reason in _RULES:
        if re.search(pattern, combined, re.IGNORECASE):
            return score, reason
    # Default: medium-low
    return 3, "Unclassified action"
