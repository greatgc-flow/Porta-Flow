@echo off
:: ================================================================
:: run-sandbox-test.bat  -  Launch Porta-Flow Windows Sandbox test
::
:: Generates a path-correct .wsb from the template, then launches
:: Windows Sandbox. Requires: Windows 11 Pro/Enterprise/Education,
:: Windows Sandbox feature enabled (optionalfeatures.exe).
::
:: Results: _archive\test-results\test_YYYYMMDD_HHMMSS.txt
:: ================================================================

:: --- Resolve physical base path (no SUBST) ---
set "SYS_PHYS=%~dp0"
if "%SYS_PHYS:~-1%"=="\" set "SYS_PHYS=%SYS_PHYS:~0,-1%"
for %%I in ("%SYS_PHYS%\..\..") do set "BASE_PHYS=%%~fI"

set "TEMPLATE=%~dp0sandbox-unit-test.wsb"
set "GENERATED=%TEMP%\porta_sandbox_test_%RANDOM%.wsb"
set "RESULTS_DIR=%BASE_PHYS%\_archive\test-results"

echo [sandbox-test] Physical base: %BASE_PHYS%
echo [sandbox-test] Results dir  : %RESULTS_DIR%

if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"

:: --- Generate .wsb with real path ---
powershell -NoProfile -Command ^
    "$t = Get-Content '%TEMPLATE:\=\\%' -Raw;" ^
    "$t = $t.Replace('__PORTABLE_ROOT__', '%BASE_PHYS:\=\\%');" ^
    "[System.IO.File]::WriteAllText('%GENERATED:\=\\%', $t, (New-Object System.Text.UTF8Encoding($false)));" ^
    "Write-Host '[sandbox-test] WSB generated: %GENERATED%'"

if errorlevel 1 (
    echo [sandbox-test] ERROR: Failed to generate .wsb file.
    exit /b 1
)

:: --- Check Windows Sandbox is available ---
where WindowsSandbox.exe > nul 2>&1
if errorlevel 1 (
    echo [sandbox-test] ERROR: Windows Sandbox not found.
    echo                Enable: optionalfeatures.exe ^> "Windows Sandbox"
    del "%GENERATED%" > nul 2>&1
    exit /b 1
)

echo [sandbox-test] Launching Windows Sandbox...
echo [sandbox-test] Watch for test results in: %RESULTS_DIR%
start "" "%GENERATED%"

:: Brief wait then clean up the temp wsb
timeout /t 5 /nobreak > nul
del "%GENERATED%" > nul 2>&1
