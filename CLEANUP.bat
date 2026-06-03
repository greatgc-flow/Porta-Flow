@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0_sys\env\python\python.exe"
if not exist "%PY%" (
    echo [Error] Portable Python not found. Run INSTALL.bat first.
    pause
    exit /b 1
)

echo =====================================================
echo  Portable Dev — Cleanup Utility (Python Refactored)
echo =====================================================
echo  1. Light (Safe) - Temp files, caches, old logs
echo  2. Hard        - Tier 1 + Setup archives + venv
echo  3. Reset       - Tier 2 + Portable Runtimes/Tools
echo  4. ZeroBase    - Tier 3 + Workspace + All data (WIPE)
echo =====================================================
set /p CHOICE="Choose cleanup level (1-4, Default=1): "

if "%CHOICE%"=="2" (
    set "TIER=2"
) else if "%CHOICE%"=="3" (
    set "TIER=3"
) else if "%CHOICE%"=="4" (
    set "TIER=4"
) else (
    set "TIER=1"
)

"%PY%" "_sys\cli\cleanup.py" --tier %TIER%

endlocal
pause
