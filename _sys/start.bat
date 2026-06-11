@echo off
set "PY=%~dp0env\python\python.exe"

:: Normalize argument (Handles trailing dots and special characters)
set "_T=%~1"
if defined _T for %%I in ("%_T%") do set "_T=%%~fI"
:: Trailing backslash (drive root like E:\) escapes the closing quote — append a dot
if defined _T if "%_T:~-1%"=="\" set "_T=%_T%."

if not exist "%PY%" echo [Error] Run install.bat first. & pause & exit /b 1
"%PY%" "%~dp0cli\launcher.py" "%_T%" || (echo [FATAL] Execution failed. & pause & exit /b 1)
