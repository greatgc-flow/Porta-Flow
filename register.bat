@echo off
set "PY=%~dp0_sys\env\python\python.exe"
if not exist "%PY%" echo [Error] Run install.bat first. & pause & exit /b 1
"%PY%" "%~dp0_sys\cli\manage.py" %~n0 %* || (echo [FATAL] Execution failed. & pause & exit /b 1)
