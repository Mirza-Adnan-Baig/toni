import sys

from . import config, tools
from .agent import Agent, ensure_ollama


def show_tool(name, args):
    print(f"  [tool] {name} {str(args)[:150]}")


def text_mode(cfg):
    tools.configure(cfg, lambda c: input(f"  Run this? / Ausfuehren? {c}  [y/N/j] ").strip().lower()[:1] in ("y", "j"))
    agent = Agent(cfg)
    print(f"{cfg['name']} text chat ({cfg['language']}). Type 'exit' to quit.")
    while (q := input("\nYou: ").strip()) not in ("exit", "quit"):
        if q:
            print(f"{cfg['name']}: {agent.ask(q, show_tool)}")


def check(cfg):
    import ollama
    from .speech import Ears, Mouth
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
    ears = Ears(cfg)
    print("    heard:", ears.listen(wait_s=15))
    print("4/4 Brain: asking the model (first time loads it, can take a minute)...")
    print("    model says:", Agent(cfg).ask(t["hello_q"]))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    if "--setlang" in argv:
        code = argv[argv.index("--setlang") + 1]
        config.load(code)  # validates
        config.set_language(code)
        print(f"Language set to: {code}")
        return
    lang = argv[argv.index("--lang") + 1] if "--lang" in argv else None
    cfg = config.load(lang)
    ensure_ollama()
    try:
        if "--check" in argv:
            check(cfg)
        elif "--text" in argv:
            text_mode(cfg)
        else:
            from .ui import serve
            serve(cfg, open_browser="--no-browser" not in argv)
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")


if __name__ == "__main__":
    main()
