@echo off
cd /d "%~dp0"
echo.
echo   1 = English
echo   2 = Deutsch
echo.
choice /c 12 /n /m "Choose 1 or 2: "
if errorlevel 2 goto de
".venv\Scripts\python.exe" -m toni --setlang en
goto end
:de
".venv\Scripts\python.exe" -m toni --setlang de
:end
pause
