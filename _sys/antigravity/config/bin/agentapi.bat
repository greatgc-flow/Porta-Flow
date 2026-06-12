@echo off
:: agentapi.bat -- portable agy agentapi launcher
:: Derives SYS_DIR from script location (3 levels up = project root, then _sys)
if not defined SYS_DIR for %%I in ("%~dp0..\..\..\_sys") do set "SYS_DIR=%%~fI"
"%SYS_DIR%\tools\agy\agy.EXE" agentapi %*
