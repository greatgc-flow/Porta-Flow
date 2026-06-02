@echo off
:: raw-log.bat [AXIS] [RESPONSE_FILE] [OPTIONAL_DIRECTIVE_FILE]
::
:: Saves raw Gemini I/O to _archive/raw-log/ for audit.
:: Zero AI token cost - pure file copy.
::
:: Usage (from Axis scripts):
::   call "%~dp0raw-log.bat" "Axis-E" "%OUT_FILE%" "%TEMP_MERGED%"
::   call "%~dp0raw-log.bat" "Axis-B" "%OUT_FILE%"

if defined BASE_DIR (set "_B=%BASE_DIR%") else (for %%I in ("%~dp0..\..") do set "_B=%%~fI")

set "_RAWDIR=%_B%\_archive\raw-log"
if not exist "%_RAWDIR%" mkdir "%_RAWDIR%" > nul 2>&1

for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddHHmmss"') do set "_TS=%%T"

if "%~2"=="" goto :EOF
if not exist "%~2" goto :DIRECTIVE

copy "%~2" "%_RAWDIR%\%_TS%_%~1_response.txt" > nul 2>&1

:DIRECTIVE
if "%~3"=="" goto :EOF
if not exist "%~3" goto :EOF
copy "%~3" "%_RAWDIR%\%_TS%_%~1_directive.txt" > nul 2>&1
