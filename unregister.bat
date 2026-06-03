@echo off
setlocal
cd /d "%~dp0"

call "_sys\cli\manage.bat" Unregister --base-dir "%~dp0."

endlocal
