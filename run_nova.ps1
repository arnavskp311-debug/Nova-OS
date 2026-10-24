# NOVA OS: Windows PowerShell Launcher
# Safe AI Desktop Trial Environment

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "          NOVA OS // AI Desktop Trial              " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "[!] Safe Windows Container: Non-destructive desktop trial." -ForegroundColor Green
Write-Host ""

# Verify Python
try {
    $pyVer = python --version 2>&1
    Write-Host "[*] Detected: $pyVer" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org and re-run."
    Read-Host "Press Enter to exit"
    exit 1
}

# Launch NOVA OS
Write-Host "[*] Launching NOVA OS..." -ForegroundColor Cyan
python main.py $args

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[!] Application exited with code $LASTEXITCODE. Check data\logs\nova_os.log" -ForegroundColor Yellow
}
