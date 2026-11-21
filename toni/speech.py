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
        path = MODELS / f"whisper-{cfg['whisper_model']}"
        # CPU keeps the GPU free for the language model. int8 is fast and accurate enough.
        self.model = WhisperModel(str(path), device="cpu", compute_type="int8", cpu_threads=8)
        self.prompt = f"{cfg['name']}, {cfg['name']}."
        self.noise = 0.005

    def _record(self, wait_s=None, max_s=25):
        pre = collections.deque(maxlen=10)
        frames, started, quiet, t0 = [], False, 0, time.time()
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=BLOCK, device=self.dev) as s:
            while True:
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

    def listen(self, wait_s=None):
        """Wait for speech, return the text (or None)."""
        audio = self._record(wait_s)
        if audio is None:
            return None
        segs, _ = self.model.transcribe(audio, language="en", beam_size=1, vad_filter=True,
                                        initial_prompt=self.prompt, condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segs).strip()
        return text or None


class Mouth:
    def __init__(self, cfg):
        from kokoro_onnx import Kokoro
        self.k = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
        self.voice, self.speed, self.dev = cfg["voice"], cfg["speed"], cfg["speaker_device"]
        self.lang = "en-gb" if cfg["voice"][:2] in ("bm", "bf") else "en-us"

    @staticmethod
    def clean(text):
        text = re.sub(r"```.*?```", " I put the code on screen. ", text, flags=re.S)
        text = re.sub(r"https?://\S+", " a link ", text)
        text = re.sub(r"[`*#_>|~]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def speak(self, text):
        text = self.clean(text)
        if not text:
            return
        parts = [p for p in re.split(r"(?<=[.!?:])\s+", text) if p.strip()]
        q = queue.Queue(maxsize=2)

        def producer():
            for p in parts:
                q.put(self.k.create(p, voice=self.voice, speed=self.speed, lang=self.lang))
            q.put(None)

        threading.Thread(target=producer, daemon=True).start()
        while (item := q.get()) is not None:
            samples, sr = item
            sd.play(samples, sr, device=self.dev)
            sd.wait()
