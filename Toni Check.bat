@echo off
cd /d "%~dp0"
title Toni check
set HF_HUB_OFFLINE=1
".venv\Scripts\python.exe" -m toni --check
pause
