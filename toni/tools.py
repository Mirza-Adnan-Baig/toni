"""Things Toni can do. Files are limited to the workspace folder."""
import datetime
import os
import pathlib
import re
import subprocess

_cfg = {}
_confirm = lambda msg: False  # replaced at startup

BLOCKED = re.compile(r"format-volume|diskpart|bcdedit|reg\s+delete|cipher\s+/w", re.I)


def configure(cfg, confirm):
    global _cfg, _confirm
    _cfg, _confirm = cfg, confirm


def _safe(path):
    root = pathlib.Path(_cfg["workspace"]).resolve()
    p = (root / path).resolve()
    if root != p and root not in p.parents:
        raise ValueError("Path is outside the workspace folder.")
    return p


def list_files(path: str = ".") -> str:
    """List files and folders inside the workspace.

    Args:
        path: Folder relative to the workspace, "." for the top.
    """
    p = _safe(path)
    return "\n".join(sorted(f"{x.name}{'/' if x.is_dir() else ''}" for x in p.iterdir())) or "(empty)"


def read_file(path: str) -> str:
    """Read a text file from the workspace.

    Args:
        path: File path relative to the workspace.
    """
    return _safe(path).read_text(encoding="utf-8", errors="replace")[:20000]


def write_file(path: str, content: str) -> str:
    """Create or overwrite a text/code file in the workspace.

    Args:
        path: File path relative to the workspace, e.g. "game/main.py".
        content: Full file contents.
    """
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {p}"


def run_command(command: str, timeout_seconds: int = 60) -> str:
    """Run a PowerShell command on the PC, inside the workspace folder. Use for running code, installing packages, git, etc.

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
            cwd=_cfg["workspace"], capture_output=True, text=True,
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


TOOLS = [list_files, read_file, write_file, run_command, open_app, get_time]
REGISTRY = {f.__name__: f for f in TOOLS}
