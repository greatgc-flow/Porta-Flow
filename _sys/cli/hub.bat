@echo off
set "SYS_DIR=%~dp0.."
set "PYTHONUTF8=1"
pushd "%SYS_DIR%\.." >nul
"%SYS_DIR%\env\venv\Scripts\python.exe" "%SYS_DIR%\core\hub.py" %*
set "HUB_EXIT=%ERRORLEVEL%"
popd >nul
exit /b %HUB_EXIT%
