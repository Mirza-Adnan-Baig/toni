import subprocess
import time

import ollama

from . import tools

def ensure_ollama():
    try:
        ollama.list()
        return
    except Exception:
        pass
    subprocess.Popen(["ollama", "serve"], creationflags=0x08000000)  # no console window
    for _ in range(30):
        time.sleep(1)
        try:
            ollama.list()
            return
        except Exception:
            pass
    raise RuntimeError("Ollama is not running. Open the Ollama app from the Start menu and try again.")


def _role(m):
    return m["role"] if isinstance(m, dict) else m.role


class Agent:
    def __init__(self, cfg):
        self.cfg = cfg
        self.t = cfg["t"]
        self.messages = [{"role": "system", "content": self.t["system"].format(name=cfg["name"], ws=cfg["workspace"])}]

    def _trim(self):
        if len(self.messages) > 60:
            cut = len(self.messages) - 40
            while cut < len(self.messages) and _role(self.messages[cut]) != "user":
                cut += 1
            self.messages = self.messages[:1] + self.messages[cut:]

    def ask(self, text, on_tool=None):
        self._trim()
        self.messages.append({"role": "user", "content": text})
        for _ in range(14):
            resp = ollama.chat(model=self.cfg["model"], messages=self.messages, tools=tools.TOOLS,
                               options={"num_ctx": self.cfg["num_ctx"], "temperature": 0.4})
            msg = resp.message
            self.messages.append(msg)
            if not msg.tool_calls:
                return msg.content or self.t["done"]
            for call in msg.tool_calls:
                name, args = call.function.name, dict(call.function.arguments)
                if on_tool:
                    on_tool(name, args)
                try:
                    result = tools.REGISTRY[name](**args)
                except Exception as e:  # report to the model so it can recover
                    result = f"Error: {e}"
                self.messages.append({"role": "tool", "tool_name": name, "content": str(result)[:6000]})
        return self.t["stuck"]
