"""Shared brain: one Toni object used by the web UI, voice mode and checks."""
import re
import threading
import uuid

from . import config, tools
from .agent import Agent

YES = re.compile(r"\b(yes|yeah|yep|sure|go ahead|do it|okay|ok|proceed|please|ja|jawohl|klar|gerne|bitte|mach|mach das|in ordnung)\b", re.I)
NO = re.compile(r"\b(no|nope|don't|do not|nein|nicht|lieber nicht)\b", re.I)
STOP = re.compile(r"\b(stop|that's all|that is all|thank you|thanks|go to sleep|goodbye|never ?mind|cancel|danke|tschüss|tschuess|das war's|das wars|schluss|abbrechen|vergiss es|gute nacht)\b", re.I)


def wake_split(text, cfg):
    """Return the command after the wake word, or None if the wake word wasn't said."""
    words = "|".join(map(re.escape, cfg["wake_words"]))
    m = re.search(rf"\b(?:(?:hey|hi|ok|okay|hallo|hej)[ ,]+)?(?:{words})\b[ ,.!?:]*", text, re.I)
    if not m or m.start() > 15:
        return None
    return text[m.end():].strip()


class Toni:
    def __init__(self, cfg):
        self.cfg = cfg
        self.events, self._n = [], 0
        self.state = "idle"          # idle | listening | thinking | speaking | loading
        self.pending = None          # command waiting for a UI yes/no
        self._confirm_evt, self._confirm_ans = threading.Event(), False
        self._ears = self._mouth = self.agent = None
        self._load_lock, self.ask_lock = threading.Lock(), threading.Lock()
        self._tl = threading.local()
        self.stop = threading.Event()
        self.voice_thread = None
        self._build()

    # ---- events ----
    def emit(self, kind, text):
        self._n += 1
        self.events.append({"id": self._n, "kind": kind, "text": text})
        del self.events[:-400]
        print(f"[{kind}] {text}", flush=True)

    # ---- parts ----
    def _build(self):
        self.agent = Agent(self.cfg)
        tools.configure(self.cfg, self._confirm)

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

    # ---- confirmation of PC commands ----
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

    # ---- ask ----
    def ask(self, text, origin="ui"):
        self._tl.origin = origin
        with self.ask_lock:
            self.emit("user", text)
            prev, self.state = self.state, "thinking"
            try:
                reply = self.agent.ask(text, lambda n, a: self.emit("tool", f"{n} {str(a)[:150]}"))
            except Exception as e:
                reply = f"Error: {e}"
            self.state = "listening" if self.voice_on else "idle"
            self.emit("assistant", reply)
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
        self._ears = self._mouth = None
        self._build()
        self.emit("status", f"Settings applied (language: {self.cfg['language']}).")
        if was_on:
            self.start_voice()

    def _voice_loop(self):
        try:
            self.state = "loading"
            cfg, t = self.cfg, self.cfg["t"]
            ears, mouth = self.ears(), self.mouth()
            self.state = "listening"
            self.say(t["online"].format(name=cfg["name"]))
            self.emit("status", f"Listening. Say '{cfg['name']}'.")
            while not self.stop.is_set():
                heard = ears.listen(wait_s=1)
                if not heard:
                    continue
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
                    reply = self.ask(cmd, "voice")
                    self.say(reply)
                    nxt = ears.listen(wait_s=cfg["followup_seconds"])
                    if not nxt or (len(nxt.split()) <= 6 and STOP.search(nxt)):
                        break
                    cmd = wake_split(nxt, cfg) or nxt
        except Exception as e:
            self.emit("error", f"Voice stopped: {e}")
        finally:
            self.state = "idle"
