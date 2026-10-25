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

:: Ensure Ollama AI daemon is active
tasklist /fi "imagename eq ollama.exe" 2>nul | findstr /i "ollama.exe" >nul
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        echo [*] Auto-starting Ollama AI daemon...
        start "" /b "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve >nul 2>&1
    )
)

:: Run NOVA OS
echo [*] Launching NOVA OS...
python main.py %*

if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with an error. Check data\logs\nova_os.log.
    pause
)
