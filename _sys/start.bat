@echo off
set "PY=%~dp0env\python\python.exe"
if not exist "%PY%" echo [Error] Run install.bat first. & pause & exit /b 1
"%PY%" "%~dp0cli\launcher.py" %* || (echo [FATAL] Execution failed. & pause & exit /b 1)
