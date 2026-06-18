@echo off
set "SYS_DIR=%~dp0.."
set "PYTHONUTF8=1"
"%SYS_DIR%nvenv\Scripts\python.exe" "%~dp0check_docs_mece.py" %*
