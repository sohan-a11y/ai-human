"""Task Manager skill pack — process management, CPU/memory monitoring."""

from tools.base_tool import BaseTool


class ProcessListTool(BaseTool):
    name = "process_list"
    description = "List running processes with CPU and memory usage. Can filter by name."
    parameters = {"type": "object", "properties": {
        "filter_name": {"type": "string", "default": "", "description": "Filter by process name"},
        "sort_by": {"type": "string", "enum": ["cpu", "memory", "name", "pid"], "default": "memory"},
        "top_n": {"type": "integer", "default": 20},
    }, "required": []}

    def run(self, filter_name: str = "", sort_by: str = "memory", top_n: int = 20) -> str:
        try:
            import psutil
            procs = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
                try:
                    info = proc.info
                    if filter_name and filter_name.lower() not in info["name"].lower():
                        continue
                    mem_mb = info["memory_info"].rss / (1024 * 1024) if info["memory_info"] else 0
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu": info["cpu_percent"] or 0,
                        "mem_mb": mem_mb,
                        "status": info["status"],
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            key_map = {"cpu": "cpu", "memory": "mem_mb", "name": "name", "pid": "pid"}
            procs.sort(key=lambda p: p[key_map.get(sort_by, "mem_mb")], reverse=sort_by != "name")

            lines = [f"{'PID':>7} | {'Name':<30} | {'CPU%':>6} | {'Mem MB':>8} | Status"]
            lines.append("-" * 75)
            for p in procs[:top_n]:
                lines.append(f"{p['pid']:>7} | {p['name']:<30} | {p['cpu']:>6.1f} | {p['mem_mb']:>8.1f} | {p['status']}")
            return "\n".join(lines)
        except ImportError:
            return "Requires: pip install psutil"
        except Exception as e:
            return f"Error: {e}"


class ProcessKillTool(BaseTool):
    name = "process_kill"
    description = "Kill a process by PID or name. Use with caution."
    parameters = {"type": "object", "properties": {
        "pid": {"type": "integer", "default": 0, "description": "Process ID to kill"},
        "name": {"type": "string", "default": "", "description": "Process name to kill (kills all matching)"},
        "force": {"type": "boolean", "default": False},
    }, "required": []}

    def run(self, pid: int = 0, name: str = "", force: bool = False) -> str:
        try:
            import psutil
            killed = []
            if pid:
                proc = psutil.Process(pid)
                pname = proc.name()
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                killed.append(f"{pname} (PID {pid})")
            elif name:
                for proc in psutil.process_iter(["pid", "name"]):
                    if name.lower() in proc.info["name"].lower():
                        try:
                            if force:
                                proc.kill()
                            else:
                                proc.terminate()
                            killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            else:
                return "Provide either pid or name."

            if killed:
                return f"{'Killed' if force else 'Terminated'}: " + ", ".join(killed)
            return "No matching processes found."
        except psutil.NoSuchProcess:
            return f"Process {pid} not found."
        except psutil.AccessDenied:
            return f"Access denied. May need admin privileges."
        except Exception as e:
            return f"Error: {e}"


class SystemResourcesTool(BaseTool):
    name = "system_resources"
    description = "Show current system resource usage — CPU, RAM, disk, network."
    parameters = {"type": "object", "properties": {}}

    def run(self) -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            disk = psutil.disk_usage("/")

            lines = [
                f"CPU: {cpu}% ({psutil.cpu_count()} cores)",
                f"CPU Freq: {cpu_freq.current:.0f} MHz" if cpu_freq else "",
                f"RAM: {mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB ({mem.percent}%)",
                f"Swap: {swap.used / (1024**3):.1f} / {swap.total / (1024**3):.1f} GB ({swap.percent}%)",
                f"Disk: {disk.used / (1024**3):.1f} / {disk.total / (1024**3):.1f} GB ({disk.percent}%)",
            ]

            # Network I/O
            net = psutil.net_io_counters()
            lines.append(f"Network: Sent {net.bytes_sent / (1024**2):.1f} MB | Recv {net.bytes_recv / (1024**2):.1f} MB")

            # Top 5 memory consumers
            procs = []
            for proc in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    mem_mb = proc.info["memory_info"].rss / (1024**2) if proc.info["memory_info"] else 0
                    procs.append((proc.info["name"], mem_mb))
                except Exception:
                    pass
            procs.sort(key=lambda x: x[1], reverse=True)
            lines.append("\nTop 5 memory consumers:")
            for name, mb in procs[:5]:
                lines.append(f"  {name}: {mb:.1f} MB")

            return "\n".join(l for l in lines if l)
        except ImportError:
            return "Requires: pip install psutil"
        except Exception as e:
            return f"Error: {e}"


class StartProcessTool(BaseTool):
    name = "start_process"
    description = "Start a new process/application."
    parameters = {"type": "object", "properties": {
        "command": {"type": "string", "description": "Command or path to execute"},
        "args": {"type": "string", "default": "", "description": "Space-separated arguments"},
        "working_dir": {"type": "string", "default": ""},
    }, "required": ["command"]}

    def run(self, command: str, args: str = "", working_dir: str = "") -> str:
        import subprocess
        import shlex
        try:
            cmd_parts = [command] + (shlex.split(args) if args else [])
            kwargs = {"start_new_session": True}
            if working_dir:
                kwargs["cwd"] = working_dir
            proc = subprocess.Popen(cmd_parts, **kwargs)
            return f"Started process: {command} (PID {proc.pid})"
        except Exception as e:
            return f"Error starting process: {e}"
