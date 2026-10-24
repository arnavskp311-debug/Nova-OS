@echo off
title NOVA OS Launcher
cd /d "%~dp0"

echo ===================================================
echo           NOVA OS // AI Desktop Trial
echo ===================================================
echo [!] Safe Windows Container: Non-destructive trial.
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and re-run.
    pause
    exit /b 1
)

:: Run NOVA OS
echo [*] Launching NOVA OS...
python main.py %*

if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with an error. Check data\logs\nova_os.log.
    pause
)
