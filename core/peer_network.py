"""
Peer AI Network — allows multiple AI Human instances to discover each other
on the local network, share workflows, exchange knowledge, and distribute tasks.

Architecture:
  - Each instance runs a FastAPI server on port 8090 (configurable)
  - Discovery uses mDNS/Bonjour (zeroconf library) OR manual IP list
  - Peers sync: learned skills, successful workflows, task templates
  - Tasks can be delegated to less-busy peers
  - Knowledge sharing: automatically push new learnings to all peers

Protocol:
  POST /peer/knowledge  — push a learned fact
  POST /peer/workflow   — share a successful workflow
  GET  /peer/status     — get peer status (CPU, RAM, busy, capabilities)
  POST /peer/delegate   — delegate a task to this peer
  GET  /peer/discover   — list of known peers this peer knows about
"""

from __future__ import annotations
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from utils.logger import get_logger

log = get_logger(__name__)

_PEERS_FILE = Path("data/known_peers.json")
_DEFAULT_PORT = 8090


class PeerInfo:
    def __init__(self, host: str, port: int, name: str = ""):
        self.host = host
        self.port = port
        self.name = name or f"ai_human@{host}"
        self.last_seen: float = 0.0
        self.is_busy: bool = False
        self.cpu_percent: float = 0.0
        self.capabilities: list[str] = []

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> dict:
        return {
            "host": self.host, "port": self.port, "name": self.name,
            "last_seen": self.last_seen, "capabilities": self.capabilities,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PeerInfo":
        p = cls(d["host"], d["port"], d.get("name", ""))
        p.last_seen = d.get("last_seen", 0)
        p.capabilities = d.get("capabilities", [])
        return p


class PeerNetwork:
    """Manage connections to peer AI Human instances."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = _DEFAULT_PORT,
        agent_name: str = "AI Human",
        on_task_received: Optional[Callable] = None,
        on_knowledge_received: Optional[Callable] = None,
    ):
        self._host = host
        self._port = port
        self._name = agent_name
        self._on_task = on_task_received
        self._on_knowledge = on_knowledge_received
        self._peers: dict[str, PeerInfo] = {}
        self._server_thread: Optional[threading.Thread] = None
        self._discovery_thread: Optional[threading.Thread] = None
        self._running = False
        self._load_known_peers()

    def start(self) -> None:
        self._running = True
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        self._discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self._discovery_thread.start()
        log.info(f"Peer network started on port {self._port}")

    def stop(self) -> None:
        self._running = False

    def add_peer(self, host: str, port: int = _DEFAULT_PORT) -> bool:
        """Manually add a peer by IP/host."""
        key = f"{host}:{port}"
        if key not in self._peers:
            self._peers[key] = PeerInfo(host, port)
        return self._ping_peer(self._peers[key])

    def list_peers(self) -> list[dict]:
        return [p.to_dict() for p in self._peers.values()]

    def get_available_peer(self) -> Optional[PeerInfo]:
        """Return the least-busy available peer for task delegation."""
        available = [
            p for p in self._peers.values()
            if not p.is_busy and time.time() - p.last_seen < 60
        ]
        if not available:
            return None
        return min(available, key=lambda p: p.cpu_percent)

    # ── Knowledge Sharing ──────────────────────────────────────────────────────

    def broadcast_knowledge(self, fact: str, category: str = "general") -> int:
        """Push a learned fact to all known peers. Returns number of peers reached."""
        payload = {
            "fact": fact,
            "category": category,
            "from": self._name,
            "timestamp": datetime.now().isoformat(),
        }
        count = 0
        for peer in list(self._peers.values()):
            if self._post_to_peer(peer, "/peer/knowledge", payload):
                count += 1
        return count

    def broadcast_workflow(self, workflow_name: str, workflow_data: dict) -> int:
        """Share a successful workflow with all peers."""
        payload = {
            "name": workflow_name,
            "workflow": workflow_data,
            "from": self._name,
            "timestamp": datetime.now().isoformat(),
        }
        count = 0
        for peer in list(self._peers.values()):
            if self._post_to_peer(peer, "/peer/workflow", payload):
                count += 1
        return count

    def delegate_task(self, goal: str, peer: Optional[PeerInfo] = None) -> dict:
        """Delegate a goal to a peer. Auto-selects least busy if peer not specified."""
        target = peer or self.get_available_peer()
        if not target:
            return {"success": False, "error": "No available peers"}

        payload = {
            "goal": goal,
            "from": self._name,
            "timestamp": datetime.now().isoformat(),
        }
        success = self._post_to_peer(target, "/peer/delegate", payload)
        if success:
            return {"success": True, "peer": target.name}
        return {"success": False, "error": f"Failed to reach peer {target.name}"}

    def sync_from_peer(self, peer: PeerInfo) -> dict:
        """Pull latest knowledge and workflows from a peer."""
        try:
            import requests
            r = requests.get(f"{peer.base_url}/peer/knowledge_dump", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if self._on_knowledge:
                    for fact in data.get("facts", []):
                        self._on_knowledge(fact["content"], fact.get("category", "peer_sync"))
                return {"facts": len(data.get("facts", [])), "peer": peer.name}
        except Exception as e:
            log.debug(f"Sync from peer {peer.name} failed: {e}")
        return {"facts": 0, "peer": peer.name}

    # ── mDNS Discovery ─────────────────────────────────────────────────────────

    def _discovery_loop(self) -> None:
        """Discover peers via mDNS (zeroconf) or periodic pinging of known peers."""
        # Try zeroconf first
        if self._try_zeroconf_register():
            log.info("mDNS peer discovery active")
        else:
            log.info("mDNS not available — using manual peer list only")

        # Periodically ping known peers to check availability
        while self._running:
            for peer in list(self._peers.values()):
                self._ping_peer(peer)
            time.sleep(30)

    def _try_zeroconf_register(self) -> bool:
        try:
            from zeroconf import ServiceInfo, Zeroconf
            import socket

            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            info = ServiceInfo(
                "_ai-human._tcp.local.",
                f"{self._name}._ai-human._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=self._port,
                properties={"name": self._name, "version": "1.0"},
            )
            zc = Zeroconf()
            zc.register_service(info)

            # Also browse for other instances
            from zeroconf import ServiceBrowser

            class Listener:
                def add_service(self_inner, zc_inner, type_, name):
                    service_info = zc_inner.get_service_info(type_, name)
                    if service_info:
                        ip = socket.inet_ntoa(service_info.addresses[0])
                        port = service_info.port
                        peer_name = service_info.properties.get(b"name", b"unknown").decode()
                        if ip != local_ip:
                            key = f"{ip}:{port}"
                            if key not in self._peers:
                                self._peers[key] = PeerInfo(ip, port, peer_name)
                                log.info(f"Discovered peer: {peer_name} @ {ip}:{port}")
                                self._save_known_peers()

                def remove_service(self_inner, *args): pass
                def update_service(self_inner, *args): pass

            ServiceBrowser(zc, "_ai-human._tcp.local.", Listener())
            return True
        except ImportError:
            return False
        except Exception as e:
            log.debug(f"zeroconf failed: {e}")
            return False

    # ── FastAPI Server ─────────────────────────────────────────────────────────

    def _run_server(self) -> None:
        try:
            from fastapi import FastAPI
            import uvicorn

            app = FastAPI(title="AI Human Peer API")

            @app.get("/peer/status")
            def status():
                import psutil
                return {
                    "name": self._name,
                    "busy": False,
                    "cpu": psutil.cpu_percent() if self._safe_import("psutil") else 0,
                    "ram": psutil.virtual_memory().percent if self._safe_import("psutil") else 0,
                    "peers_known": len(self._peers),
                    "timestamp": datetime.now().isoformat(),
                }

            @app.post("/peer/knowledge")
            def receive_knowledge(data: dict):
                fact = data.get("fact", "")
                category = data.get("category", "peer")
                from_peer = data.get("from", "unknown")
                log.info(f"Knowledge received from {from_peer}: {fact[:80]}")
                if self._on_knowledge:
                    self._on_knowledge(f"[From {from_peer}] {fact}", category)
                return {"status": "received"}

            @app.post("/peer/workflow")
            def receive_workflow(data: dict):
                log.info(f"Workflow received from {data.get('from', 'unknown')}: {data.get('name', '?')}")
                # Store workflow locally
                wf_dir = Path("data/peer_workflows")
                wf_dir.mkdir(parents=True, exist_ok=True)
                wf_file = wf_dir / f"{data.get('name', 'unknown')}.json"
                wf_file.write_text(json.dumps(data, indent=2))
                return {"status": "received"}

            @app.post("/peer/delegate")
            def receive_task(data: dict):
                goal = data.get("goal", "")
                from_peer = data.get("from", "unknown")
                log.info(f"Task delegated from {from_peer}: {goal[:100]}")
                if self._on_task:
                    threading.Thread(target=self._on_task, args=(goal,), daemon=True).start()
                    return {"status": "accepted", "message": "Task is being processed"}
                return {"status": "rejected", "message": "No task handler configured"}

            @app.get("/peer/discover")
            def get_peers():
                return {"peers": [p.to_dict() for p in self._peers.values()]}

            @app.get("/peer/knowledge_dump")
            def knowledge_dump():
                # Return recent learnings (from semantic memory if available)
                return {"facts": [], "name": self._name}

            uvicorn.run(app, host=self._host, port=self._port, log_level="warning")
        except ImportError:
            log.warning("FastAPI/uvicorn not available — peer network server disabled")
        except Exception as e:
            log.error(f"Peer server error: {e}")

    # ── Utilities ──────────────────────────────────────────────────────────────

    def _ping_peer(self, peer: PeerInfo) -> bool:
        try:
            import requests
            r = requests.get(f"{peer.base_url}/peer/status", timeout=5)
            if r.status_code == 200:
                data = r.json()
                peer.last_seen = time.time()
                peer.is_busy = data.get("busy", False)
                peer.cpu_percent = data.get("cpu", 0)
                peer.name = data.get("name", peer.name)
                return True
        except Exception:
            pass
        return False

    def _post_to_peer(self, peer: PeerInfo, endpoint: str, payload: dict) -> bool:
        try:
            import requests
            r = requests.post(f"{peer.base_url}{endpoint}", json=payload, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def _safe_import(self, module: str) -> bool:
        try:
            __import__(module)
            return True
        except ImportError:
            return False

    def _load_known_peers(self) -> None:
        if not _PEERS_FILE.exists():
            return
        try:
            data = json.loads(_PEERS_FILE.read_text())
            for item in data:
                peer = PeerInfo.from_dict(item)
                self._peers[f"{peer.host}:{peer.port}"] = peer
        except Exception:
            pass

    def _save_known_peers(self) -> None:
        try:
            data = [p.to_dict() for p in self._peers.values()]
            _PEERS_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass
