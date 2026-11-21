# Toni - a private, offline AI assistant for your PC

Toni listens for its name, talks back, writes and runs code, opens apps and manages files. **After install, nothing leaves your PC.** No cloud, no account, no subscription.

Built for: Windows 11, NVIDIA RTX 5080 (16 GB), Core Ultra 7 265K, 64 GB RAM.

## What's inside (all free, all local)

| Job | Tool | Why |
|---|---|---|
| Brain + coding | [Ollama](https://ollama.com) running `gpt-oss:20b` | Fits the 16 GB GPU fully (very fast), strong at tool use and coding |
| Hearing | faster-whisper `small.en` (on CPU) | Accurate, leaves the GPU free for the brain |
| Voice | Kokoro (British male "George") | Natural, runs on CPU |
| Hands | `toni/tools.py` | Read/write files, run commands, open apps |

Why not Hermes Agent? Its Windows support is still beta and goes through WSL2, which is fragile for a beginner. Toni is a small, self-contained agent that does the same job on plain Windows.

## Install (about 30 minutes, mostly downloading)

1. Make sure Windows is updated and the PC has **~20 GB free** on the drive and internet.
2. Install the latest **NVIDIA driver** (NVIDIA App or nvidia.com/drivers), restart.
3. Download this project: green **Code** button on GitHub, **Download ZIP**, then right-click the ZIP, **Extract All** (put it somewhere simple, e.g. `C:\Toni`). Or with git:
   ```powershell
   git clone https://github.com/Mirza-Adnan-Baig/toni.git C:\Toni
   ```
4. Open the folder and **double-click `Install Toni.bat`**. If Windows warns "unknown publisher", click **More info**, then **Run anyway**. Say yes to any installer prompts.
5. Wait until it prints **Done!**. If it fails, read the message and double-click it again; it resumes where it stopped.

## Use it

- Desktop shortcut **Toni check** (first time): tests speakers, microphone and brain. Allow microphone access if Windows asks (Settings > Privacy > Microphone).
- Desktop shortcut **Toni**: starts voice mode. Say **"Toni, ..."**
  - "Toni, what time is it?"
  - "Toni, make a snake game in Python and run it."
  - "Toni, open Notepad."
  - "Toni, list the files in my workspace."
  - After an answer it keeps listening ~8 seconds, so you can just keep talking. Say "thanks" or "stop" to end.
- Desktop shortcut **Toni (text chat)**: same assistant, typed.
- Toni's files live in `C:\Users\<you>\Toni\workspace`. It can only read/write there. Before running any PC command it **asks "Shall I?"**; answer "yes" or "no".

## Make it yours

Create a file `config.json` in the Toni folder (it's ignored by git):

```json
{
  "name": "Friday",
  "wake_words": ["friday"],
  "voice": "af_heart",
  "ask_before_commands": true
}
```

Voices: `bm_george`, `bm_lewis`, `am_michael`, `am_adam`, `af_heart`, `af_bella`, `bf_emma`. Restart Toni after changes.

## Troubleshooting

| Problem | Fix |
|---|---|
| Install stops with an error | Run `Install Toni.bat` again |
| Toni doesn't react to its name | Run **Toni check**, see what it "Heard". Speak clearly, closer to the mic, or add the misheard spelling to `wake_words` |
| Wrong mic/speaker | Set the right default device in Windows Sound settings |
| First answer takes a minute | The brain is loading into the GPU. Later answers are fast |
| "Ollama is not running" | Open **Ollama** from the Start menu, retry |
| Slow or crashes while gaming | Close the game; the brain needs ~14 GB of the GPU's 16 GB |
| Want a different brain | Run `ollama pull devstral-small-2` in PowerShell (coding specialist, tighter fit), then set `"model"` in `config.json` |

## Update later

```powershell
cd C:\Toni
git pull
```

Then run `Install Toni.bat` again.

## Safety notes

- Toni can run commands you approve. Don't say yes to things you don't understand.
- Dangerous commands (disk format, registry delete, etc.) are always refused.
- Voice processing happens on this PC; nothing is uploaded.
