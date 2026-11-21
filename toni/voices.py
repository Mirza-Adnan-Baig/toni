"""Voice engines (Piper, Kokoro) behind one interface, plus the catalog shown in the dashboard."""
import io
import re
import subprocess
import sys
import wave

import numpy as np

from .config import MODELS

KOKORO_MODEL, KOKORO_VOICES = MODELS / "kokoro-v1.0.onnx", MODELS / "voices-v1.0.bin"
KOKORO_NOTE = {"af": "female US", "am": "male US", "bf": "female UK", "bm": "male UK"}
PIPER_ID = re.compile(r"^[a-z]{2}_[A-Z]{2}-[A-Za-z0-9_]+-(x_low|low|medium|high)$")
_cache = {}


def split(voice_id):
    eng, _, name = voice_id.partition(":")
    return (eng, name) if name else ("piper", eng)


def chatterbox_installed():
    import importlib.util
    return importlib.util.find_spec("chatterbox") is not None


def catalog():
    """Installed voices: [{id, label, lang, engine}]"""
    out = []
    d = MODELS / "piper"
    for f in sorted(d.glob("*.onnx")) if d.exists() else []:
        n = f.name[:-5]
        out.append({"id": "piper:" + n, "label": f"Piper - {n}", "lang": n[:2], "engine": "piper"})
    if KOKORO_MODEL.exists() and KOKORO_VOICES.exists():
        try:
            names = sorted(np.load(KOKORO_VOICES, allow_pickle=True).files)
        except Exception:
            names = []
        for n in names:
            if n[:2] in KOKORO_NOTE:
                out.append({"id": "kokoro:" + n, "label": f"Kokoro - {n[3:].title()} ({KOKORO_NOTE[n[:2]]})",
                            "lang": "en", "engine": "kokoro"})
    if chatterbox_installed():
        for lang, nm in (("de", "German"), ("en", "English")):
            out.append({"id": "chatterbox:" + lang, "label": f"Chatterbox - {nm} (most human, slow, uses ~3.5 GB GPU)",
                        "lang": lang, "engine": "chatterbox"})
    return out


def add_piper(name):
    """Download one more Piper voice (needs internet once)."""
    if not PIPER_ID.match(name):
        raise ValueError("Voice names look like de_DE-thorsten-high (see the Piper samples page).")
    r = subprocess.run([sys.executable, "-m", "piper.download_voices", name, "--download-dir", str(MODELS / "piper")],
                       capture_output=True, text=True, timeout=600)
    if not (MODELS / "piper" / f"{name}.onnx").exists():
        raise ValueError("Download failed. Check the voice name and your internet connection.")


class PiperEngine:
    def __init__(self, name, speed):
        from piper import PiperVoice, SynthesisConfig
        self.v = PiperVoice.load(str(MODELS / "piper" / f"{name}.onnx"))
        self.syn = SynthesisConfig(length_scale=1.0 / speed)

    def synth(self, text):
        for ch in self.v.synthesize(text, syn_config=self.syn):
            yield ch.audio_float_array, ch.sample_rate


class KokoroEngine:
    def __init__(self, name, speed):
        from kokoro_onnx import Kokoro
        self.k = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
        self.name, self.speed = name, speed
        self.lang = "en-gb" if name[0] == "b" else "en-us"

    def synth(self, text):
        for part in [p for p in re.split(r"(?<=[.!?:])\s+", text) if p.strip()]:
            s, sr = self.k.create(part, voice=self.name, speed=self.speed, lang=self.lang)
            yield s, sr


class ChatterboxEngine:
    """Natural multilingual voice (MIT license). Optional: run 'Install Chatterbox voices.bat' first."""
    _model = None

    def __init__(self, lang, speed):
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        self.lang = lang
        if ChatterboxEngine._model is None:
            ChatterboxEngine._model = ChatterboxMultilingualTTS.from_pretrained(
                device="cuda" if torch.cuda.is_available() else "cpu")
        self.m = ChatterboxEngine._model

    def synth(self, text):
        for part in [p for p in re.split(r"(?<=[.!?:])\s+", text) if p.strip()]:
            wav = self.m.generate(part, language_id=self.lang)
            yield wav.squeeze().cpu().numpy(), self.m.sr


def load(voice_id, speed=1.0):
    key = (voice_id, round(speed, 2))
    if key not in _cache:
        eng, name = split(voice_id)
        _cache[key] = {"kokoro": KokoroEngine, "chatterbox": ChatterboxEngine}.get(eng, PiperEngine)(name, speed)
    return _cache[key]


def wav_bytes(engine, text):
    parts, sr = [], 22050
    for a, sr in engine.synth(text):
        parts.append(np.asarray(a, dtype=np.float32))
    pcm = (np.clip(np.concatenate(parts), -1, 1) * 32767).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    return buf.getvalue()
