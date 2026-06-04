@echo off
:: ================================================================
:: gemini-set-ratio.bat [0-10]
::
:: Sets GEMINI_RATIO in _sys\gemini\config.json
::
:: Usage:
::   gemini-set-ratio.bat 10   -> full delegation (everything via Gemini)
::   gemini-set-ratio.bat 7    -> delegate non-trivial tasks
::   gemini-set-ratio.bat 5    -> consult for complex decisions only
::   gemini-set-ratio.bat 0    -> Gemini OFF
::
:: Ratio levels:
::   0     Gemini OFF (no auto calls)
::   1-4   Manual only (no auto-consult)
::   5-6   Consult for complex analysis / design decisions
::   7-9   Mandatory consult before any non-trivial work
::   10    Full delegation: every read/write/analysis goes through Gemini first
:: ================================================================

if not defined GEMINI_DIR for %%I in ("%~dp0.") do set "GEMINI_DIR=%%~fI"
set "_GD=%GEMINI_DIR%"
set "_CFG=%_GD%\config.json"

if "%~1"=="" (
    echo Usage: gemini-set-ratio.bat [0-10]
    echo.
    echo Current config:
    type "%_CFG%"
    exit /b 0
)

set "_N=%~1"
if %_N% LSS 0 set "_N=0"
if %_N% GTR 10 set "_N=10"

powershell -NoProfile -Command "$n=[int]'%_N%'; try { $cfg=Get-Content '%_CFG:\=\\%' -Raw|ConvertFrom-Json } catch { $cfg=[pscustomobject]@{ratio=5;review_interval_min=5;last_review_ts=$null} }; $cfg|Add-Member -NotePropertyName ratio -NotePropertyValue $n -Force; [System.IO.File]::WriteAllText('%_CFG:\=\\%',($cfg|ConvertTo-Json -Depth 3),(New-Object System.Text.UTF8Encoding($false)))"

echo [gemini-set-ratio] GEMINI_RATIO set to %_N%
if "%_N%"=="0"  echo   [Gemini OFF - no auto calls]
if "%_N%"=="10" echo   [Full delegation - all reads/writes/analysis go through Gemini first]
type "%_CFG%"

set "_GD=" & set "_CFG=" & set "_N="
