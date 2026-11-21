import os
import sys
import urllib.request
import webbrowser

from . import config

URL = "http://127.0.0.1:8765"


def _prepare(background):
    os.environ.setdefault("HF_HOME", str(config.MODELS / "hf"))  # model cache stays inside the app folder
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # never go online after install
    try:  # be nice to games and other programs: run at below-normal priority
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass
    if background or sys.stdout is None:  # no console window: write to a log file instead
        d = config.ROOT / "logs"
        d.mkdir(exist_ok=True)
        f = d / "nova.log"
        if f.exists() and f.stat().st_size > 1_000_000:
            f.unlink()
        sys.stdout = sys.stderr = open(f, "a", encoding="utf-8", buffering=1)
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _running():
    try:
        return urllib.request.urlopen(URL + "/", timeout=1.5).status == 200
    except Exception:
        return False


def text_mode(cfg):
    from .agent import ensure_ollama
    from .core import Toni
    from . import tools
    ensure_ollama()
    toni = Toni(cfg)
    toni.quiet = True
    tools.configure(cfg, lambda c: input(f"  Run this? / Ausfuehren? {c}  [y/N/j] ").strip().lower()[:1] in ("y", "j"))
    print(f"{cfg['name']} text chat ({cfg['language']}), project '{toni.active['project']}'. Type 'exit' to quit.")
    while (q := input("\nYou: ").strip()) not in ("exit", "quit"):
        if q:
            print(f"{cfg['name']}: {toni.ask(q, 'text')}")


def check(cfg):
    import ollama
    from .agent import ensure_ollama
    from .core import Toni
    from .speech import Ears, Mouth
    ensure_ollama()
    t, name = cfg["t"], cfg["name"]
    print("1/4 Brain: looking for the AI model...")
    have = [m.model for m in ollama.list().models]
    ok = any(m.startswith(cfg["model"]) for m in have)
    print("    model installed:", ok, have)
    if not ok:
        print(f"    FIX: run  ollama pull {cfg['model']}")
    print("2/4 Voice: you should hear a greeting now...")
    Mouth(cfg).speak(t["hello"].format(name=name))
    print("3/4 Hearing:", t["say"].format(name=name))
    print("    heard:", Ears(cfg).listen(wait_s=15))
    print("4/4 Brain: asking the model (first time loads it, can take a minute)...")
    toni = Toni(cfg)
    toni.quiet = True
    print("    model says:", toni.ask(t["hello_q"], "text"))


def main():
    argv = sys.argv[1:]
    background = "--background" in argv
    _prepare(background)
    if "--setlang" in argv:
        code = argv[argv.index("--setlang") + 1]
        config.load(code)  # validates
        config.set_language(code)
        print(f"Language set to: {code}")
        return
    cfg = config.load(argv[argv.index("--lang") + 1] if "--lang" in argv else None)
    try:
        if "--check" in argv:
            check(cfg)
        elif "--text" in argv:
            text_mode(cfg)
        else:
            page = "/workspace" if "--workspace" in argv else ""
            if _running():  # already started (e.g. at Windows start): just open the page
                if not background:
                    webbrowser.open(URL + page)
                return
            from .agent import ensure_ollama
            from .ui import serve
            ensure_ollama()
            serve(cfg, open_browser=not background and "--no-browser" not in argv, page=page)
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")


if __name__ == "__main__":
    main()
