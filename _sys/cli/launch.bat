@echo off
set "START_BAT=%~dp0..\start.bat"
call "%START_BAT%" %* || (echo [FATAL] Session ended with errors. & pause & exit /b 1)
