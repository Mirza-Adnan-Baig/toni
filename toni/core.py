"""Shared brain: projects, chats, agents, voice loop. Used by the web UI and the terminal modes."""
import re
import threading
from difflib import SequenceMatcher
import time
import uuid

from . import config, tools
from .agent import Agent
from .store import Store

YES = re.compile(r"\b(yes|yeah|yep|sure|go ahead|do it|okay|ok|proceed|please|ja|jawohl|klar|gerne|bitte|mach|mach das|in ordnung)\b", re.I)
NO = re.compile(r"\b(no|nope|don't|do not|nein|nicht|lieber nicht)\b", re.I)
STOP = re.compile(r"\b(stop|that's all|that is all|thank you|thanks|go to sleep|goodbye|never ?mind|cancel|danke|tschüss|tschuess|das war's|das wars|schluss|abbrechen|vergiss es|gute nacht)\b", re.I)


def wake_split(text, cfg, thr=0.65):
    """Return the command after the wake word, or None if the wake word wasn't said.
    The wake word may be the 1st-3rd word ("Hey Nova, ...") and may be slightly misheard ("Nuva")."""
    words = [w.lower() for w in cfg["wake_words"]]
    for i, m in enumerate(re.finditer(r"[\w'-]+", text)):
        if i > 2:
            break
        w = m.group(0).lower()
        if w in words or any(len(x) >= 4 and (w.endswith(x) or SequenceMatcher(None, w, x).ratio() >= thr) for x in words):
            return text[m.end():].lstrip(" ,.!?:;-").strip()
    return None


class Toni:
    def __init__(self, cfg, registry=None):
        self.cfg = cfg
        self.quiet = False
        self.store = Store(registry or config.ROOT / "projects.json", cfg["projects_dir"])
        self.events, self._n = [], 0
        self.state = "idle"          # idle | listening | thinking | speaking | loading
        self.pending = None
        self._confirm_evt, self._confirm_ans = threading.Event(), False
        self._ears = self._mouth = None
        self._agents = {}            # (project, chat id) -> (chat dict, Agent)
        self._load_lock, self.ask_lock = threading.Lock(), threading.Lock()
        self._tl = threading.local()
        self.stop = threading.Event()      # stops the voice loop
        self.cancel = threading.Event()    # stops the running agent task
        self.voice_thread = None
        self.active, self.seq = {"project": None, "chat": None}, 0
        self.voice_chat = {}
        tools.configure(cfg, self._confirm)
        tools.HOOKS.update(list_projects=self._h_list, open_project=self._h_open, new_chat=self._h_new_chat)
        self._ensure_voice_chat()
        self.set_active(self.store.projects()[0]["name"])

    def _ensure_voice_chat(self):
        """The companion (voice) has its own permanent conversation, separate from workspace chats."""
        if "Voice" not in {p["name"] for p in self.store.projects()}:
            self.store.create("Voice")
        cid = next((c["id"] for c in self.store.chats("Voice") if c["title"] == "Voice conversation"), None)
        cid = cid or self.store.new_chat("Voice", "Voice conversation")["id"]
        self.voice_chat = {"project": "Voice", "chat": cid}

    # ---- events ----
    def emit(self, kind, text, **extra):
        self._n += 1
        self.events.append({"id": self._n, "kind": kind, "text": text, **extra})
        del self.events[:-400]
        if not (self.quiet and kind in ("user", "assistant")):
            print(f"[{kind}] {text}", flush=True)

    @property
    def last_id(self):
        return self._n

    # ---- active project / chat ----
    def set_active(self, project, chat_id=None):
        if chat_id is None:
            chats = self.store.chats(project)
            chat_id = chats[0]["id"] if chats else self.store.new_chat(project)["id"]
        self.active = {"project": project, "chat": chat_id}
        self.seq += 1
        return self.seq

    def _h_list(self):
        names = [p["name"] for p in self.store.projects()]
        return f"Projects: {', '.join(names)}. Open now: {self.active['project']}."

    def _h_open(self, name):
        names = [p["name"] for p in self.store.projects() if not p["missing"]]
        low = name.strip().lower()
        hits = [n for n in names if n.lower() == low] or [n for n in names if low in n.lower() or n.lower() in low]
        if not hits:
            return f"No project matches '{name}'. Projects: {', '.join(names)}."
        if len(hits) > 1:
            return f"Several projects match: {', '.join(hits)}. Ask the user which one."
        self.set_active(hits[0])
        return f"Opened project '{hits[0]}' on screen."

    def _h_new_chat(self, title="New chat"):
        p = self.active["project"]
        self.set_active(p, self.store.new_chat(p, title or "New chat")["id"])
        return f"Started a new chat in '{p}' and showed it on screen."

    # ---- parts ----
    def ears(self):
        with self._load_lock:
            if self._ears is None:
                from .speech import Ears
                self._ears = Ears(self.cfg)
            self._ears.stop = self.stop
            return self._ears

    def mouth(self):
        with self._load_lock:
            if self._mouth is None:
                from .speech import Mouth
                self._mouth = Mouth(self.cfg)
            return self._mouth

    # ---- confirmation of PC commands (voice-origin: spoken; UI-origin: buttons; timeout = no) ----
    def _confirm(self, cmd):
        if getattr(self._tl, "origin", "ui") == "voice":
            self.emit("confirm", cmd)
            self.state = "speaking"
            self.mouth().speak(self.cfg["t"]["confirm"].format(cmd=cmd[:120]))
            self.state = "listening"
            ans = self.ears().listen(wait_s=8)
            self.emit("heard", ans or "")
            return bool(ans and YES.search(ans) and not NO.search(ans))
        self.pending = {"id": uuid.uuid4().hex, "cmd": cmd}
        self._confirm_evt.clear()
        self.emit("confirm", cmd)
        ok = self._confirm_evt.wait(180) and self._confirm_ans
        self.pending = None
        return ok

    def answer_confirm(self, yes):
        self._confirm_ans = bool(yes)
        self._confirm_evt.set()

    # ---- chats ----
    def _chat(self, project, cid):
        key = (project, cid)
        if key not in self._agents:
            data = self.store.load_chat(project, cid)
            path = self.store.path(project)
            agent = Agent(self.cfg, str(path), project, self.store.notes(project), data.get("messages"))
            self._agents[key] = (data, agent)
        return self._agents[key]

    def forget(self, project=None):
        """Drop cached agents (after settings/language change or chat/project removal)."""
        for k in [k for k in self._agents if project is None or k[0] == project]:
            self._agents.pop(k)

    def chat_log(self, project, cid):
        data = self.store.load_chat(project, cid)
        return {"title": data["title"], "log": data["log"], "last_id": self.last_id}

    def _event(self, project, data, kind, text):
        data["log"].append({"kind": kind, "text": text})
        data["log"] = data["log"][-600:]
        data["updated"] = time.time()
        self.store.save_chat(project, data)
        self.emit(kind, text, chat=data["id"], project=project)

    def ask(self, text, origin="ui", project=None, chat_id=None):
        project = project or self.active["project"]
        chat_id = chat_id or self.active["chat"]
        self._tl.origin = origin
        if self.ask_lock.locked():
            self.emit("status", "Nova is busy. Your request is queued.")
        with self.ask_lock:
            self.cancel.clear()
            try:
                data, agent = self._chat(project, chat_id)
            except Exception as e:
                self.emit("error", str(e))
                return str(e)
            tools.set_workspace(self.store.path(project))
            if data["title"] == "New chat" and not data["log"]:
                data["title"] = text.strip()[:40] or "New chat"
            self._event(project, data, "user", text)
            self.state = "thinking"
            try:
                reply = agent.ask(text, lambda n, a: self._event(project, data, "tool", f"{n} {str(a)[:150]}"),
                                  self.cancel.is_set)
            except Exception as e:
                reply = f"Error: {e}"
            data["messages"] = agent.dump()
            self.state = "listening" if self.voice_on else "idle"
            self._event(project, data, "assistant", reply)
        return reply

    def say(self, text):
        self.state = "speaking"
        try:
            self.mouth().speak(text)
        finally:
            self.state = "listening" if self.voice_on else "idle"

    # ---- voice loop ----
    @property
    def voice_on(self):
        return bool(self.voice_thread and self.voice_thread.is_alive())

    def start_voice(self):
        if self.voice_on:
            return
        self.stop.clear()
        self.voice_thread = threading.Thread(target=self._voice_loop, daemon=True)
        self.voice_thread.start()

    def stop_voice(self):
        self.stop.set()
        if self.voice_thread:
            self.voice_thread.join(timeout=15)
        self.state = "idle"

    def reload(self):
        was_on = self.voice_on
        self.stop_voice()
        self.cfg = config.load()
        self.store.parent = type(self.store.parent)(self.cfg["projects_dir"])
        self._ears = self._mouth = None
        self.forget()
        tools.configure(self.cfg, self._confirm)
        self.emit("status", f"Settings applied (language: {self.cfg['language']}).")
        if was_on:
            self.start_voice()

    def _warm(self):
        """Load the AI model into the GPU while the user is still speaking the command."""
        def go():
            try:
                import ollama
                ollama.generate(model=self.cfg["model"], prompt="", keep_alive=self.cfg["model_keep_alive"],
                                options={"num_ctx": self.cfg["num_ctx"]})
            except Exception:
                pass
        threading.Thread(target=go, daemon=True).start()

    def _voice_loop(self):
        first = True
        while not self.stop.is_set():
            try:
                self._voice_session(first)
                first = False
            except Exception as e:  # e.g. microphone not ready right after boot: retry quietly
                self.emit("error", f"Voice problem, retrying in 10 s: {e}")
                self.state = "idle"
                self.stop.wait(10)
        self.state = "idle"

    def _voice_session(self, announce):
        cfg, t = self.cfg, self.cfg["t"]
        self.state = "loading"
        self._ensure_voice_chat()
        ears = self.ears()
        self.mouth()
        self.state = "listening"
        if announce:
            self.say(t["online"].format(name=cfg["name"]))
        self.emit("status", f"Listening. Say '{cfg['name']}'.")
        while not self.stop.is_set():
            heard = ears.listen_wake(1, lambda s: wake_split(s, cfg) is not None)
            if not heard:
                continue
            self._warm()
            self.emit("heard", heard)
            cmd = wake_split(heard, cfg)
            if cmd is None:
                continue
            if not cmd:
                self.say(t["yes"])
                cmd = ears.listen(wait_s=6)
                if not cmd:
                    continue
            while cmd and not self.stop.is_set():
                reply = self.ask(cmd, "voice", **{"project": self.voice_chat["project"], "chat_id": self.voice_chat["chat"]})
                self.say(reply)
                nxt = ears.listen(wait_s=cfg["followup_seconds"])
                if not nxt or (len(nxt.split()) <= 6 and STOP.search(nxt)):
                    break
                cmd = wake_split(nxt, cfg) or nxt
