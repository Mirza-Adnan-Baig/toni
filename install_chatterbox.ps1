# Optional: adds the Chatterbox voices (very human, but big and slow). Needs internet. Safe to run again.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Run 'Install Nova.bat' first." }
$env:HF_HOME = Join-Path $PSScriptRoot "models\hf"
Write-Host "Installing Chatterbox voices (about 6 GB download, 10-30 minutes)..." -ForegroundColor Cyan
& $py -m pip install uv
$uv = Join-Path $PSScriptRoot ".venv\Scripts\uv.exe"
& $uv pip install --python $py torch torchaudio --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw "PyTorch download failed. Run this again." }
Set-Content (Join-Path $env:TEMP "nova_ovr.txt") "torch>=2.7`ntorchaudio>=2.7"
& $uv pip install --python $py chatterbox-tts --override (Join-Path $env:TEMP "nova_ovr.txt")
if ($LASTEXITCODE -ne 0) { throw "Chatterbox install failed. Run this again." }
Write-Host "Downloading the voice model..." -ForegroundColor Cyan
& $py -c "from chatterbox.mtl_tts import ChatterboxMultilingualTTS as C; C.from_pretrained(device='cpu')"
if ($LASTEXITCODE -ne 0) { throw "Model download failed. Run this again." }
Write-Host "Done. Restart Nova, then pick a 'Chatterbox' voice in Settings." -ForegroundColor Green
