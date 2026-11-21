import re
import sys

from . import config, tools
from .agent import Agent, ensure_ollama

YES = re.compile(r"\b(yes|yeah|yep|sure|go ahead|do it|okay|ok|proceed|please)\b", re.I)
STOP = re.compile(r"\b(stop|that's all|that is all|thank you|thanks|go to sleep|goodbye|never ?mind|cancel)\b", re.I)


def show_tool(name, args):
    print(f"  [tool] {name} {str(args)[:150]}")


def text_mode(cfg):
    tools.configure(cfg, lambda c: input(f"  Run this? {c}  [y/N] ").strip().lower().startswith("y"))
    agent = Agent(cfg)
    print(f"{cfg['name']} text chat. Type 'exit' to quit.")
    while (q := input("\nYou: ").strip()) not in ("exit", "quit"):
        if q:
            print(f"{cfg['name']}: {agent.ask(q, show_tool)}")


def wake_split(text, cfg):
    """Return the command after the wake word, or None if the wake word wasn't said."""
    words = "|".join(map(re.escape, cfg["wake_words"]))
    m = re.search(rf"\b(?:(?:hey|hi|ok|okay)[ ,]+)?(?:{words})\b[ ,.!?:]*", text, re.I)
    if not m or m.start() > 15:
        return None
    return text[m.end():].strip()


def voice_mode(cfg):
    from .speech import Ears, Mouth
    print("Loading voice models...")
    ears, mouth = Ears(cfg), Mouth(cfg)

    def confirm(cmd):
        print(f"  Command: {cmd}")
        mouth.speak(f"I'd like to run: {cmd[:120]}. Shall I?")
        ans = ears.listen(wait_s=8)
        print(f"  You: {ans}")
        return bool(ans and YES.search(ans))

    tools.configure(cfg, confirm)
    agent = Agent(cfg)
    name = cfg["name"]
    mouth.speak(f"{name} online.")
    print(f"Listening. Say '{name}' to wake me. Ctrl+C to quit.")
    while True:
        heard = ears.listen()
        if not heard:
            continue
        cmd = wake_split(heard, cfg)
        if cmd is None:
            continue
        if not cmd:
            mouth.speak("Yes?")
            cmd = ears.listen(wait_s=6)
            if not cmd:
                continue
        while cmd:
            print(f"You: {cmd}")
            reply = agent.ask(cmd, show_tool)
            print(f"{name}: {reply}")
            mouth.speak(reply)
            nxt = ears.listen(wait_s=cfg["followup_seconds"])
            if not nxt or (len(nxt.split()) <= 6 and STOP.search(nxt)):
                break
            cmd = wake_split(nxt, cfg) or nxt


def check(cfg):
    import ollama
    from .speech import Ears, Mouth
    have = [m.model for m in ollama.list().models]
    print("Model installed:", any(m.startswith(cfg["model"]) for m in have), have)
    mouth = Mouth(cfg)
    mouth.speak(f"Hello. This is {cfg['name']}. If you can hear me, the speakers work.")
    ears = Ears(cfg)
    print("Say something now (e.g. 'Toni, what time is it')...")
    print("Heard:", ears.listen(wait_s=15))
    print("Asking the model (first time loads it, can take a minute)...")
    print("Model says:", Agent(cfg).ask("Say hello in five words."))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = config.load()
    ensure_ollama()
    try:
        if "--check" in sys.argv:
            check(cfg)
        elif "--text" in sys.argv:
            text_mode(cfg)
        else:
            voice_mode(cfg)
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")


if __name__ == "__main__":
    main()
