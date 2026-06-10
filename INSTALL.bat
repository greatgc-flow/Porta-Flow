@echo off
setlocal enabledelayedexpansion
:: ================================================================
:: INSTALL.bat  -  Portable Dev Environment Bootstrapper
::
:: Bootstraps minimal Python, then delegates to _sys\core\setup.py.
:: Runtime versions/URLs sourced from _sys\runtimes.json (no hardcoding).
:: ================================================================

:: ── Runtime config from _sys\runtimes.json (fallback if missing) ──
set "_RT=%~dp0_sys\runtimes.json"
set "PY_VER=3.13.4"
set "PY_URL=https://www.python.org/ftp/python/3.13.4/python-3.13.4-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
if exist "!_RT!" (
    for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "((Get-Content '!_RT!')|ConvertFrom-Json).runtimes.python.version"`) do set "PY_VER=%%v"
    for /f "usebackq delims=" %%u in (`powershell -NoProfile -Command "((Get-Content '!_RT!')|ConvertFrom-Json).runtimes.python.url"`) do set "PY_URL=%%u"
    for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "((Get-Content '!_RT!')|ConvertFrom-Json).runtimes.python.get_pip_url"`) do set "GET_PIP_URL=%%p"
)

set "PY_DIR=%~dp0_sys\env\python"
set "PY_EXE=%PY_DIR%\python.exe"

echo ^>^>^> Checking for Portable Python %PY_VER%...

if not exist "%PY_EXE%" (
    echo [i] Python not found. Bootstrapping Python !PY_VER!...
    if not exist "%~dp0_sys\data\setup-files" mkdir "%~dp0_sys\data\setup-files"

    set "ZIP_PATH=%~dp0_sys\data\setup-files\python-bootstrap.zip"

    echo [i] Downloading Python embeddable zip...
    curl -L "!PY_URL!" -o "!ZIP_PATH!"
    if errorlevel 1 (
        echo [Error] Failed to download Python.
        if "%CI%"=="" pause
        exit /b 1
    )

    echo [i] Extracting Python...
    if not exist "%PY_DIR%" mkdir "%PY_DIR%"
    powershell -NoProfile -Command "Expand-Archive -Force -Path '!ZIP_PATH!' -DestinationPath '%PY_DIR%'"
    if errorlevel 1 (
        echo [Error] Failed to extract Python.
        if "%CI%"=="" pause
        exit /b 1
    )

    :: Enable pip (uncomment import site in ._pth)
    for %%f in ("%PY_DIR%\python*._pth") do (
        powershell -NoProfile -Command "(Get-Content '%%f') -replace '#import site', 'import site' | Set-Content '%%f'"
    )

    :: Install pip
    echo [i] Installing pip from !GET_PIP_URL!...
    curl -L "!GET_PIP_URL!" -o "%~dp0_sys\data\setup-files\get-pip.py"
    "%PY_EXE%" "%~dp0_sys\data\setup-files\get-pip.py" --no-warn-script-location
)

echo [OK] Python is ready. Handing over to setup.py...
"%PY_EXE%" "%~dp0_sys\core\setup.py" %* || (echo [FATAL] Setup failed. & pause & exit /b 1)

echo [OK] Setup completed successfully.
endlocal
