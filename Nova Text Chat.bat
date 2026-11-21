@echo off
cd /d "%~dp0"
title Nova (text)
set HF_HUB_OFFLINE=1
".venv\Scripts\python.exe" -m toni --text
pause
