@echo off
:: agentapi.bat -- portable agy launcher
:: agy.exe path derived from BASE_DIR (3 levels up from this bat file)
:: tool_paths.ag.exe in _sys/ai/infra.json: _sys/tools/agy/agy.exe
if not defined BASE for %%I in ("%~dp0..\..\..") do set "BASE=%%~fI"
"%BASE%\_sys\tools\agy\agy.EXE" agentapi %*
