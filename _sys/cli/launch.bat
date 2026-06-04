@echo off
setlocal
:: launch.bat - Simple relay to start.bat
:: Minimalist structure to ensure stability.

set "SYS_DIR=%~dp0.."
set "START_BAT=%SYS_DIR%\start.bat"

:: Directly call start.bat and pause. No 'start' command to avoid hiding errors.
call "%START_BAT%" %*

if errorlevel 1 (
    echo.
    echo [ERROR] Execution failed with code %errorlevel%
    pause
) else (
    echo.
    echo [SUCCESS] Session ended.
    pause
)

endlocal
