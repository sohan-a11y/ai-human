"""
Launcher — the persistent watchdog process.

This is the ONLY thing you run. It starts main.py and monitors it forever.

Responsibilities:
  - Start the agent (main.py)
  - Watch for crash signals
  - Handle restart requests from SelfUpdater
  - Roll back to previous version if new version crashes on startup
  - Restart automatically after any unexpected crash

Usage:
  python launcher.py
  python launcher.py --goal "open calculator"
  python launcher.py --no-ui
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
SIGNAL_FILE = ROOT / "data" / "restart_signal.json"
VERSIONS_DIR = ROOT / "versions"

RESTART_DELAY = 3        # seconds between crash and restart
MAX_FAST_CRASHES = 5     # crashes within 60s = "broken"
STARTUP_GRACE_PERIOD = 60  # seconds to detect startup failure


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [LAUNCHER] {msg}", flush=True)


def run_agent(extra_args: list[str] = []) -> subprocess.Popen:
    cmd = [sys.executable, str(ROOT / "main.py")] + extra_args
    log(f"Starting agent: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(ROOT))


def read_signal() -> dict | None:
    if SIGNAL_FILE.exists():
        try:
            data = json.loads(SIGNAL_FILE.read_text())
            SIGNAL_FILE.unlink()  # consume it
            return data
        except Exception:
            pass
    return None


def rollback(signal: dict) -> bool:
    prev = signal.get("previous_version")
    if not prev:
        log("No previous version in signal — cannot rollback")
        return False

    # SECURITY: validate version ID is safe (alphanumeric + underscore only)
    # before passing to subprocess — prevents code injection via version string
    import re
    if not re.match(r"^[a-zA-Z0-9_]+$", str(prev)):
        log(f"SECURITY: Unsafe version ID rejected: {prev!r}")
        return False

    log(f"ROLLING BACK to {prev}")
    try:
        # Pass version as argument, not string interpolation in code
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; from core.version_manager import VersionManager; VersionManager().rollback(sys.argv[1])",
             str(prev)],
            cwd=str(ROOT), timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        log(f"Rollback failed: {e}")
        return False


def main():
    extra_args = sys.argv[1:]
    log("AI Human Launcher starting")
    log(f"Root: {ROOT}")

    crash_times: list[float] = []
    last_signal: dict | None = None

    while True:
        proc = run_agent(extra_args)
        start_time = time.time()

        # Monitor the running process
        while True:
            time.sleep(1)

            # Check for restart/update signal
            signal = read_signal()
            if signal:
                action = signal.get("action")
                log(f"Signal received: {action}")

                if action == "restart":
                    last_signal = signal
                    wait = signal.get("wait_seconds", 5)
                    log(f"Self-update restart requested. Waiting {wait}s then restarting...")

                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()

                    log(f"Waiting {wait} seconds before restart...")
                    time.sleep(wait)
                    break  # restart outer loop

                elif action == "shutdown":
                    log("Shutdown requested. Stopping.")
                    proc.terminate()
                    return

            # Check if agent process ended
            ret = proc.poll()
            if ret is not None:
                elapsed = time.time() - start_time
                log(f"Agent exited with code {ret} after {elapsed:.0f}s")

                # If it crashed very fast (startup failure) and we just did a self-update
                if last_signal and elapsed < STARTUP_GRACE_PERIOD:
                    log("New version crashed on startup! Rolling back...")
                    if rollback(last_signal):
                        log("Rollback successful. Restarting previous version.")
                    else:
                        log("Rollback failed. Starting whatever is there now.")
                    last_signal = None
                    time.sleep(RESTART_DELAY)
                    break  # restart outer loop

                else:
                    last_signal = None

                # Track crash frequency
                now = time.time()
                crash_times.append(now)
                crash_times = [t for t in crash_times if now - t < 60]

                if len(crash_times) >= MAX_FAST_CRASHES:
                    log(f"WARNING: {MAX_FAST_CRASHES} crashes in 60s. Waiting 60s before retry.")
                    time.sleep(60)
                    crash_times = []
                else:
                    log(f"Restarting in {RESTART_DELAY}s...")
                    time.sleep(RESTART_DELAY)

                break  # restart outer loop


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Launcher stopped by user.")
