"""Local web UI (http://127.0.0.1:8765). Standard library only. Every /api call needs the page's token."""
import json
import os
import pathlib
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import autostart, config, voices
from .core import Toni
from .store import pick_folder

PORT = 8765
PAGES = {"/": "companion.html", "/workspace": "workspace.html"}
_dir = pathlib.Path(__file__).parent


def make_server(toni, port=PORT, token=None):
    token = token or secrets.token_urlsafe(24)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    S = toni.store

    def projects():
        out = []
        for p in S.projects():
            chats = [] if p["missing"] else S.chats(p["name"])
            out.append({**p, "chats": chats})
        return out

    def cfg_public():
        return {k: toni.cfg[k] for k in config.EDITABLE} | {"voices": voices.catalog(), "autostart": autostart.enabled()}

    # ---- GET handlers: (query dict) -> json ----
    def poll(q):
        since = int(q.get("since", 0))
        return {"events": [e for e in toni.events if e["id"] > since], "state": toni.state,
                "voice_on": toni.voice_on, "pending": toni.pending, "active": toni.active,
                "seq": toni.seq, "last_id": toni.last_id, "voice_chat": toni.voice_chat}

    GET = {
        "/api/poll": poll,
        "/api/config": lambda q: cfg_public(),
        "/api/projects": lambda q: projects(),
        "/api/chat": lambda q: toni.chat_log(q["project"], q["id"]),
        "/api/files": lambda q: S.listing(q["project"], q.get("path", "")),
        "/api/file": lambda q: {"text": S.read(q["project"], q["path"])},
    }

    # ---- POST handlers: (body dict) -> json ----
    def send(d):
        text = (d.get("text") or "").strip()
        project, chat, speak = d.get("project"), d.get("chat"), bool(d.get("speak"))

        def work():
            reply = toni.ask(text, "ui", project, chat)
            if speak and not toni.voice_on:
                toni.say(reply)

        if text:
            threading.Thread(target=work, daemon=True).start()
        return {"ok": True}

    def chat_new(d):
        c = S.new_chat(d["project"], (d.get("title") or "New chat")[:40])
        return {"id": c["id"], "seq": toni.set_active(d["project"], c["id"])}

    def chat_rename(d):
        c = S.load_chat(d["project"], d["id"])
        c["title"] = (d["title"] or "Chat").strip()[:40]
        S.save_chat(d["project"], c)
        toni.forget(d["project"])
        return {"ok": True}

    def chat_delete(d):
        S.delete_chat(d["project"], d["id"])
        toni.forget(d["project"])
        if toni.active["chat"] == d["id"]:
            toni.set_active(d["project"])
        return {"ok": True}

    def project_new(d):
        name = S.create(d["name"], d.get("parent") or None)
        return {"name": name, "seq": toni.set_active(name)}

    def project_add(d):
        name = S.add(d["path"])
        return {"name": name, "seq": toni.set_active(name)}

    def project_rename(d):
        new = S.rename(d["name"], d["new"])
        toni.forget()
        if toni.active["project"] == d["name"]:
            toni.active["project"] = new
            toni.seq += 1
        return {"name": new}

    def project_remove(d):
        S.remove(d["name"])
        toni.forget(d["name"])
        if toni.active["project"] == d["name"]:
            toni.set_active(S.projects()[0]["name"])
        return {"ok": True}

    def active(d):
        return {"seq": toni.set_active(d["project"], d.get("chat"))}

    def confirm(d):
        toni.answer_confirm(d.get("yes"))
        return {"ok": True}

    def voice(d):
        if d.get("on"):
            toni.start_voice()
        else:
            threading.Thread(target=toni.stop_voice, daemon=True).start()
        return {"ok": True}

    def stop(d):
        toni.cancel.set()
        toni.answer_confirm(False)
        return {"ok": True}

    def save_cfg(d):
        wl = d.get("wake_words")
        if isinstance(wl, str):
            d["wake_words"] = [w.strip().lower() for w in wl.split(",") if w.strip()]
        config.save(d)
        threading.Thread(target=toni.reload, daemon=True).start()
        return {"ok": True}

    def quit_(d):
        threading.Timer(0.5, lambda: os._exit(0)).start()
        return {"ok": True}

    def preview(d):
        vid = d["voice"]
        if vid not in {v["id"] for v in voices.catalog()}:
            raise ValueError("Unknown voice.")
        lang = "en" if vid.startswith("kokoro:") else vid.split(":")[-1][:2]  # chatterbox ids are the language
        text = config.TEXT.get(lang, config.TEXT["en"])["sample"].format(name=toni.cfg["name"])
        return voices.wav_bytes(voices.load(vid, float(d.get("speed") or toni.cfg["speed"])), text)

    POST = {
        "/api/voice/preview": preview,
        "/api/voice/add": lambda d: voices.add_piper(d["name"].strip()) or {"ok": True},
        "/api/quit": quit_,
        "/api/autostart": lambda d: autostart.set_enabled(bool(d.get("on"))) or {"ok": True},
        "/api/send": send, "/api/stop": stop, "/api/confirm": confirm, "/api/voice": voice,
        "/api/chat/new": chat_new, "/api/chat/rename": chat_rename, "/api/chat/delete": chat_delete,
        "/api/project/new": project_new, "/api/project/add": project_add,
        "/api/project/rename": project_rename, "/api/project/remove": project_remove,
        "/api/pick": lambda d: {"path": pick_folder(d.get("initial"))},
        "/api/active": active, "/api/config": save_cfg,
        "/api/open": lambda d: S.open_external(d["project"], d.get("path", "")) or {"ok": True},
    }

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

        def _route(self, table, arg):
            u = urlparse(self.path)
            fn = table.get(u.path)
            if u.path == "/api/voice/preview":
                fn = preview
            if fn is None:
                return self._send({"error": "not found"}, 404)
            try:
                out = fn(arg(u))
                if isinstance(out, bytes):
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/wav")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    return self.wfile.write(out)
                self._send(out)
            except (ValueError, KeyError, FileNotFoundError, NotADirectoryError, PermissionError) as e:
                self._send({"error": str(e) or e.__class__.__name__}, 400)
            except Exception as e:
                self._send({"error": f"{e.__class__.__name__}: {e}"}, 500)

        def _guard(self):
            if self.headers.get("Host") not in hosts or self.headers.get("X-Token") != token:
                self._send({"error": "forbidden"}, 403)
                return False
            return True

        def do_GET(self):
            if self.headers.get("Host") not in hosts:
                return self._send({"error": "forbidden"}, 403)
            page = PAGES.get(urlparse(self.path).path)
            if page:
                html = (_dir / page).read_text(encoding="utf-8")
                return self._send(html.replace("__TOKEN__", token), ctype="text/html")
            if self._guard():
                self._route(GET, lambda u: {k: v[0] for k, v in parse_qs(u.query).items()})

        def do_POST(self):
            if self._guard():
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                self._route(POST, lambda u: body)

    return ThreadingHTTPServer(("127.0.0.1", port), H), token


def serve(cfg, open_browser=True, page=""):
    toni = Toni(cfg)
    srv, _ = make_server(toni)
    url = f"http://127.0.0.1:{PORT}"
    print(f"Nova is running at {url}  (close this window to quit)")
    if cfg["autostart_voice"]:
        toni.start_voice()
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url + page)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
