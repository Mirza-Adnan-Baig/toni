"""Start Nova silently when Windows starts (Startup-folder shortcut, no admin rights needed)."""
import os
import pathlib
import subprocess
import sys

from .config import ROOT


def _lnk():
    return pathlib.Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup/Nova.lnk"


def enabled():
    return _lnk().exists()


def set_enabled(on):
    lnk = _lnk()
    if not on:
        lnk.unlink(missing_ok=True)
        return
    exe = pathlib.Path(sys.executable)
    exe = exe.with_name("pythonw.exe") if exe.with_name("pythonw.exe").exists() else exe
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');$s.TargetPath='%s';"
          "$s.Arguments='-m toni --background';$s.WorkingDirectory='%s';$s.WindowStyle=7;$s.Save()") % (lnk, exe, ROOT)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
