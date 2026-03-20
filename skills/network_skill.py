"""Network skill pack — ping, port scan, DNS lookup, download, HTTP requests."""

import subprocess
from tools.base_tool import BaseTool


class PingTool(BaseTool):
    name = "ping"
    description = "Ping a host to check connectivity and latency."
    parameters = {"type": "object", "properties": {
        "host": {"type": "string", "description": "Hostname or IP address"},
        "count": {"type": "integer", "default": 4},
    }, "required": ["host"]}

    def run(self, host: str, count: int = 4) -> str:
        try:
            result = subprocess.run(
                ["ping", "-n", str(min(count, 10)), host],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout[:3000]
        except subprocess.TimeoutExpired:
            return f"Ping to {host} timed out."
        except Exception as e:
            return f"Error: {e}"


class PortScanTool(BaseTool):
    name = "port_scan"
    description = "Scan common ports on a host to check which are open."
    parameters = {"type": "object", "properties": {
        "host": {"type": "string"},
        "ports": {"type": "string", "default": "21,22,23,25,53,80,443,3306,3389,5432,8080,8443",
                  "description": "Comma-separated ports to scan"},
        "timeout": {"type": "number", "default": 1.0},
    }, "required": ["host"]}

    def run(self, host: str, ports: str = "21,22,23,25,53,80,443,3306,3389,5432,8080,8443",
            timeout: float = 1.0) -> str:
        import socket
        port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
        results = []
        for port in port_list:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                status = "OPEN" if result == 0 else "closed"
                if status == "OPEN":
                    results.append(f"  Port {port}: {status}")
                sock.close()
            except Exception:
                pass
        if not results:
            return f"No open ports found on {host}"
        return f"Open ports on {host}:\n" + "\n".join(results)


class DNSLookupTool(BaseTool):
    name = "dns_lookup"
    description = "Perform DNS lookup for a hostname. Returns IP addresses and records."
    parameters = {"type": "object", "properties": {
        "hostname": {"type": "string"},
        "record_type": {"type": "string", "default": "A", "description": "A, AAAA, MX, NS, TXT, CNAME"},
    }, "required": ["hostname"]}

    def run(self, hostname: str, record_type: str = "A") -> str:
        import socket
        try:
            # Basic A record lookup
            if record_type.upper() == "A":
                ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
                unique_ips = list(set(ip[4][0] for ip in ips))
                return f"{hostname} → {', '.join(unique_ips)}"
            elif record_type.upper() == "AAAA":
                ips = socket.getaddrinfo(hostname, None, socket.AF_INET6)
                unique_ips = list(set(ip[4][0] for ip in ips))
                return f"{hostname} (IPv6) → {', '.join(unique_ips)}"
            else:
                # Use nslookup for other record types
                result = subprocess.run(
                    ["nslookup", "-type=" + record_type, hostname],
                    capture_output=True, text=True, timeout=10
                )
                return result.stdout[:2000]
        except socket.gaierror:
            return f"DNS lookup failed for {hostname}"
        except Exception as e:
            return f"Error: {e}"


class DownloadFileTool(BaseTool):
    name = "download_file"
    description = "Download a file from a URL and save it locally."
    parameters = {"type": "object", "properties": {
        "url": {"type": "string"},
        "save_path": {"type": "string", "description": "Local path to save the file"},
        "timeout": {"type": "integer", "default": 60},
    }, "required": ["url", "save_path"]}

    def run(self, url: str, save_path: str, timeout: int = 60) -> str:
        try:
            import requests
            from pathlib import Path
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            total = 0
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total += len(chunk)
            size_mb = total / (1024 * 1024)
            return f"Downloaded {size_mb:.1f} MB to {save_path}"
        except Exception as e:
            return f"Error: {e}"


class HTTPRequestTool(BaseTool):
    name = "http_request"
    description = "Make an HTTP request (GET, POST, PUT, DELETE) and return the response."
    parameters = {"type": "object", "properties": {
        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"], "default": "GET"},
        "url": {"type": "string"},
        "headers": {"type": "string", "default": "", "description": "JSON string of headers"},
        "body": {"type": "string", "default": "", "description": "Request body (JSON string for POST/PUT)"},
        "timeout": {"type": "integer", "default": 30},
    }, "required": ["url"]}

    def run(self, url: str, method: str = "GET", headers: str = "",
            body: str = "", timeout: int = 30) -> str:
        import json
        try:
            import requests
            hdrs = json.loads(headers) if headers else {}
            kwargs = {"headers": hdrs, "timeout": timeout}
            if body and method in ("POST", "PUT", "PATCH"):
                try:
                    kwargs["json"] = json.loads(body)
                except json.JSONDecodeError:
                    kwargs["data"] = body

            resp = requests.request(method, url, **kwargs)
            result = f"Status: {resp.status_code}\n"
            content_type = resp.headers.get("content-type", "")
            if "json" in content_type:
                try:
                    result += json.dumps(resp.json(), indent=2)[:3000]
                except Exception:
                    result += resp.text[:3000]
            else:
                result += resp.text[:3000]
            return result
        except Exception as e:
            return f"Error: {e}"


class NetworkInfoTool(BaseTool):
    name = "network_info"
    description = "Show local network configuration — IP addresses, adapters, routes."
    parameters = {"type": "object", "properties": {}}

    def run(self) -> str:
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout[:5000]
        except Exception as e:
            return f"Error: {e}"
