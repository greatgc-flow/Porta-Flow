@echo off
setlocal

:: ================================================================
:: gem.bat  --  Direct Gemini chat, resumes Claude's active session
::
:: Usage:
::   gem              -> REPL, continues Claude's Gemini session
::   gem -n           -> REPL, new fresh session
::   gem "message"    -> one-shot (continues Claude's session)
::   gem -n "message" -> one-shot (new session)
:: ================================================================

:: Ensure npm-global (gemini.cmd) is in PATH
for %%I in ("%~dp0..") do set "_SYSDIR=%%~fI"
if exist "%_SYSDIR%\env\nodejs\npm-global\gemini.cmd" (
    set "PATH=%_SYSDIR%\env\nodejs\npm-global;%PATH%"
)

:: Verify gemini is installed
where gemini >nul 2>&1
if errorlevel 1 (
    echo [gem] ERROR: gemini CLI not found.
    echo       Check: %_SYSDIR%\env\nodejs\npm-global\gemini.cmd
    exit /b 1
)

:: Resolve session ID file
if defined GEMINI_DIR (
    set "_SID_FILE=%GEMINI_DIR%\session-id.txt"
) else (
    set "_SID_FILE=%_SYSDIR%\gemini\session-id.txt"
)

:: Parse -n flag (new session)
set "_NEW=0"
set "_FIRST=%~1"
if /i "%_FIRST%"=="-n" (
    set "_NEW=1"
    shift
)

:: Build session flag
set "_SESSION_FLAG="
if "%_NEW%"=="0" (
    if exist "%_SID_FILE%" (
        set /p "_SID=" < "%_SID_FILE%"
        if defined _SID set "_SESSION_FLAG=--resume %_SID%"
    )
)

if "%~1"=="" (
    :: Interactive REPL
    if defined _SESSION_FLAG (
        echo [gem] Resuming Claude's Gemini session...
    ) else (
        echo [gem] Starting new Gemini session...
    )
    gemini %_SESSION_FLAG%
) else (
    :: One-shot: pass message via env var (special-char safe)
    set "_GEM_MSG=%*"
    powershell -NoProfile -Command "Write-Output $env:_GEM_MSG" | gemini %_SESSION_FLAG% --approval-mode plan -p "Respond to the message." -o text
)

endlocal