@echo off
setlocal enabledelayedexpansion
:: check-portability.bat  -  Axis-A: Full Portability & Corpus Scan
::
:: This script performs a full scan of the workspace to ensure portability compliance
:: and consistency across all environments.

for %%I in ("%~dp0..\..") do set "BASE_DIR=%%~fI"
set "OUT_FILE=%BASE_DIR%\_archive\portability-audit.json"

echo [portability-scan] Starting Axis-A Full Audit...

:: Check if Gemini is ON
set "GEMINI_MODE=OFF"
if exist "%BASE_DIR%\_sys\gemini\status.json" (
    for /f "tokens=*" %%a in ('python -c "import json,sys; d=json.load(open(r'%BASE_DIR%\_sys\gemini\status.json', encoding='utf-8-sig')); print(d.get('mode','OFF'))" 2^>nul') do set "GEMINI_MODE=%%a"
)

if "!GEMINI_MODE!"=="OFF" (
    echo [portability-scan] Gemini is OFF. Performing basic structural audit...
    :: Basic local audit logic here
    echo {"status": "UNKNOWN", "reason": "Gemini OFF"} > "%OUT_FILE%"
    call "%BASE_DIR%\_sys\hooks\collab-log.bat" "Axis-A" "check-portability.bat" "REFUSED" "Gemini OFF - Basic scan only"
    goto :done
)

echo [portability-scan] Gemini is ON. Performing deep corpus scan...
:: Deep scan logic via Gemini CLI
gemini -p "Analyze the entire codebase for portability issues (hardcoded paths, environment dependencies, MECE violations). Output a structured JSON report." > "%OUT_FILE%"

if errorlevel 1 (
    echo [portability-scan] ERROR: Gemini scan failed.
    call "%BASE_DIR%\_sys\hooks\collab-log.bat" "Axis-A" "check-portability.bat" "FAIL" "Error: Gemini scan failed"
    exit /b 1
)

call "%BASE_DIR%\_sys\hooks\collab-log.bat" "Axis-A" "check-portability.bat" "OK" "Output: %OUT_FILE%"

:done
echo [portability-scan] Audit complete. Report saved to: %OUT_FILE%
endlocal
