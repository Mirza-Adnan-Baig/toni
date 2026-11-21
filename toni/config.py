import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

DEFAULTS = {
    "name": "Toni",
    "wake_words": ["toni", "tony", "tonie", "tonny", "toney"],
    "model": "gpt-oss:20b",
    "num_ctx": 16384,
    "voice": "bm_george",        # British male. Others: am_michael, af_heart, bf_emma ...
    "speed": 1.05,
    "whisper_model": "small.en",
    "ask_before_commands": True,  # Toni asks "Shall I?" before running PC commands
    "workspace": str(pathlib.Path.home() / "Toni" / "workspace"),
    "followup_seconds": 8,        # keeps listening this long after a reply (no wake word needed)
    "mic_device": None,
    "speaker_device": None,
}


def load():
    cfg = dict(DEFAULTS)
    p = ROOT / "config.json"
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    pathlib.Path(cfg["workspace"]).mkdir(parents=True, exist_ok=True)
    return cfg
