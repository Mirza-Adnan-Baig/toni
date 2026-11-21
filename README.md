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
7. Puts shortcuts on your Desktop

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

Double-click **Nova** on the Desktop. A black window opens (keep it open - it is the engine) and your browser shows the chat page at `http://127.0.0.1:8765`.

- **Talk:** say **"Nova, ..."**, e.g. "Nova, what time is it?" / "Nova, make a number guessing game in Python and run it." / "Nova, open the calculator."
  After an answer Nova keeps listening ~8 seconds, so you can continue without the name. Say "thanks" or "stop" to end.
- **Type:** use the box at the bottom of the page. Tick **read aloud** to hear typed answers.
- **Start/Stop listening:** top-right button. The coloured dot shows the state (green = listening, yellow = thinking, blue = speaking).
- **Safety:** before running any command on the PC, Nova asks. By voice, answer "yes"/"no" (or "ja"/"nein"); in the browser, click Allow/Deny.
- Nova works in the folder `C:\Users\<name>\Nova\workspace` (its projects appear there).
- No browser? Use the **Nova (text chat)** shortcut.
- To quit: close the black window.

---

## Language: English <-> German

Install and test in English (default). To switch to German, any of these:
- In the chat page: **Settings -> Language -> Deutsch -> Save and apply** (on a small window, click the **Settings** button top-right).
- Or double-click the **Nova language** shortcut and press 2 (Deutsch) or 1 (English).

In German, Nova listens to German, answers in German and uses a German voice. The wake word stays the same ("Nova"). Switching takes a few seconds.

---

## Customise

Everything below can be changed in the chat page under **Settings -> Save and apply**.

### Change the wake word (the name you call)
1. Settings -> **Name** = what Nova calls itself, e.g. `Atlas`.
2. Settings -> **Wake words** = how it might be *written* when heard, separated by commas, e.g. `atlas, atlas, atlass`.
3. Save and apply, then say "Atlas, hello".

Tips: pick a name with 2-3 clear syllables that is not an everyday word ("Nova", "Atlas", "Friday" work well). If it does not react, look at the grey `heard: ...` lines in the chat to see how your word was understood, and add that spelling to the wake words. English and German hearing may spell a name differently, so add both.

### Change the voice
- Settings -> **English voice** / **German voice** (dropdowns). Included, all female:
  - English: `en_US-amy-medium` (default), `en_GB-jenny_dioco-medium`
  - German: `de_DE-kerstin-medium` (default), `de_DE-ramona-low`
- **Speaking speed** slider (1.0 is normal).
- More voices (male ones, other accents): browse https://rhasspy.github.io/piper-samples/ , then in PowerShell:
  ```powershell
  cd C:\Nova
  .venv\Scripts\python.exe -m piper.download_voices de_DE-thorsten-medium --download-dir models\piper
  ```
  Reload the chat page; the new voice appears in the dropdown. (Needs internet once.)

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
