@echo off
setlocal
:: launch.bat - Registry command relay to start.bat
:: Called by: Windows Explorer right-click menu (via registry)

set "SYS_DIR=%~dp0.."
set "START_BAT=%SYS_DIR%\start.bat"

if "%~1"=="" (
    start cmd.exe /c "call \"%START_BAT%\" || pause"
) else (
    start cmd.exe /c "call \"%START_BAT%\" \"%~1\" || pause"
)

endlocal
