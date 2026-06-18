:: ================================================================
:: agy-status.bat  -  Quick Antigravity (agy) peer health check
:: Delegates detailed health to hub.py peer-status.
:: ================================================================
@echo off

set "_PEER=ag"
set "_AGY_EXE=%~dp0..\tools\agy\agy.exe"

set "_INSTALLED=false"
if exist "%_AGY_EXE%" set "_INSTALLED=true"

echo [Antigravity] installed=%_INSTALLED%
python "%~dp0..\core\hub.py" peer-status --peer %_PEER% 2>&1

set "_INSTALLED="
set "_PEER="
set "_AGY_EXE="
