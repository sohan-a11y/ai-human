"""
Mobile Companion Bridge — FastAPI server that the React Native mobile app
connects to. Provides a REST + WebSocket API for remote agent control.

Endpoints:
  GET  /mobile/status        — agent status, current goal, metrics
  POST /mobile/goal          — send a new goal to the agent
  GET  /mobile/history       — recent task history
  GET  /mobile/screenshot    — current screen as JPEG
  WS   /mobile/stream        — real-time event stream (agent thoughts, actions)
  POST /mobile/voice         — upload voice audio, returns transcription + runs goal
  GET  /mobile/notifications — pending notifications
  POST /mobile/notification/dismiss — dismiss a notification
  GET  /mobile/templates     — list task templates
  POST /mobile/template/run  — run a task template

Runs on port 8081 (separate from desktop dashboard on 8080).
Mobile app connects via local WiFi — same network as PC.
"""

from __future__ import annotations
import asyncio
import base64
import io
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from utils.logger import get_logger

log = get_logger(__name__)

_NOTIFICATIONS_FILE = Path("data/mobile_notifications.json")
_NOTIFICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)


class MobileBridge:
    """FastAPI bridge for mobile companion app."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8081,
        on_goal_received: Optional[Callable[[str], None]] = None,
        get_status_fn: Optional[Callable] = None,
        get_screenshot_fn: Optional[Callable] = None,
    ):
        self._host = host
        self._port = port
        self._on_goal = on_goal_received
        self._get_status = get_status_fn
        self._get_screenshot = get_screenshot_fn
        self._event_queues: list[asyncio.Queue] = []
        self._notifications: list[dict] = self._load_notifications()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info(f"Mobile bridge started on http://{self._host}:{self._port}")

    def push_event(self, event_type: str, data: dict) -> None:
        """Push an event to all connected mobile clients."""
        if not self._loop:
            return
        event = json.dumps({"type": event_type, "data": data, "ts": time.time()})
        for q in self._event_queues:
            try:
                self._loop.call_soon_threadsafe(q.put_nowait, event)
            except Exception:
                pass

    def push_notification(self, title: str, body: str, priority: str = "normal") -> None:
        """Add a push notification for the mobile app."""
        notif = {
            "id": f"notif_{int(time.time()*1000)}",
            "title": title,
            "body": body,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }
        self._notifications.append(notif)
        self._notifications = self._notifications[-50:]  # keep last 50
        self._save_notifications()
        self.push_event("notification", notif)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_server())

    async def _start_server(self) -> None:
        try:
            from fastapi import FastAPI, WebSocket, WebSocketDisconnect
            from fastapi.responses import JSONResponse, Response
            import uvicorn
        except ImportError:
            log.error("FastAPI/uvicorn not installed: pip install fastapi uvicorn")
            return

        import os, secrets as _secrets
        app = FastAPI(title="AI Human Mobile Bridge")
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi import Depends, HTTPException, status as _status
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

        # SECURITY: localhost CORS only
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost", "http://127.0.0.1"],
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

        _mobile_token = os.environ.get("MOBILE_API_TOKEN", "")
        _bearer = HTTPBearer(auto_error=False)

        async def _verify(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
            if _mobile_token:
                if not credentials or not _secrets.compare_digest(credentials.credentials, _mobile_token):
                    raise HTTPException(status_code=_status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        @app.get("/mobile/status")
        async def get_status():
            status = {}
            if self._get_status:
                try:
                    status = self._get_status() or {}
                except Exception:
                    pass
            return JSONResponse({
                "online": True,
                "timestamp": datetime.now().isoformat(),
                **status,
            })

        @app.post("/mobile/goal")
        async def send_goal(body: dict):
            goal = body.get("goal", "").strip()
            if not goal:
                return JSONResponse({"error": "Empty goal"}, status_code=400)
            if self._on_goal:
                threading.Thread(target=self._on_goal, args=(goal,), daemon=True).start()
                return JSONResponse({"status": "accepted", "goal": goal})
            return JSONResponse({"error": "Agent not connected"}, status_code=503)

        @app.get("/mobile/screenshot")
        async def get_screenshot():
            if self._get_screenshot:
                try:
                    img = self._get_screenshot()
                    if img:
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=70)
                        return Response(
                            content=buf.getvalue(),
                            media_type="image/jpeg",
                        )
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            return JSONResponse({"error": "Screenshot not available"}, status_code=503)

        @app.get("/mobile/screenshot/base64")
        async def get_screenshot_b64():
            if self._get_screenshot:
                try:
                    img = self._get_screenshot()
                    if img:
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=60)
                        encoded = base64.b64encode(buf.getvalue()).decode()
                        return JSONResponse({"image": encoded, "format": "jpeg"})
                except Exception as e:
                    return JSONResponse({"error": str(e)}, status_code=500)
            return JSONResponse({"error": "Screenshot not available"}, status_code=503)

        @app.get("/mobile/notifications")
        async def get_notifications():
            return JSONResponse({"notifications": self._notifications})

        @app.post("/mobile/notification/dismiss")
        async def dismiss_notification(body: dict):
            notif_id = body.get("id")
            for n in self._notifications:
                if n["id"] == notif_id:
                    n["read"] = True
            self._save_notifications()
            return JSONResponse({"status": "dismissed"})

        @app.post("/mobile/voice")
        async def process_voice(body: dict):
            """Receive base64-encoded audio, transcribe, run as goal."""
            audio_b64 = body.get("audio")
            if not audio_b64:
                return JSONResponse({"error": "No audio data"}, status_code=400)
            try:
                audio_bytes = base64.b64decode(audio_b64)
                import tempfile
                # SECURITY: use context manager + explicit delete to avoid race condition
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir) / "voice.wav"
                    tmp_path.write_bytes(audio_bytes)
                    text = self._transcribe(str(tmp_path))

                if text and self._on_goal:
                    threading.Thread(target=self._on_goal, args=(text,), daemon=True).start()
                    return JSONResponse({"transcription": text, "status": "running"})
                return JSONResponse({"transcription": text or "", "status": "no_action"})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.get("/mobile/templates")
        async def list_templates():
            try:
                from core.task_templates import TaskTemplateLibrary
                lib = TaskTemplateLibrary()
                templates = [
                    {
                        "id": t.id,
                        "name": t.name,
                        "description": t.description,
                        "category": t.category,
                        "estimated_minutes": t.estimated_minutes,
                        "parameters": t.parameters,
                        "tags": t.tags,
                    }
                    for t in lib.list_all()
                ]
                return JSONResponse({"templates": templates})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.post("/mobile/template/run")
        async def run_template(body: dict):
            template_id = body.get("template_id")
            params = body.get("params", {})
            try:
                from core.task_templates import TaskTemplateLibrary
                lib = TaskTemplateLibrary()
                goal = lib.instantiate(template_id, **params)
                if not goal:
                    return JSONResponse({"error": f"Template '{template_id}' not found"}, status_code=404)
                if self._on_goal:
                    threading.Thread(target=self._on_goal, args=(goal,), daemon=True).start()
                    return JSONResponse({"status": "accepted", "goal": goal[:200]})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.websocket("/mobile/stream")
        async def websocket_stream(ws: WebSocket):
            await ws.accept()
            q: asyncio.Queue = asyncio.Queue()
            self._event_queues.append(q)
            log.info("Mobile app connected to event stream")
            try:
                while True:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                    await ws.send_text(event)
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "ping"}))
            except WebSocketDisconnect:
                pass
            finally:
                self._event_queues.remove(q)
                log.info("Mobile app disconnected from event stream")

        config = uvicorn.Config(app, host=self._host, port=self._port, log_level="warning")
        server = uvicorn.Server(config)
        await server.serve()

    def _transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text."""
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path, language="en")
            return " ".join(s.text for s in segments).strip()
        except ImportError:
            pass
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = r.record(source)
            return r.recognize_google(audio)
        except Exception:
            pass
        return ""

    def _load_notifications(self) -> list:
        if _NOTIFICATIONS_FILE.exists():
            try:
                return json.loads(_NOTIFICATIONS_FILE.read_text())
            except Exception:
                pass
        return []

    def _save_notifications(self) -> None:
        try:
            _NOTIFICATIONS_FILE.write_text(json.dumps(self._notifications, indent=2))
        except Exception:
            pass


def get_connection_info() -> str:
    """Return instructions for connecting the mobile app."""
    import socket
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "YOUR_PC_IP"

    return f"""
Mobile App Connection Info
==========================
PC IP Address: {ip}
Port: 8081

In the mobile app, enter server URL:
  http://{ip}:8081

Make sure your phone and PC are on the same WiFi network.
"""
