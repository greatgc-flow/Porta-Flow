@echo off
setlocal EnableDelayedExpansion
:: ================================================================
:: sandbox-test.bat  -  Portable Dev Env unit tests
::
:: Designed to run inside Windows Sandbox (mounted read-only at C:\PortableDev).
:: Results are written to C:\TestResults\ (mapped to _archive\test-results\).
::
:: Exit code: 0 = all PASS, 1 = one or more FAIL
:: ================================================================

set "SANDBOX_ROOT=C:\PortableDev"
set "RESULTS_DIR=C:\TestResults"
set "SYS_DIR=%SANDBOX_ROOT%\_sys"

for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "_DT=%%T"
set "RESULT_FILE=%RESULTS_DIR%\test_%_DT%.txt"

if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"

set "_PASS=0"
set "_FAIL=0"
set "_TOTAL=0"

echo ============================== >> "%RESULT_FILE%"
echo Porta-Flow Sandbox Test Report >> "%RESULT_FILE%"
echo Run: %_DT%                     >> "%RESULT_FILE%"
echo ============================== >> "%RESULT_FILE%"
echo.                               >> "%RESULT_FILE%"

call :TEST "start.bat exists"       "exist %SYS_DIR%\start.bat"
call :TEST "git.exe in env"         "exist %SYS_DIR%\env\git\cmd\git.exe"
call :TEST "node.exe in env"        "exist %SYS_DIR%\env\nodejs\node.exe"
call :TEST "rg.exe in tools"        "exist %SYS_DIR%\tools\ripgrep\rg.exe"
call :TEST "fd.exe in tools"        "exist %SYS_DIR%\tools\fd\fd.exe"
call :TEST "jq.exe in tools"        "exist %SYS_DIR%\tools\jq\jq.exe"
call :TEST "bat.exe in tools"       "exist %SYS_DIR%\tools\bat\bat.exe"
call :TEST "fzf.exe in tools"       "exist %SYS_DIR%\tools\fzf\fzf.exe"
call :TEST "ctx-save.bat exists"    "exist %SYS_DIR%\context\ctx-save.bat"
call :TEST "ctx-end.bat exists"     "exist %SYS_DIR%\context\ctx-end.bat"
call :TEST "collab-log-append.bat"  "exist %SYS_DIR%\context\collab-log-append.bat"
call :TEST "raw-log.bat exists"     "exist %SYS_DIR%\context\raw-log.bat"
call :TEST "CLAUDE.md exists"       "exist %SANDBOX_ROOT%\CLAUDE.md"
call :TEST "CONVENTION.md exists"   "exist %SANDBOX_ROOT%\CONVENTION.md"
call :TEST "GEMINI.md exists"       "exist %SANDBOX_ROOT%\GEMINI.md"
call :TEST "agents dir exists"      "exist %SANDBOX_ROOT%\.claude\agents"
call :TEST "settings.json exists"   "exist %SANDBOX_ROOT%\.claude\settings.json"

:: PATH test: run rg and check exit code
"%SYS_DIR%\tools\ripgrep\rg.exe" --version > nul 2>&1
if not errorlevel 1 (call :RESULT "rg.exe executes OK" "PASS") else (call :RESULT "rg.exe executes OK" "FAIL")

:: JSON sanity: settings.json parseable
powershell -NoProfile -Command "try { Get-Content '%SANDBOX_ROOT%\.claude\settings.json' -Raw | ConvertFrom-Json | Out-Null; exit 0 } catch { exit 1 }" > nul 2>&1
if not errorlevel 1 (call :RESULT "settings.json valid JSON" "PASS") else (call :RESULT "settings.json valid JSON" "FAIL")

echo. >> "%RESULT_FILE%"
echo ------------------------------ >> "%RESULT_FILE%"
echo TOTAL: %_TOTAL%  PASS: %_PASS%  FAIL: %_FAIL% >> "%RESULT_FILE%"
echo ------------------------------ >> "%RESULT_FILE%"

type "%RESULT_FILE%"

if "%_FAIL%"=="0" (
    echo [sandbox-test] ALL PASS (%_PASS%/%_TOTAL%)
    endlocal
    exit /b 0
) else (
    echo [sandbox-test] FAILED: %_FAIL%/%_TOTAL%
    endlocal
    exit /b 1
)

:TEST
:: %1=label  %2=condition (if exist ... or if defined ...)
set /a "_TOTAL+=1"
if %~2 (
    call :RESULT "%~1" "PASS"
) else (
    call :RESULT "%~1" "FAIL"
)
exit /b 0

:RESULT
if "%~2"=="PASS" (
    set /a "_PASS+=1"
    echo   [PASS] %~1 >> "%RESULT_FILE%"
) else (
    set /a "_FAIL+=1"
    echo   [FAIL] %~1 >> "%RESULT_FILE%"
)
exit /b 0
