"""Local web UI (http://127.0.0.1:8765). Standard library only."""
import json
import pathlib
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config
from .core import Toni

PORT = 8765
HTML = (pathlib.Path(__file__).parent / "ui.html").read_text(encoding="utf-8")


def public_cfg(t):
    c = t.cfg
    return {k: c[k] for k in config.EDITABLE} | {"voices": config.voices()}


def serve(cfg, open_browser=True):
    toni = Toni(cfg)
    token = secrets.token_urlsafe(24)
    hosts = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, obj, code=200, ctype="application/json"):
            body = obj.encode() if isinstance(obj, str) else json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _ok(self):
            return self.headers.get("Host") in hosts

        def do_GET(self):
            if not self._ok():
                return self._send({"error": "bad host"}, 403)
            if self.path == "/":
                return self._send(HTML.replace("__TOKEN__", token), ctype="text/html")
            if self.path.startswith("/api/poll"):
                since = int(self.path.split("since=")[-1] or 0) if "since=" in self.path else 0
                return self._send({
                    "events": [e for e in toni.events if e["id"] > since],
                    "state": toni.state, "voice_on": toni.voice_on, "pending": toni.pending,
                })
            if self.path == "/api/config":
                return self._send(public_cfg(toni))
            self._send({"error": "not found"}, 404)

        def do_POST(self):
            if not self._ok() or self.headers.get("X-Token") != token:
                return self._send({"error": "forbidden"}, 403)
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/chat":
                text = (data.get("text") or "").strip()
                speak = bool(data.get("speak"))

                def work():
                    reply = toni.ask(text, "ui")
                    if speak and not toni.voice_on:
                        toni.say(reply)

                if text:
                    threading.Thread(target=work, daemon=True).start()
                return self._send({"ok": True})
            if self.path == "/api/confirm":
                toni.answer_confirm(data.get("yes"))
                return self._send({"ok": True})
            if self.path == "/api/voice":
                if data.get("on"):
                    toni.start_voice()
                else:
                    threading.Thread(target=toni.stop_voice, daemon=True).start()
                return self._send({"ok": True})
            if self.path == "/api/config":
                wl = data.get("wake_words")
                if isinstance(wl, str):
                    data["wake_words"] = [w.strip().lower() for w in wl.split(",") if w.strip()]
                config.save(data)
                threading.Thread(target=toni.reload, daemon=True).start()
                return self._send({"ok": True})
            self._send({"error": "not found"}, 404)

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    url = f"http://127.0.0.1:{PORT}"
    print(f"Toni UI running at {url}  (close this window to quit)")
    if cfg["autostart_voice"]:
        toni.start_voice()
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
