"""
SafetyBroker — sits between the agent's reasoning output and ActionExecutor.
Nothing executes without passing through here first.
"""

from __future__ import annotations

from config import Config
from safety.risk_classifier import classify
from safety.audit_log import AuditLog
from utils.logger import get_logger

log = get_logger(__name__)


class SafetyBlock(Exception):
    """Raised when an action is hard-blocked."""


class SafetyBroker:

    def __init__(self, config: Config, audit: AuditLog):
        self._confirm_threshold = config.safety_confirm_threshold
        self._block_threshold = config.safety_block_threshold
        self._audit = audit

    def check(self, action_name: str, args: dict) -> bool:
        """
        Returns True if action is allowed.
        Raises SafetyBlock if action is blocked.
        Shows confirmation dialog if action needs approval.
        """
        score, reason = classify(action_name, args)
        log.debug(f"Safety: {action_name} | score={score} | {reason}")

        self._audit.log(action_name, args, score, reason)

        if score >= self._block_threshold:
            msg = f"BLOCKED (score {score}/10): {reason}\nAction: {action_name}\nArgs: {args}"
            log.warning(msg)
            raise SafetyBlock(msg)

        if score >= self._confirm_threshold:
            approved = self._show_confirmation(action_name, args, score, reason)
            if not approved:
                raise SafetyBlock(f"User denied action: {action_name}")
            return True

        return True

    def _show_confirmation(self, action_name: str, args: dict, score: int, reason: str) -> bool:
        """Show a tkinter modal dialog asking user to approve or deny."""
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            msg = (
                f"AI wants to perform a potentially risky action.\n\n"
                f"Action : {action_name}\n"
                f"Args   : {args}\n"
                f"Risk   : {score}/10 — {reason}\n\n"
                f"Allow this?"
            )
            result = messagebox.askyesno("AI Human — Safety Confirmation", msg, parent=root)
            root.destroy()
            return result
        except Exception as e:
            log.error(f"Confirmation dialog failed: {e}")
            return False  # Deny if dialog can't open
