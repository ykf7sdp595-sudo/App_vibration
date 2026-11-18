@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Environnement absent. Suivre les instructions du README pour creer .venv.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 pause
