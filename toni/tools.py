"""Things Nova can do. File access is limited to the current project folder."""
import datetime
import os
import pathlib
import re
import subprocess
import threading

_cfg = {}
_confirm = lambda msg: False  # replaced at startup
_tl = threading.local()
HOOKS = {}                    # filled by core.Toni: project/chat switching

BLOCKED = re.compile(r"format-volume|diskpart|bcdedit|reg\s+delete|cipher\s+/w", re.I)


def configure(cfg, confirm):
    global _cfg, _confirm
    _cfg, _confirm = cfg, confirm


def set_workspace(path):
    _tl.ws = str(path)


def _ws():
    ws = getattr(_tl, "ws", None)
    if not ws:
        raise RuntimeError("No project selected.")
    return pathlib.Path(ws)


def _safe(path):
    root = _ws().resolve()
    p = (root / path).resolve()
    if os.path.commonpath([os.path.normcase(str(root)), os.path.normcase(str(p))]) != os.path.normcase(str(root)):
        raise ValueError("Path is outside the project folder.")
    if ":" in str(path) or any(part.lower() == ".nova" for part in p.relative_to(root).parts):
        raise ValueError("That path is not available.")
    return p


def list_files(path: str = ".") -> str:
    """List files and folders inside the current project.

    Args:
        path: Folder relative to the project, "." for the top.
    """
    p = _safe(path)
    return "\n".join(sorted(f"{x.name}{'/' if x.is_dir() else ''}" for x in p.iterdir() if x.name != ".nova")) or "(empty)"


def read_file(path: str) -> str:
    """Read a text file from the current project.

    Args:
        path: File path relative to the project.
    """
    return _safe(path).read_text(encoding="utf-8", errors="replace")[:20000]


def write_file(path: str, content: str) -> str:
    """Create or overwrite a text/code file in the current project.

    Args:
        path: File path relative to the project, e.g. "game/main.py".
        content: Full file contents.
    """
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {p.name}"


def run_command(command: str, timeout_seconds: int = 60) -> str:
    """Run a PowerShell command on the PC, inside the current project folder. Use for running code, installing packages, git, etc.

    Args:
        command: The PowerShell command.
        timeout_seconds: Give up after this many seconds.
    """
    if BLOCKED.search(command):
        return "Refused: that command is too dangerous."
    if _cfg.get("ask_before_commands", True) and not _confirm(command):
        return "The user said no. Do not run it."
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            cwd=str(_ws()), capture_output=True, text=True,
            timeout=min(int(timeout_seconds), 600), errors="replace",
        )
        return f"exit code {r.returncode}\n{(r.stdout + r.stderr)[-4000:]}"
    except subprocess.TimeoutExpired:
        return "Timed out."


def open_app(name: str) -> str:
    """Open an app, file or website on the PC (e.g. "notepad", "calc", "https://example.com").

    Args:
        name: App name, file path or URL.
    """
    os.startfile(name)
    return f"Opened {name}"


def get_time() -> str:
    """Get the current date and time."""
    return datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")


def _hook(name, *a):
    if name not in HOOKS:
        return "Not available."
    return HOOKS[name](*a)


def list_projects() -> str:
    """List the user's projects and the one that is open now."""
    return _hook("list_projects")


def open_project(name: str) -> str:
    """Switch the app to another project (opens its latest chat on screen). Use when the user says e.g. 'open project Homework'.

    Args:
        name: Project name (approximate is fine).
    """
    return _hook("open_project", name)


def new_chat(title: str = "New chat") -> str:
    """Start a new empty chat inside the current project and show it on screen.

    Args:
        title: Short title for the chat.
    """
    return _hook("new_chat", title)


TOOLS = [list_files, read_file, write_file, run_command, open_app, get_time,
         list_projects, open_project, new_chat]
REGISTRY = {f.__name__: f for f in TOOLS}
