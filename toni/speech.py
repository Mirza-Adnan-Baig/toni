import collections
import queue
import re
import threading
import time

import numpy as np
import sounddevice as sd

from .config import MODELS

SR = 16000
BLOCK = 512                  # 32 ms
SILENCE_BLOCKS = 28          # ~0.9 s of quiet ends a sentence


class Ears:
    def __init__(self, cfg):
        from faster_whisper import WhisperModel
        self.dev = cfg["mic_device"]
        self.lang = cfg["language"]
        path = MODELS / f"whisper-{cfg['whisper_model']}"
        # CPU keeps the GPU free for the language model. int8 is fast and accurate enough.
        self.model = WhisperModel(str(path), device="cpu", compute_type="int8", cpu_threads=8)
        # Tiny model (2 threads) is the always-on wake-word checker: very cheap, only runs when someone speaks.
        self.wake = WhisperModel(str(MODELS / f"whisper-{cfg['wake_model']}"), device="cpu",
                                 compute_type="int8", cpu_threads=2)
        self.prompt = f"{cfg['name']}, {cfg['name']}."
        self.noise = 0.005
        self.stop = None

    def _record(self, wait_s=None, max_s=25):
        pre = collections.deque(maxlen=10)
        frames, started, quiet, t0 = [], False, 0, time.time()
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=BLOCK, device=self.dev) as s:
            while True:
                if self.stop is not None and self.stop.is_set():
                    return None
                x = s.read(BLOCK)[0][:, 0]
                rms = float(np.sqrt(np.mean(x * x)))
                thr = max(0.012, self.noise * 3.5)
                if not started:
                    pre.append(x)
                    if rms > thr:
                        started, frames, quiet = True, list(pre), 0
                    else:
                        self.noise = 0.98 * self.noise + 0.02 * rms
                        if wait_s is not None and time.time() - t0 > wait_s:
                            return None
                else:
                    frames.append(x)
                    quiet = 0 if rms > thr * 0.7 else quiet + 1
                    if quiet >= SILENCE_BLOCKS or len(frames) * BLOCK / SR > max_s:
                        break
        audio = np.concatenate(frames)
        return audio if len(audio) / SR > 0.35 else None

    def listen_wake(self, wait_s, is_wake):
        """Idle listening. Cheap tiny-model check; only if the wake word is heard, re-transcribe with the good model."""
        audio = self._record(wait_s, max_s=6)
        if audio is None:
            return None
        segs, _ = self.wake.transcribe(audio, language=self.lang, beam_size=1, vad_filter=True,
                                       initial_prompt=self.prompt, condition_on_previous_text=False)
        quick = " ".join(s.text.strip() for s in segs).strip()
        if not quick or not is_wake(quick):
            return None
        return self.transcribe(audio) or quick

    def transcribe(self, audio, model=None):
        segs, _ = (model or self.model).transcribe(audio, language=self.lang, beam_size=1, vad_filter=True,
                                        initial_prompt=self.prompt, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs).strip() or None

    def listen(self, wait_s=None):
        """Wait for speech, return the text (or None)."""
        audio = self._record(wait_s)
        return None if audio is None else self.transcribe(audio)


class Mouth:
    def __init__(self, cfg):
        from . import voices
        self.engine = voices.load(cfg["voice"], cfg["speed"])
        self.dev = cfg["speaker_device"]
        self.t = cfg["t"]

    def clean(self, text):
        text = re.sub(r"```.*?```", self.t["code"], text, flags=re.S)
        text = re.sub(r"https?://\S+", self.t["link"], text)
        text = re.sub(r"[`*#_>|~]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def speak(self, text):
        text = self.clean(text)
        if not text:
            return
        q = queue.Queue(maxsize=3)

        def producer():
            try:
                for item in self.engine.synth(text):
                    q.put(item)
            finally:
                q.put(None)

        threading.Thread(target=producer, daemon=True).start()
        while (item := q.get()) is not None:
            samples, sr = item
            sd.play(samples, sr, device=self.dev)
            sd.wait()
