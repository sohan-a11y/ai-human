"""
Browser Extension WebSocket Bridge — Python server that the Chrome/Edge
extension connects to. Provides more reliable browser control than Playwright
because it runs inside the actual browser context.

Protocol (JSON messages):
  Agent → Extension: {"cmd": "click", "selector": "#btn", "id": "req_001"}
  Extension → Agent: {"id": "req_001", "status": "ok", "result": "..."}

Commands:
  click, type, get_text, get_html, navigate, evaluate, scroll,
  wait_for, screenshot, get_url, get_title, fill_form, highlight

The extension connects to ws://localhost:8765 automatically.
"""

from __future__ import annotations
import asyncio
import json
import threading
import time
import uuid
from typing import Any, Optional, Callable
from utils.logger import get_logger

log = get_logger(__name__)


class BrowserBridge:
    """
    WebSocket server that the browser extension connects to.
    Provides synchronous interface for the agent to use.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self._host = host
        self._port = port
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server = None
        self._clients: set = set()
        self._pending: dict[str, asyncio.Future] = {}
        self._thread: Optional[threading.Thread] = None
        self._event_handlers: dict[str, Callable] = {}

    def start(self) -> None:
        """Start the WebSocket server in a background thread."""
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        # Wait for server to be ready
        for _ in range(50):
            if self._loop and self._loop.is_running():
                break
            time.sleep(0.1)

    def stop(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    @property
    def is_connected(self) -> bool:
        return len(self._clients) > 0

    def wait_for_connection(self, timeout: float = 30.0) -> bool:
        """Wait until the extension connects."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_connected:
                return True
            time.sleep(0.5)
        return False

    # ── Browser Commands ───────────────────────────────────────────────────────

    def click(self, selector: str, timeout: float = 10.0) -> dict:
        return self._send_command({"cmd": "click", "selector": selector}, timeout)

    def type_text(self, selector: str, text: str, timeout: float = 10.0) -> dict:
        return self._send_command({"cmd": "type", "selector": selector, "text": text}, timeout)

    def get_text(self, selector: str = "body", timeout: float = 10.0) -> str:
        result = self._send_command({"cmd": "get_text", "selector": selector}, timeout)
        return result.get("result", "")

    def get_html(self, selector: str = "html", timeout: float = 10.0) -> str:
        result = self._send_command({"cmd": "get_html", "selector": selector}, timeout)
        return result.get("result", "")

    def navigate(self, url: str, timeout: float = 30.0) -> dict:
        return self._send_command({"cmd": "navigate", "url": url}, timeout)

    def evaluate(self, script: str, timeout: float = 10.0) -> Any:
        result = self._send_command({"cmd": "evaluate", "script": script}, timeout)
        return result.get("result")

    def scroll(self, selector: str = "window", direction: str = "down",
               amount: int = 300, timeout: float = 5.0) -> dict:
        return self._send_command({
            "cmd": "scroll", "selector": selector,
            "direction": direction, "amount": amount
        }, timeout)

    def wait_for(self, selector: str, timeout: float = 30.0) -> dict:
        return self._send_command({"cmd": "wait_for", "selector": selector}, timeout)

    def screenshot(self, timeout: float = 10.0) -> str:
        """Returns base64-encoded PNG of current page."""
        result = self._send_command({"cmd": "screenshot"}, timeout)
        return result.get("result", "")

    def get_url(self, timeout: float = 5.0) -> str:
        result = self._send_command({"cmd": "get_url"}, timeout)
        return result.get("result", "")

    def get_title(self, timeout: float = 5.0) -> str:
        result = self._send_command({"cmd": "get_title"}, timeout)
        return result.get("result", "")

    def fill_form(self, fields: dict[str, str], timeout: float = 15.0) -> dict:
        """Fill multiple form fields: {selector: value}."""
        return self._send_command({"cmd": "fill_form", "fields": fields}, timeout)

    def highlight(self, selector: str, color: str = "red", timeout: float = 5.0) -> dict:
        """Visually highlight an element for debugging."""
        return self._send_command({"cmd": "highlight", "selector": selector, "color": color}, timeout)

    def find_and_click(self, text: str, timeout: float = 10.0) -> dict:
        """Find element containing text and click it."""
        script = f"""
        const all = Array.from(document.querySelectorAll('button,a,input[type=submit],[role=button]'));
        const el = all.find(e => e.textContent.trim().toLowerCase().includes({json.dumps(text.lower())}));
        if (el) {{ el.click(); return 'clicked: ' + el.tagName + ' ' + el.textContent.trim().substring(0,50); }}
        return 'not found';
        """
        return self._send_command({"cmd": "evaluate", "script": script}, timeout)

    def extract_page_data(self, timeout: float = 15.0) -> dict:
        """Extract key data from page: title, url, links, headings, text."""
        script = """
        return {
            url: location.href,
            title: document.title,
            headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(h => h.textContent.trim()).slice(0,20),
            links: Array.from(document.querySelectorAll('a[href]')).map(a => ({text: a.textContent.trim().substring(0,50), href: a.href})).slice(0,30),
            text: document.body.innerText.substring(0, 3000)
        };
        """
        result = self._send_command({"cmd": "evaluate", "script": script}, timeout)
        return result.get("result", {})

    # ── Internal ───────────────────────────────────────────────────────────────

    def _send_command(self, payload: dict, timeout: float) -> dict:
        if not self.is_connected:
            return {"error": "Browser extension not connected. Open Chrome/Edge with the AI Human extension."}

        req_id = str(uuid.uuid4())[:8]
        payload["id"] = req_id
        future = self._loop.create_future()

        async def _send():
            self._pending[req_id] = future
            msg = json.dumps(payload)
            clients = list(self._clients)
            if clients:
                websocket = next(iter(clients))
                await websocket.send(msg)

        asyncio.run_coroutine_threadsafe(_send(), self._loop)

        try:
            # Block current thread waiting for response
            start = time.time()
            while time.time() - start < timeout:
                if future.done():
                    return future.result()
                time.sleep(0.05)
            return {"error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            self._pending.pop(req_id, None)

    def _run_server(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_server())

    async def _start_server(self) -> None:
        try:
            import websockets
        except ImportError:
            log.error("websockets not installed: pip install websockets")
            return

        async def handler(websocket):
            self._clients.add(websocket)
            log.info(f"Browser extension connected from {websocket.remote_address}")
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        req_id = data.get("id")
                        if req_id and req_id in self._pending:
                            future = self._pending.pop(req_id)
                            if not future.done():
                                self._loop.call_soon_threadsafe(future.set_result, data)
                    except Exception as e:
                        log.debug(f"Bridge message error: {e}")
            finally:
                self._clients.discard(websocket)
                log.info("Browser extension disconnected")

        self._server = await websockets.serve(handler, self._host, self._port)
        log.info(f"Browser extension bridge listening on ws://{self._host}:{self._port}")
        await asyncio.Future()  # run forever


# Extension files for Chrome/Edge
EXTENSION_MANIFEST = {
    "manifest_version": 3,
    "name": "AI Human Browser Bridge",
    "version": "1.0",
    "description": "Connects browser to AI Human agent via WebSocket",
    "permissions": ["activeTab", "scripting", "tabs", "storage"],
    "host_permissions": ["<all_urls>"],
    "background": {"service_worker": "background.js"},
    "content_scripts": [
        {
            "matches": ["<all_urls>"],
            "js": ["content.js"],
            "run_at": "document_idle",
        }
    ],
    "action": {
        "default_popup": "popup.html",
        "default_title": "AI Human Bridge",
    },
}

EXTENSION_BACKGROUND_JS = """
let ws = null;
let reconnectInterval = 3000;

function connect() {
    ws = new WebSocket('ws://localhost:8765');
    ws.onopen = () => {
        console.log('[AI Human] Bridge connected');
        chrome.action.setBadgeText({text: '●'});
        chrome.action.setBadgeBackgroundColor({color: '#00aa00'});
    };
    ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);
        const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
        if (!tab) { ws.send(JSON.stringify({id: msg.id, error: 'no active tab'})); return; }
        try {
            const result = await chrome.scripting.executeScript({
                target: {tabId: tab.id},
                func: executeCommand,
                args: [msg]
            });
            const r = result[0].result;
            ws.send(JSON.stringify({id: msg.id, status: 'ok', result: r}));
        } catch(e) {
            ws.send(JSON.stringify({id: msg.id, status: 'error', error: e.message}));
        }
    };
    ws.onclose = () => {
        chrome.action.setBadgeText({text: '○'});
        setTimeout(connect, reconnectInterval);
    };
}

function executeCommand(msg) {
    const cmd = msg.cmd;
    const sel = msg.selector;
    const el = sel && sel !== 'window' ? document.querySelector(sel) : null;

    if (cmd === 'click') {
        if (!el) return 'element not found: ' + sel;
        el.click(); return 'clicked';
    }
    if (cmd === 'type') {
        if (!el) return 'element not found: ' + sel;
        el.focus(); el.value = msg.text;
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
        return 'typed';
    }
    if (cmd === 'get_text') {
        return el ? el.innerText : document.body.innerText.substring(0, 5000);
    }
    if (cmd === 'get_html') {
        return el ? el.innerHTML.substring(0, 10000) : document.documentElement.outerHTML.substring(0, 10000);
    }
    if (cmd === 'navigate') {
        location.href = msg.url; return 'navigating';
    }
    if (cmd === 'evaluate') {
        // SECURITY: eval() removed. Only allow pre-approved read-only scripts.
        // The agent uses dedicated commands (get_text, get_url, fill_form, etc.) instead.
        // If you need custom JS, add a named command above with explicit logic.
        const SAFE_SCRIPTS = {
            'get_page_data': () => ({
                url: location.href, title: document.title,
                headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(h => h.textContent.trim()).slice(0,20),
                links: Array.from(document.querySelectorAll('a[href]')).map(a => ({text: a.textContent.trim().substring(0,50), href: a.href})).slice(0,30),
                text: document.body.innerText.substring(0, 3000)
            }),
            'get_forms': () => Array.from(document.forms).map(f => ({
                id: f.id, action: f.action,
                fields: Array.from(f.elements).map(e => ({name: e.name, type: e.type, tagName: e.tagName}))
            })).slice(0,10),
        };
        const fn = SAFE_SCRIPTS[msg.script];
        if (fn) return fn();
        return {error: 'Script not in approved list: ' + msg.script};
    }
    if (cmd === 'scroll') {
        const amount = msg.direction === 'down' ? msg.amount : -msg.amount;
        if (el && el !== window) el.scrollBy(0, amount);
        else window.scrollBy(0, amount);
        return 'scrolled';
    }
    if (cmd === 'get_url') return location.href;
    if (cmd === 'get_title') return document.title;
    if (cmd === 'screenshot') {
        // screenshot handled differently — returns base64 via tabs.captureVisibleTab
        return 'use_capture_tab';
    }
    if (cmd === 'fill_form') {
        const results = {};
        for (const [s, v] of Object.entries(msg.fields)) {
            const input = document.querySelector(s);
            if (input) { input.value = v; input.dispatchEvent(new Event('input', {bubbles:true})); results[s] = 'filled'; }
            else results[s] = 'not found';
        }
        return results;
    }
    if (cmd === 'highlight') {
        if (el) { el.style.outline = '3px solid ' + (msg.color || 'red'); return 'highlighted'; }
        return 'element not found';
    }
    if (cmd === 'wait_for') {
        return document.querySelector(sel) ? 'found' : 'not found';
    }
    return 'unknown command: ' + cmd;
}

connect();
"""

EXTENSION_POPUP_HTML = """<!DOCTYPE html>
<html>
<head><title>AI Human Bridge</title>
<style>body{font-family:sans-serif;padding:12px;width:220px;}</style>
</head>
<body>
<h3>🤖 AI Human Bridge</h3>
<div id="status">Connecting...</div>
<script>
chrome.runtime.getBackgroundPage(bg => {
    const ws = bg.ws;
    document.getElementById('status').textContent =
        ws && ws.readyState === 1 ? '✅ Connected to agent' : '❌ Not connected';
});
</script>
</body>
</html>
"""


def create_extension_files(output_dir: str = "browser_extension") -> str:
    """Write extension files to disk so user can load them in Chrome/Edge."""
    import json as _json
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    (out / "manifest.json").write_text(_json.dumps(EXTENSION_MANIFEST, indent=2))
    (out / "background.js").write_text(EXTENSION_BACKGROUND_JS)
    (out / "popup.html").write_text(EXTENSION_POPUP_HTML)
    # Empty content.js (content scripts not needed — background handles all)
    (out / "content.js").write_text("// AI Human content script placeholder")

    instructions = f"""
Extension created at: {out.resolve()}

To install in Chrome/Edge:
1. Open chrome://extensions (or edge://extensions)
2. Enable "Developer mode" (top right toggle)
3. Click "Load unpacked"
4. Select the folder: {out.resolve()}
5. The extension will auto-connect to AI Human when it runs

The AI Human agent will start a WebSocket server on ws://localhost:8765
"""
    (out / "INSTALL.txt").write_text(instructions)
    return str(out.resolve())
