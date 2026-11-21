import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

DEFAULTS = {
    "language": "en",                 # "en" = English, "de" = Deutsch (switch in the UI or with Language.bat)
    "name": "Nova",
    "wake_words": ["nova", "nova", "novah"],
    "model": "gpt-oss:20b",
    "num_ctx": 16384,
    "voice_en": "en_US-amy-medium",      # female English voice
    "voice_de": "de_DE-kerstin-medium",  # female German voice
    "speed": 1.0,
    "whisper_model": "small",         # multilingual hearing model (English + German)
    "ask_before_commands": True,      # ask before running PC commands
    "autostart_voice": True,          # start listening as soon as the window opens
    "workspace": str(pathlib.Path.home() / "Nova" / "workspace"),
    "followup_seconds": 8,            # keeps listening this long after a reply (no wake word needed)
    "mic_device": None,
    "speaker_device": None,
}

EDITABLE = {"language", "name", "wake_words", "voice_en", "voice_de", "speed", "model",
            "ask_before_commands", "autostart_voice", "followup_seconds"}

TEXT = {
    "en": {
        "system": (
            "You are {name}, a private AI assistant running fully offline on the user's own PC. The user is not a programmer. "
            "Always answer in English.\n"
            "You can talk, write and run code, manage files in the workspace folder ({ws}), and open apps. File paths are relative to that folder and commands run inside it.\n"
            "Rules:\n"
            "- Your replies are spoken aloud: be brief and natural, 1-3 short sentences. No markdown, no lists, no emojis.\n"
            "- When asked to build something, write the files with write_file, test with run_command, then summarise in one or two sentences. Never read code aloud.\n"
            "- Use tools instead of guessing. If a tool fails, fix it and retry.\n"
            "- Ask a short question only if the request is truly unclear."
        ),
        "online": "{name} online.",
        "yes": "Yes?",
        "confirm": "I'd like to run: {cmd}. Shall I?",
        "code": " I put the code on screen. ",
        "link": " a link ",
        "hello": "Hello. This is {name}. If you can hear me, the speakers work.",
        "say": "Say something now, for example: '{name}, what time is it?'",
        "stuck": "I got stuck on that one. Could you rephrase it?",
        "done": "Done.",
        "hello_q": "Say hello in five words.",
    },
    "de": {
        "system": (
            "Du bist {name}, ein privater KI-Assistent, der komplett offline auf dem PC des Nutzers laeuft. Der Nutzer ist kein Programmierer. "
            "Antworte immer auf Deutsch.\n"
            "Du kannst sprechen, Code schreiben und ausfuehren, Dateien im Arbeitsordner ({ws}) verwalten und Programme oeffnen. Dateipfade sind relativ zu diesem Ordner und Befehle laufen darin.\n"
            "Regeln:\n"
            "- Deine Antworten werden laut vorgelesen: kurz und natuerlich, 1-3 kurze Saetze. Kein Markdown, keine Listen, keine Emojis.\n"
            "- Wenn etwas gebaut werden soll: Dateien mit write_file schreiben, mit run_command testen, dann in ein bis zwei Saetzen zusammenfassen. Nie Code vorlesen.\n"
            "- Benutze Werkzeuge statt zu raten. Wenn ein Werkzeug fehlschlaegt, behebe es und versuche es erneut.\n"
            "- Stelle nur eine kurze Rueckfrage, wenn die Anfrage wirklich unklar ist."
        ),
        "online": "{name} ist bereit.",
        "yes": "Ja?",
        "confirm": "Ich moechte folgendes ausfuehren: {cmd}. Soll ich?",
        "code": " Ich habe den Code auf dem Bildschirm gezeigt. ",
        "link": " ein Link ",
        "hello": "Hallo. Ich bin {name}. Wenn du mich hoerst, funktionieren die Lautsprecher.",
        "say": "Sag jetzt etwas, zum Beispiel: '{name}, wie spaet ist es?'",
        "stuck": "Da bin ich haengengeblieben. Kannst du es anders sagen?",
        "done": "Erledigt.",
        "hello_q": "Sag Hallo in fuenf Woertern.",
    },
}


def _file():
    return ROOT / "config.json"


def _read():
    return json.loads(_file().read_text(encoding="utf-8-sig")) if _file().exists() else {}


def load(lang_override=None):
    cfg = dict(DEFAULTS)
    cfg.update(_read())
    if lang_override:
        cfg["language"] = lang_override
    if cfg["language"] not in TEXT:
        raise SystemExit(f"Unknown language '{cfg['language']}'. Use 'en' or 'de'.")
    cfg["t"] = TEXT[cfg["language"]]
    cfg["voice"] = cfg["voice_" + cfg["language"]]
    pathlib.Path(cfg["workspace"]).mkdir(parents=True, exist_ok=True)
    return cfg


def save(updates):
    data = _read()
    data.update({k: v for k, v in updates.items() if k in EDITABLE})
    _file().write_text(json.dumps(data, indent=2), encoding="utf-8")


def set_language(code):
    save({"language": code})


def voices():
    d = MODELS / "piper"
    return sorted(p.name[:-5] for p in d.glob("*.onnx")) if d.exists() else []
