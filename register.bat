@echo off
setlocal
cd /d "%~dp0"

call "_sys\cli\manage.bat" Register --base-dir "%~dp0."

endlocal
