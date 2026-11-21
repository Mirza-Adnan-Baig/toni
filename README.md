# Nova - a private AI assistant that runs 100% on your own PC

Talk to it, type to it. It answers by voice, writes and runs code, manages files and opens programs. **After installation nothing leaves the PC** - no cloud, no account, no subscription.

- Speaks and understands **English and German** (switch any time)
- Has a **chat window** in your browser (opens automatically) plus voice control
- Everything can be customised: name, wake word, voice, language, speed
- Made for: Windows 11 - RTX 5080 (16 GB) - Core Ultra 7 265K - 64 GB RAM

> The assistant is called **Nova** (you can rename it, see [Customise](#customise)). `toni` is only the name of this project folder.

---

## Part 1 - Install (about 30-60 minutes, mostly downloading)

You need: Windows 11, a working internet connection **for the install only**, and about **25 GB free disk space**. No programming knowledge needed. Just do the steps in order.

### Step 1 - Update the graphics driver
1. Open the Start menu, type **NVIDIA App**, open it (or go to https://www.nvidia.com/drivers).
2. Install the newest **Game Ready / Studio driver**.
3. Restart the PC.

### Step 2 - Open PowerShell
PowerShell is a text window where you type commands. You will copy-paste a few lines.
1. Press the **Windows key**.
2. Type `PowerShell`.
3. Press **Enter**. A blue (or black) window opens.

How to paste: copy a command from this page, then **right-click** inside the PowerShell window (or press Ctrl+V), then press **Enter**.

### Step 3 - Install Git
Git is a free tool that downloads projects from GitHub.

Paste this and press Enter:
```powershell
winget install --id Git.Git -e --source winget
```
- If it asks to accept terms, type `Y` and press Enter.
- When it says **Successfully installed**, **close the PowerShell window completely** and open a new one (Step 2 again). This is required so Windows notices the new program.

Check that it worked, paste:
```powershell
git --version
```
You should see something like `git version 2.xx`. If you see "not recognized", restart the PC and try again. If `winget` itself is not recognized, install Git manually from https://git-scm.com/download/win (click through with the default options), then open a new PowerShell.

### Step 4 - Download Nova ("clone" the project)
Paste these two lines one after another (each followed by Enter):
```powershell
git clone https://github.com/Mirza-Adnan-Baig/toni.git C:\Nova
```
```powershell
cd C:\Nova
```
This creates the folder `C:\Nova` with all files. (If a Windows window asks you to sign in to GitHub, close it: the project is public and needs no login. If git complains about "dubious ownership", run `git config --global --add safe.directory C:/Nova` and try again.)

### Step 5 - Run the installer
Still in PowerShell, paste:
```powershell
& ".\Install Nova.bat"
```
(Or open the folder with `explorer C:\Nova` and double-click **Install Nova.bat**.)

What happens now - **just wait**, it says what it is doing in 7 steps:
1. Checks the graphics card
2. Installs Python 3.11
3. Installs Ollama (the engine that runs the AI)
4. Downloads the AI brain (**13 GB** - this is the long part)
5. Installs Nova's programs
6. Downloads voices and the hearing model
7. Puts shortcuts on your Desktop and makes Nova start quietly when Windows starts

Good to know:
- Windows may ask "Do you want to allow this app to make changes?" -> **Yes**.
- If a blue "Windows protected your PC" box appears -> **More info** -> **Run anyway**.
- Never close the window while it runs. If it fails or you lose internet, just run Step 5 again; it continues where it stopped.
- At the end it prints **Done!**

### Step 6 - Test everything
1. Double-click **Nova check** on the Desktop.
2. You should **hear a voice** greeting you. Then speak a sentence into the microphone. It prints what it heard, then the AI answers.
3. If Windows asks for microphone access, allow it (Settings -> Privacy & security -> Microphone -> allow desktop apps).

The first AI answer takes up to a minute (the brain loads into the GPU). After that it is fast.

---

## Part 2 - Use it

Nova has **two separate screens**. Both are web pages in your browser, served only by your own PC.

### 1. Companion (the "talk to someone" screen) - `Nova` shortcut
A glowing orb that listens, thinks and speaks. This is your Jarvis-style assistant.
- Say **"Nova, ..."**, e.g. "Nova, what time is it?" / "Nova, make a number guessing game in Python and run it."
- Nova keeps listening ~8 seconds after answering, so you can carry on without repeating the name. Say "thanks" or "stop" to end.
- What you said and what Nova answers appear as large captions. **Transcript** shows the whole conversation. You can also type in the box at the bottom.
- Bottom left: microphone on/off. Bottom right: stop the current task. Top: **EN/DE** language switch.
- Orb colours: green = listening, yellow = thinking, blue = speaking.
- Nova **starts by itself when Windows starts**, in the background, and listens quietly. The `Nova` shortcut just shows the screen.
- The voice conversation is its own permanent chat (inside a project called **Voice**), separate from your work chats.

### 2. Workspace (like Claude Code) - `Nova Workspace` shortcut
For real work: projects, many chats, files.
- **Left:** your **projects**, each with its own chats. `+ New` creates a project, `Add folder` uses a folder you already have. The `+` next to a project starts a new chat.
- **Middle:** the chat. You see every step Nova takes (files written, commands run) live. **Stop** cancels a running task.
- **Right, Files:** the project's files (read-only view; `Open` opens a file in Windows, `Open folder` opens Explorer). **Right, Settings:** language, name, wake word, voices and more.
- Chats are **saved automatically** and are still there after a restart, with their full history.
- Before running any command on the PC, Nova asks (Allow/Deny button, or "yes"/"no" by voice).

### Choose where projects live (not just drive C:)
Projects can be **any folder on any drive**, for example `D:\Nova Projects\Homework`.
- `+ New` asks for a name, then asks where to create it. Choose Cancel at that question to pick another place such as `D:\` in a normal Windows folder window.
- `Add folder` turns an existing folder into a project.
- Settings -> **Folder for NEW projects** sets the default location (click **Browse**).
- Each project's chats are stored inside the project folder (hidden `.nova` folder), so moving or backing up the folder keeps everything.
- Removing a project (`x`) only removes it from the list. **Your files are never deleted.** Whole drives, Windows folders, Program Files and AppData are refused for safety.
- Optional: put a file named `NOVA.md` in a project folder with notes (goals, style). Nova reads it as background info.

### Always listening, but light on the PC
- A tiny speech model (about 75 MB, 2 CPU threads) only wakes up when it hears someone talk; silence costs almost nothing. The bigger model and the AI only run after your wake word.
- The AI model is loaded into the graphics card **when you say the name** and leaves again after 10 idle minutes, so games get the full GPU back. (The first answer after a long pause takes a few seconds longer.)
- Nova runs at low priority, so it does not slow down other programs.
- To stop it completely: Settings -> **Quit Nova**, or the `Stop Nova` shortcut. To stop it starting with Windows: Settings -> untick **Start Nova when Windows starts**.
- No browser page open? Nova still listens. A log is written to `C:\Nova\logs\nova.log`.
- No microphone yet after boot? Nova retries every 10 seconds by itself.

---

## Language: English <-> German

Install and test in English (default). To switch to German, any of these:
- In the Companion screen: the **EN/DE** button. Or in the Workspace: **Settings -> Language -> Deutsch -> Save and apply** (on a small window, click the **Settings** button top-right).
- Or double-click the **Nova language** shortcut and press 2 (Deutsch) or 1 (English).

In German, Nova listens to German, answers in German and uses a German voice. The wake word stays the same ("Nova"). Switching takes a few seconds.

---

## Customise

Everything below can be changed in the Workspace under **Settings -> Save and apply**.

### Change the wake word (the name you call)
1. Settings -> **Name** = what Nova calls itself, e.g. `Atlas`.
2. Settings -> **Wake words** = how it might be *written* when heard, separated by commas, e.g. `atlas, atlas, atlass`.
3. Save and apply, then say "Atlas, hello".

Tips: pick a name with 2-3 clear syllables that is not an everyday word ("Nova", "Atlas", "Friday" work well). If it does not react, look at the grey `heard: ...` lines in the chat to see how your word was understood, and add that spelling to the wake words. English and German hearing may spell a name differently, so add both.

### Change the voice
- Workspace -> Settings -> **English voice** / **German voice**. Press **Listen** next to a dropdown to hear the voice before choosing, then **Save and apply**.
- Installed voices (about 40):
  - **Kokoro** (English only, the most natural-sounding): many female and male voices, US and UK. Default: Heart.
  - **Piper** (English and German): e.g. `en_US-lessac-high`, `en_GB-cori-high`, `de_DE-kerstin-medium`, `de_DE-ramona-low`, `de_DE-thorsten-high` (male), `de_DE-mls-medium`.
  - **Chatterbox** (English and German, optional): the most human-sounding, but big and slow (about 7 s per sentence on a mid-range GPU, uses ~3.5 GB of graphics memory, so it competes with the AI model). To add it, double-click **Install Chatterbox voices.bat** (about 6 GB download, 10-30 minutes), restart Nova, then pick "Chatterbox" in the voice dropdown. Not tested on the RTX 5080 yet.
  - Without Chatterbox, German voices are Piper only, which sounds more synthetic than Kokoro's English.
  - Good to know: every voice has trade-offs. Piper is fast and light, Kokoro is natural but English only, Chatterbox is the most human but slow. Use **Listen** to compare.
- **Speaking speed** slider (1.0 is normal).
- More Piper voices: listen at https://rhasspy.github.io/piper-samples/ , then type the voice name (e.g. `de_DE-thorsten-high`) into **Add another Piper voice** in Settings and press Add. Needs internet once.

### Other options
- **AI model:** any model from https://ollama.com/library . Example: `ollama pull qwen3:14b` in PowerShell, then type `qwen3:14b` in Settings. Models up to ~14 GB run fast on the 5080. (Default `gpt-oss:20b` is tested for tool use; others are optional and may behave differently.)
- **Ask before running commands:** untick only if you trust it completely.
- **Start listening automatically:** on by default.

### Advanced: the settings file
Settings are saved in `C:\Nova\config.json`. You can also edit it in Notepad (all keys and defaults are in `toni/config.py`). Example:
```json
{ "language": "de", "name": "Atlas", "wake_words": ["atlas"], "speed": 1.1 }
```

---

## Troubleshooting

| Problem | What to do |
|---|---|
| Installer stops with an error | Read the red text, check internet, run `Install Nova.bat` again |
| `winget` / `git` "not recognized" | Close PowerShell and open a new one; if still failing, restart the PC |
| Nova does not react to its name | Open the chat page and look at the `heard:` lines; add the spelling you see to **Wake words**; speak closer to the mic |
| It hears me but nothing is spoken | Windows Sound settings: set the right default speakers; run **Nova check** |
| Wrong microphone | Windows Sound settings -> Input -> pick your mic as default |
| First answer is very slow | Normal once: the AI brain loads into the GPU |
| "Ollama is not running" | Start **Ollama** from the Start menu, then restart Nova |
| Page does not open | Browse to `http://127.0.0.1:8765` while the black window is open |
| Slow / errors while gaming | Close the game; the AI uses ~14 GB of the 16 GB GPU memory |
| German answers sound odd | Try a different model (see "AI model") or speak in short sentences |

## Update later
```powershell
cd C:\Nova
git pull
```
then run `Install Nova.bat` again.

## Remove everything
Delete the `C:\Nova` folder and the Desktop shortcuts. Uninstall **Ollama** and **Python 3.11** from Settings -> Apps if you want (the AI model files live in `C:\Users\<name>\.ollama`).

## How it works (for the curious)
Microphone -> hearing (faster-whisper, on the CPU) -> brain (Ollama + `gpt-oss:20b`, on the GPU, with tools for files/commands/apps) -> voice (Piper) -> speakers. The chat page is a tiny local web server that only accepts connections from this PC. Nothing is sent anywhere.
