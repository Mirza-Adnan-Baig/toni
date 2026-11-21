"""Projects (any folder on any drive) and chats (JSON files in each project's .nova folder)."""
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
import uuid

MAX_PREVIEW = 300_000
HIDDEN = {".nova", "__pycache__", ".git", "node_modules", ".venv"}
NO_OPEN = {".exe", ".bat", ".cmd", ".com", ".scr", ".ps1", ".psm1", ".lnk", ".msi", ".vbs", ".vbe", ".js", ".jse",
           ".wsf", ".jar", ".reg", ".hta", ".cpl", ".dll", ".url"}
RESERVED = re.compile(r"^(con|prn|aux|nul|com\d|lpt\d)(\..*)?$", re.I)


def clean_name(name):
    name = re.sub(r"[^\w\- ]", "", name or "", flags=re.U).strip()[:40]
    if not name or RESERVED.match(name):
        raise ValueError("Please use letters, numbers, spaces or dashes.")
    return name


def atomic_write(path, text):
    tmp = path.with_name(path.name + f".{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for i in range(8):  # antivirus / OneDrive can briefly lock files
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.15)
    os.replace(tmp, path)


def _norm(p):
    return os.path.normcase(str(p))


def check_project_folder(path):
    """Refuse folders so broad that the sandbox would protect nothing."""
    p = pathlib.Path(path).expanduser().resolve()
    if str(path).startswith("\\\\"):
        raise ValueError("Network paths are not supported. Map the share to a drive letter first.")
    if p.parent == p:
        raise ValueError("Please choose a folder, not a whole drive.")
    bad = [pathlib.Path.home(), pathlib.Path(os.environ.get("SystemRoot", r"C:\Windows")),
           pathlib.Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
           pathlib.Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
           pathlib.Path(os.environ.get("ProgramData", r"C:\ProgramData"))]
    for b in bad:
        if _norm(p) == _norm(b.resolve()) or _norm(b.resolve()) in [_norm(x) for x in p.parents] and b != pathlib.Path.home():
            raise ValueError("That folder is a system folder. Please choose or create a normal project folder.")
    if "appdata" in [x.lower() for x in p.parts]:
        raise ValueError("Please do not use AppData. Choose a normal project folder.")
    return p


class Store:
    def __init__(self, registry_file, default_parent):
        self.reg = pathlib.Path(registry_file)
        self.parent = pathlib.Path(default_parent)
        self.lock = threading.RLock()
        try:
            self.data = json.loads(self.reg.read_text(encoding="utf-8"))
        except Exception:
            self.data = {"projects": []}
        if not self.data["projects"]:
            self.create("General")

    def _save(self):
        atomic_write(self.reg, json.dumps(self.data, indent=1))

    # ---- projects ----
    def projects(self):
        return [{"name": p["name"], "path": p["path"], "missing": not os.path.isdir(p["path"])}
                for p in self.data["projects"]]

    def path(self, name):
        for p in self.data["projects"]:
            if p["name"] == name:
                if not os.path.isdir(p["path"]):
                    raise ValueError(f"The folder of project '{name}' is missing ({p['path']}). Plug the drive in again or remove the project.")
                return pathlib.Path(p["path"]).resolve()
        raise ValueError(f"No such project: {name}")

    def _unique(self, name):
        names = {p["name"].lower() for p in self.data["projects"]}
        n, i = name, 2
        while n.lower() in names:
            n, i = f"{name} {i}", i + 1
        return n

    def add(self, path, name=None):
        p = check_project_folder(path)
        p.mkdir(parents=True, exist_ok=True)
        with self.lock:
            for q in self.data["projects"]:
                if _norm(q["path"]) == _norm(p):
                    raise ValueError(f"That folder is already the project '{q['name']}'.")
            name = self._unique(clean_name(name or p.name))
            self.data["projects"].append({"name": name, "path": str(p)})
            self._save()
        return name

    def create(self, name, parent=None):
        parent = pathlib.Path(parent) if parent else self.parent
        return self.add(parent / clean_name(name), name)

    def rename(self, old, new):
        with self.lock:
            self.path(old)
            new = clean_name(new)
            if new.lower() != old.lower() and new.lower() in {p["name"].lower() for p in self.data["projects"]}:
                raise ValueError(f"Project '{new}' already exists.")
            for p in self.data["projects"]:
                if p["name"] == old:
                    p["name"] = new
            self._save()
        return new

    def remove(self, name):
        """Only removes it from the list. Files are never deleted."""
        with self.lock:
            self.data["projects"] = [p for p in self.data["projects"] if p["name"] != name]
            self._save()
            if not self.data["projects"]:
                self.create("General")

    def notes(self, project):
        f = self.path(project) / "NOVA.md"
        return f.read_text(encoding="utf-8", errors="replace")[:4000] if f.exists() else ""

    # ---- chats ----
    def _cdir(self, project):
        d = self.path(project) / ".nova" / "chats"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def chats(self, project):
        out = []
        for f in self._cdir(project).glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                out.append({"id": d["id"], "title": d["title"], "updated": d["updated"]})
            except Exception:
                pass
        return sorted(out, key=lambda c: -c["updated"])

    def new_chat(self, project, title="New chat"):
        d = {"version": 1, "id": uuid.uuid4().hex[:10], "title": title, "created": time.time(),
             "updated": time.time(), "log": [], "messages": []}
        self.save_chat(project, d)
        return d

    def load_chat(self, project, cid):
        if not re.fullmatch(r"[0-9a-f]{10}", cid or ""):
            raise ValueError("bad chat id")
        return json.loads((self._cdir(project) / f"{cid}.json").read_text(encoding="utf-8"))

    def save_chat(self, project, d):
        with self.lock:
            atomic_write(self._cdir(project) / f"{d['id']}.json", json.dumps(d, ensure_ascii=False))

    def delete_chat(self, project, cid):
        self.load_chat(project, cid)
        (self._cdir(project) / f"{cid}.json").unlink()

    # ---- files (read-only) ----
    def fpath(self, project, rel=""):
        root = self.path(project)
        rel = (rel or "").replace("/", "\\")
        if ":" in rel or rel.startswith("\\\\"):
            raise ValueError("Path is not allowed.")
        p = (root / rel).resolve()
        if os.path.commonpath([_norm(root), _norm(p)]) != _norm(root):
            raise ValueError("Path is outside the project.")
        if any(part.lower() in HIDDEN or RESERVED.match(part) for part in p.relative_to(root).parts):
            raise ValueError("That path is not available.")
        return p

    def listing(self, project, rel=""):
        p = self.fpath(project, rel)
        items = [{"name": x.name, "dir": x.is_dir()} for x in p.iterdir() if x.name.lower() not in HIDDEN]
        return sorted(items, key=lambda i: (not i["dir"], i["name"].lower()))[:500]

    def read(self, project, rel):
        p = self.fpath(project, rel)
        if p.stat().st_size > MAX_PREVIEW:
            raise ValueError("File too big to preview. Use 'Open' instead.")
        try:
            return p.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("Not a text file. Use 'Open' instead.")

    def open_external(self, project, rel=""):
        p = self.fpath(project, rel)
        if p.is_file() and p.suffix.lower() in NO_OPEN:
            raise ValueError("For safety, programs and scripts are not opened from here.")
        os.startfile(str(p))


def pick_folder(initial=None):
    """Native Windows folder dialog (runs in its own process so it can't freeze the server)."""
    code = ("import tkinter as tk;from tkinter import filedialog as f;r=tk.Tk();r.withdraw();"
            "r.attributes('-topmost',True);r.update();"
            "print(f.askdirectory(parent=r,title='Choose a folder',initialdir=%r or None) or '')" % (initial or ""))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=600)
    return r.stdout.strip().replace("/", "\\")
