@echo off
cd /d "%~dp0"
title Nova (keep this window open)
set HF_HUB_OFFLINE=1
".venv\Scripts\python.exe" -m toni --workspace
pause
