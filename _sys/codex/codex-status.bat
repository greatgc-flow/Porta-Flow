:: ================================================================
:: codex-status.bat  -  Quick Codex peer health check
:: Delegates detailed health to hub.py peer-status.
:: ================================================================
@echo off

set "_PEER=cx"
set "_INSTALLED=false"
where codex > nul 2>&1
if not errorlevel 1 set "_INSTALLED=true"

echo [Codex] installed=%_INSTALLED%
python "%~dp0..\core\hub.py" peer-status --peer %_PEER% 2>&1

set "_INSTALLED="
set "_PEER="
