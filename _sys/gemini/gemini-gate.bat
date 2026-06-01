@echo off
:: ================================================================
:: gemini-gate.bat THRESHOLD
:: Reads _sys\gemini\config.json, exits 0 if ratio >= THRESHOLD.
:: Usage: call gemini-gate.bat 7
:: ================================================================
if "%~1"=="" exit /b 0

if defined GEMINI_DIR (set "_GD=%GEMINI_DIR%") else (for %%I in ("%~dp0.") do set "_GD=%%~fI")
set "_CFG=%_GD%\config.json"

if not exist "%_CFG%" exit /b 1

powershell -NoProfile -Command "try { $r=[int](Get-Content '%_CFG:\=\\%' -Raw | ConvertFrom-Json).ratio; if($r -ge [int]'%~1'){exit 0}else{exit 1} } catch { exit 1 }"
set _exit=%errorlevel%
set "_GD="
set "_CFG="
exit /b %_exit%
