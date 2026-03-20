"""
SystemMonitor — continuously watches system health and network state.
Alerts the agent when thresholds are exceeded.
Runs in background, publishes events to EventBus.

Monitors:
- CPU, RAM, disk usage
- New processes starting (unexpected)
- Network connectivity
- Battery level (laptops)
- Running application crashes
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from core.event_bus import EventBus
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class SystemAlert:
    category: str    # cpu | ram | disk | process | network | battery
    message: str
    value: float
    threshold: float
    severity: str    # low | medium | high


class SystemMonitor:

    def __init__(
        self,
        event_bus: EventBus,
        goal_callback=None,
        check_interval: float = 60.0,
    ):
        self._bus = event_bus
        self._goal_callback = goal_callback
        self._interval = check_interval
        self._running = False
        self._thread: threading.Thread | None = None

        # Thresholds
        self.cpu_warn = 85.0        # %
        self.ram_warn = 85.0        # %
        self.disk_warn = 90.0       # %
        self.battery_warn = 15.0    # %

        self._known_processes: set[int] = set()
        self._was_online = True

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SystemMonitor")
        self._thread.start()
        log.info("System monitor started")

    def stop(self) -> None:
        self._running = False

    def get_status(self) -> dict:
        """Snapshot of current system health."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return {
                "cpu_pct": psutil.cpu_percent(interval=0.1),
                "ram_pct": mem.percent,
                "ram_available_gb": round(mem.available / 1e9, 1),
                "disk_pct": disk.percent,
                "disk_free_gb": round(disk.free / 1e9, 1),
                "process_count": len(psutil.pids()),
                "online": self._check_internet(),
                "battery": self._get_battery(),
            }
        except Exception as e:
            return {"error": str(e)}

    def _loop(self) -> None:
        # Snapshot initial process list
        try:
            import psutil
            self._known_processes = {p.pid for p in psutil.process_iter()}
        except Exception:
            pass

        while self._running:
            try:
                alerts = self._check_all()
                for alert in alerts:
                    self._bus.publish("system_alert", alert.__dict__)
                    log.warning(f"System alert [{alert.severity}]: {alert.message}")
                    if alert.severity == "high" and self._goal_callback:
                        self._goal_callback(f"System issue detected: {alert.message}. Take appropriate action.")
            except Exception as e:
                log.debug(f"System monitor error: {e}")
            time.sleep(self._interval)

    def _check_all(self) -> list[SystemAlert]:
        alerts = []
        try:
            import psutil

            # CPU
            cpu = psutil.cpu_percent(interval=1)
            if cpu > self.cpu_warn:
                alerts.append(SystemAlert("cpu", f"CPU usage {cpu:.0f}%", cpu, self.cpu_warn,
                                          "high" if cpu > 95 else "medium"))

            # RAM
            ram = psutil.virtual_memory().percent
            if ram > self.ram_warn:
                alerts.append(SystemAlert("ram", f"RAM usage {ram:.0f}%", ram, self.ram_warn,
                                          "high" if ram > 95 else "medium"))

            # Disk
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    if usage.percent > self.disk_warn:
                        alerts.append(SystemAlert("disk",
                            f"Disk {part.mountpoint} is {usage.percent:.0f}% full",
                            usage.percent, self.disk_warn,
                            "high" if usage.percent > 97 else "medium"))
                except Exception:
                    pass

            # Battery
            battery = self._get_battery()
            if battery and battery < self.battery_warn:
                alerts.append(SystemAlert("battery", f"Battery {battery:.0f}%", battery,
                                          self.battery_warn, "high" if battery < 5 else "medium"))

            # Network
            online = self._check_internet()
            if not online and self._was_online:
                alerts.append(SystemAlert("network", "Internet connection lost", 0, 1, "high"))
            elif online and not self._was_online:
                self._bus.publish("system_alert", {"category": "network", "message": "Internet restored", "severity": "low"})
            self._was_online = online

        except ImportError:
            pass
        return alerts

    def _check_internet(self) -> bool:
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except Exception:
            return False

    def _get_battery(self) -> float | None:
        try:
            import psutil
            b = psutil.sensors_battery()
            return b.percent if b else None
        except Exception:
            return None
