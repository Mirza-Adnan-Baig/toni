# Nova installer - run by double-clicking "Install Nova.bat". Safe to run again if anything fails.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Model = "gpt-oss:20b"
$Py311 = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

function Step($n, $msg) { Write-Host ""; Write-Host "[$n/7] $msg" -ForegroundColor Cyan }
function Need-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget not found. Open the Microsoft Store, update 'App Installer', then run this again."
    }
}
function Find-Ollama {
    $c = Get-Command ollama -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $p = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $p) { return $p }
    return $null
}
function Download($url, $dest) {
    if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 1MB)) { Write-Host "  already have $(Split-Path $dest -Leaf)"; return }
    curl.exe -L -C - --fail -o $dest $url
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $url" }
}

Write-Host "=== Installing Nova (offline AI assistant) ===" -ForegroundColor Green
Write-Host "Needs about 20 GB free disk and a one-time internet connection. Takes 15-40 minutes."

Step 1 "Checking your graphics card"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
} else {
    Write-Warning "No NVIDIA driver found. Install the latest driver from nvidia.com/drivers (or the NVIDIA App), restart, then run this again."
    throw "NVIDIA driver missing"
}

Step 2 "Installing Python 3.11"
if (-not (Test-Path $Py311)) {
    Need-Winget
    winget install -e --id Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements
}
if (-not (Test-Path $Py311)) { throw "Python 3.11 did not install. Install it manually from python.org, then run this again." }

Step 3 "Installing Ollama (runs the AI brain)"
$ollama = Find-Ollama
if (-not $ollama) {
    Need-Winget
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    $ollama = Find-Ollama
}
if (-not $ollama) { throw "Ollama did not install. Download it from ollama.com, install it, then run this again." }
# Faster replies: flash attention, and keep the model loaded in memory.
foreach ($kv in @(@("OLLAMA_FLASH_ATTENTION", "1"), @("OLLAMA_KEEP_ALIVE", "10m"))) {
    [Environment]::SetEnvironmentVariable($kv[0], $kv[1], "User")
    Set-Item -Path "Env:$($kv[0])" -Value $kv[1]
}
Get-Process "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
$up = $false
for ($i = 0; $i -lt 30; $i++) {
    try { Invoke-WebRequest "http://127.0.0.1:11434/api/version" -UseBasicParsing | Out-Null; $up = $true; break } catch { Start-Sleep -Seconds 1 }
}
if (-not $up) { throw "Ollama did not start. Restart the PC and run this again." }

Step 4 "Downloading the AI model $Model (about 13 GB - be patient)"
& $ollama pull $Model
if ($LASTEXITCODE -ne 0) { throw "Model download failed. Check your internet and run this again." }

Step 5 "Setting up the assistant's programs"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $Py311 -m venv .venv }
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Package install failed. Check your internet and run this again." }

Step 6 "Downloading voice and hearing models (about 1 GB)"
New-Item -ItemType Directory -Force -Path "models" | Out-Null
New-Item -ItemType Directory -Force -Path "models\piper" | Out-Null
foreach ($v in @("en_US-amy-medium", "en_GB-jenny_dioco-medium", "de_DE-kerstin-medium", "de_DE-ramona-low")) {
    if (-not (Test-Path "models\piper\$v.onnx.json")) {
        $ErrorActionPreference = "Continue"   # piper prints progress on stderr
        & $venvPy -m piper.download_voices $v --download-dir "models\piper" 2>&1 | Out-Null
        $ErrorActionPreference = "Stop"
        if (-not (Test-Path "models\piper\$v.onnx.json")) { throw "Voice download failed ($v). Run this again." }
    }
    Write-Host "  voice ready: $v"
}
if (-not (Test-Path "models\whisper-tiny\model.bin")) {
    & $venvPy -c "from faster_whisper import download_model; download_model('tiny', output_dir=r'models\whisper-tiny')"
    if ($LASTEXITCODE -ne 0) { throw "Wake-word model download failed. Run this again." }
}
if (-not (Test-Path "models\whisper-small\model.bin")) {
    & $venvPy -c "from faster_whisper import download_model; download_model('small', output_dir=r'models\whisper-small')"
    if ($LASTEXITCODE -ne 0) { throw "Hearing model download failed. Run this again." }
}

Step 7 "Creating shortcuts and auto-start"
$desk = [Environment]::GetFolderPath("Desktop")
$sh = New-Object -ComObject WScript.Shell
foreach ($pair in @(@("Nova", "Start Nova.bat"), @("Nova Workspace", "Nova Workspace.bat"), @("Nova text chat", "Nova Text Chat.bat"), @("Nova check", "Nova Check.bat"), @("Nova language", "Language.bat"), @("Stop Nova", "Stop Nova.bat"))) {
    $lnk = $sh.CreateShortcut("$desk\$($pair[0]).lnk")
    $lnk.TargetPath = Join-Path $PSScriptRoot $pair[1]
    $lnk.WorkingDirectory = $PSScriptRoot
    $lnk.Save()
}
# Start silently (no window) every time you log in to Windows
$startup = [Environment]::GetFolderPath("Startup")
$lnk = $sh.CreateShortcut("$startup\Nova.lnk")
$lnk.TargetPath = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
$lnk.Arguments = "-m toni --background"
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.WindowStyle = 7
$lnk.Save()

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "1. Double-click 'Nova check' on the Desktop to test speakers, mic and brain."
Write-Host "2. Then double-click 'Nova' and say the name, e.g. 'Nova, what time is it?'"
Write-Host "3. 'Nova Workspace' opens projects, chats and files. Nova also starts by itself when Windows starts."
