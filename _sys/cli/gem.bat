@echo off
for %%I in ("%~dp0..\..") do set "PORTABLE_ROOT=%%~fI"
set "PYTHONUTF8=1"
set "PATH=%PORTABLE_ROOT%\_sys\env\nodejs\npm-global;%PORTABLE_ROOT%\_sys\env\venv\Scripts;%PATH%"
FOR /F "tokens=*" %%I IN ('python "%~dp0..\core\hub.py" init-session --agent gemini') DO SET "_SID=%%I"
python "%~dp0..\core\hub.py" status --format llm
gemini --resume %_SID%
