@echo off
:: cla.bat - Claude session entry point
:: init-session -> SID issue, status -> pretty-print status, run claude
for %%I in ("%~dp0..\..") do set "PORTABLE_ROOT=%%~fI"
set "PYTHONUTF8=1"
set "PATH=%PORTABLE_ROOT%\_sys\env\venv\Scripts;%PATH%"
python "%~dp0..\core\hub.py" init-session --agent claude > nul
python "%~dp0..\core\hub.py" status
claude
