@echo off
:: run-tests.bat -- 테스트 실행 진입점
:: Usage: run-tests [--unit] [--integration] [--all]
:: Default: --unit

for %%I in ("%~dp0..\..") do set "PORTABLE_ROOT=%%~fI"
set "PYTHONUTF8=1"
set "PATH=%PORTABLE_ROOT%\_sys\env\venv\Scripts;%PATH%"

set "_MODE=unit"
if "%~1"=="--unit" set "_MODE=unit"
if "%~1"=="--integration" set "_MODE=integration"
if "%~1"=="--all" set "_MODE=all"

set "_PASS=0"
set "_FAIL=0"

if "%_MODE%"=="unit" goto :run_unit
if "%_MODE%"=="all" goto :run_unit
goto :run_integration

:run_unit
echo [tests] Running unit tests...
python -m pytest "%~dp0unit\" -v
if errorlevel 1 (set "_FAIL=1") else (set "_PASS_U=1")
if "%_MODE%"=="unit" goto :done

:run_integration
echo [tests] Running integration tests...
for %%F in ("%~dp0integration\*.ps1") do (
    powershell -ExecutionPolicy Bypass -File "%%F" -ProjectRoot "%PORTABLE_ROOT%"
    if errorlevel 1 set "_FAIL=1"
)

:done
if "%_FAIL%"=="1" (
    echo [tests] FAIL
    exit /b 1
) else (
    echo [tests] PASS
    exit /b 0
)
