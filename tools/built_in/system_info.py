"""Returns system info: OS, CPU, RAM, disk, processes."""

from __future__ import annotations

from tools.base_tool import BaseTool


class SystemInfoTool(BaseTool):
    name = "system_info"
    description = "Get information about the current system: OS, CPU, RAM, disk usage, running processes."
    parameters = {"type": "object", "properties": {}}

    def run(self, **kwargs) -> str:
        try:
            import platform, psutil
            info = {
                "os": f"{platform.system()} {platform.release()}",
                "cpu": platform.processor(),
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 1),
                "ram_used_pct": psutil.virtual_memory().percent,
                "disk_free_gb": round(psutil.disk_usage("/").free / 1e9, 1),
                "top_processes": [
                    {"name": p.info["name"], "cpu": p.info["cpu_percent"]}
                    for p in sorted(
                        psutil.process_iter(["name", "cpu_percent"]),
                        key=lambda p: p.info["cpu_percent"] or 0,
                        reverse=True,
                    )[:5]
                ],
            }
            import json
            return json.dumps(info, indent=2)
        except Exception as e:
            return f"Error: {e}"
