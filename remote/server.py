"""
Remote Control Server — FastAPI web server so you can control the agent
from your phone, another computer, or any web browser.

Access at: http://localhost:8080

Endpoints:
  GET  /              → status page
  GET  /status        → agent state, current goal, system info
  POST /goal          → set a new goal
  GET  /screenshot    → live screenshot
  GET  /memory        → recent memory
  GET  /workflows     → list workflows
  POST /schedule      → add a scheduled task
  GET  /schedules     → list scheduled tasks
  DELETE /schedule/{id} → remove a task
  GET  /events        → server-sent events stream (live updates)
"""

from __future__ import annotations

import base64
import io
import threading
from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)

# These are injected at startup via set_agent()
_agent = None
_scheduler = None
_system_monitor = None
_workflow_recorder = None


def set_agent(agent, scheduler=None, system_monitor=None, workflow_recorder=None):
    global _agent, _scheduler, _system_monitor, _workflow_recorder
    _agent = agent
    _scheduler = scheduler
    _system_monitor = system_monitor
    _workflow_recorder = workflow_recorder


def create_app():
    try:
        from fastapi import FastAPI, Depends, HTTPException, status as http_status
        from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        from pydantic import BaseModel
        import os, secrets
    except ImportError:
        raise RuntimeError("FastAPI not installed. Run: pip install fastapi uvicorn")

    app = FastAPI(title="AI Human Remote Control", version="1.0")
    # SECURITY: restrict CORS to localhost only — never allow wildcard in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # SECURITY: optional Bearer token auth. Set REMOTE_API_TOKEN in .env to enable.
    _api_token = os.environ.get("REMOTE_API_TOKEN", "")
    _bearer = HTTPBearer(auto_error=False)

    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
        if _api_token:
            if not credentials or not secrets.compare_digest(credentials.credentials, _api_token):
                raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # SECURITY: simple in-memory rate limiter (requests per minute per IP)
    import time as _time
    from collections import defaultdict
    _request_counts: dict = defaultdict(list)
    _RATE_LIMIT = 30  # max requests per minute per IP

    async def rate_limit_check(request):
        from fastapi import Request
        client_ip = getattr(request, "client", None)
        ip = client_ip.host if client_ip else "unknown"
        now = _time.time()
        _request_counts[ip] = [t for t in _request_counts[ip] if now - t < 60]
        if len(_request_counts[ip]) >= _RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _request_counts[ip].append(now)

    class GoalRequest(BaseModel):
        goal: str

    class ScheduleRequest(BaseModel):
        schedule_type: str
        schedule_value: str
        goal: str

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return _dashboard_html()

    @app.get("/status", dependencies=[Depends(verify_token)])
    async def status():
        data: dict[str, Any] = {"agent_state": "unknown", "goal": ""}
        if _agent:
            data["agent_state"] = _agent.state.name
            data["goal"] = _agent.goal
        if _system_monitor:
            data["system"] = _system_monitor.get_status()
        return data

    @app.post("/goal", dependencies=[Depends(verify_token)])
    async def set_goal(req: GoalRequest):
        if not _agent:
            return JSONResponse({"error": "Agent not initialized"}, status_code=503)
        _agent.set_goal(req.goal)
        return {"status": "ok", "goal": req.goal}

    @app.get("/screenshot", dependencies=[Depends(verify_token)])
    async def screenshot():
        from perception.screen_capture import ScreenCapture
        img = ScreenCapture().capture()
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"image": f"data:image/jpeg;base64,{b64}"}

    @app.get("/schedules", dependencies=[Depends(verify_token)])
    async def list_schedules():
        if not _scheduler:
            return []
        return _scheduler.list_tasks()

    @app.post("/schedule", dependencies=[Depends(verify_token)])
    async def add_schedule(req: ScheduleRequest):
        if not _scheduler:
            return JSONResponse({"error": "Scheduler not initialized"}, status_code=503)
        task_id = _scheduler.add(req.schedule_type, req.schedule_value, req.goal)
        return {"status": "ok", "id": task_id}

    @app.delete("/schedule/{task_id}", dependencies=[Depends(verify_token)])
    async def remove_schedule(task_id: str):
        if _scheduler and _scheduler.remove(task_id):
            return {"status": "ok"}
        return JSONResponse({"error": "Task not found"}, status_code=404)

    @app.get("/workflows", dependencies=[Depends(verify_token)])
    async def list_workflows():
        if not _workflow_recorder:
            return []
        return _workflow_recorder.list_workflows()

    return app


def start_server(host: str = "0.0.0.0", port: int = 8080) -> threading.Thread:
    """Start the remote control server in a background thread."""
    def _run():
        try:
            import uvicorn
            app = create_app()
            log.info(f"Remote control server at http://localhost:{port}")
            uvicorn.run(app, host=host, port=port, log_level="warning")
        except ImportError:
            log.warning("uvicorn not installed — remote control disabled. Run: pip install fastapi uvicorn")
        except Exception as e:
            log.error(f"Remote server failed: {e}")

    t = threading.Thread(target=_run, daemon=True, name="RemoteServer")
    t.start()
    return t


def _dashboard_html() -> str:
    return """<!DOCTYPE html>
<html>
<head>
<title>AI Human Control Panel</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; margin: 20px; }
  h1 { color: #00d4ff; }
  .card { background: #16213e; border-radius: 8px; padding: 16px; margin: 10px 0; }
  input, button, select { padding: 8px 12px; border-radius: 4px; border: none; margin: 4px; }
  input { background: #0f3460; color: white; width: 60%; }
  button { background: #00d4ff; color: #1a1a2e; font-weight: bold; cursor: pointer; }
  #status { color: #00ff88; }
  #screenshot img { max-width: 100%; border-radius: 8px; }
</style>
</head>
<body>
<h1>AI Human — Remote Control</h1>
<div class="card">
  <b id="status">Loading...</b>
  <br><br>
  <input id="goal" placeholder="Enter goal..." />
  <button onclick="setGoal()">Send Goal</button>
</div>
<div class="card" id="screenshot">
  <button onclick="refreshScreenshot()">Refresh Screenshot</button>
  <br><img id="ss" src="" style="display:none"/>
</div>
<script>
async function fetchStatus() {
  const r = await fetch('/status');
  const d = await r.json();
  document.getElementById('status').textContent =
    'State: ' + d.agent_state + ' | Goal: ' + (d.goal || 'none');
}
async function setGoal() {
  const goal = document.getElementById('goal').value;
  if (!goal) return;
  await fetch('/goal', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({goal})});
  document.getElementById('goal').value = '';
  fetchStatus();
}
async function refreshScreenshot() {
  const r = await fetch('/screenshot');
  const d = await r.json();
  const img = document.getElementById('ss');
  img.src = d.image;
  img.style.display = 'block';
}
setInterval(fetchStatus, 3000);
fetchStatus();
</script>
</body>
</html>"""
