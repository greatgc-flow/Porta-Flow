:: ================================================================
:: claude-status.bat  -  Single source of truth for Claude status
:: ================================================================
@echo off
setlocal enabledelayedexpansion

:: Ensure claude.cmd is findable
set "NPM_GLOBAL=%~dp0..\env\nodejs\npm-global"
if exist "%NPM_GLOBAL%\claude.cmd" (
    set "PATH=%NPM_GLOBAL%;%PATH%"
)

set "_STATUS_FILE=%~dp0status.json"
for /f "delims=" %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddHHmmss"') do set "_DT=%%I"

set "CLAUDE_MODE=OFF"
set "CLAUDE_OFF_REASON="

where.exe claude > nul 2>&1
if errorlevel 1 (
    set "CLAUDE_OFF_REASON=not_installed"
    goto :WRITE_STATUS
)

set "_CLAUDE_CONFIG=%~dp0config\.claude.json"
if not exist "%_CLAUDE_CONFIG%" (
    set "CLAUDE_OFF_REASON=not_authenticated"
    goto :WRITE_STATUS
)

:: Check if .claude.json contains a session token (simplified check via regex for robustness)
powershell -NoProfile -Command "if (Select-String -Path '%_CLAUDE_CONFIG:\=\\%' -Pattern '\"oauthAccount\"' -Quiet) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    set "CLAUDE_OFF_REASON=session_expired"
    goto :WRITE_STATUS
)

set "CLAUDE_MODE=ON"
set "CLAUDE_OFF_REASON=ready"

:WRITE_STATUS
set "_INSTALLED=false"
where.exe claude > nul 2>&1
if not errorlevel 1 set "_INSTALLED=true"
set "_AUTHED=false"
if "%CLAUDE_MODE%"=="ON" set "_AUTHED=true"

powershell -NoProfile -Command "$f='%_STATUS_FILE:\=\\%'; $json=[ordered]@{ mode='%CLAUDE_MODE%'; reason='%CLAUDE_OFF_REASON%'; installed=[bool]::Parse('%_INSTALLED%'); authenticated=[bool]::Parse('%_AUTHED%'); last_check='%_DT%' }; [System.IO.File]::WriteAllText($f, ($json | ConvertTo-Json), (New-Object System.Text.UTF8Encoding($false)))"

echo Claude Status: %CLAUDE_MODE% (%CLAUDE_OFF_REASON%)
endlocal
