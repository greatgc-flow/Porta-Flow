@echo off
:: ================================================================
:: claude-gate.bat
:: Simple check if Claude is available (ON).
:: Usage: call claude-gate.bat
:: ================================================================
set "_SD=%~dp0"
set "_STATUS=%_SD%status.json"

if not exist "%_STATUS%" (
    call "%_SD%claude-status.bat" > nul
)

powershell -NoProfile -Command "try { $m=(Get-Content '%_STATUS:\=\\%' -Raw | ConvertFrom-Json).mode; if($m -eq 'ON'){exit 0}else{exit 1} } catch { exit 1 }"
exit /b %errorlevel%
