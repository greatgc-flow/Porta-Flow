@echo off
setlocal enabledelayedexpansion
:: ================================================================
:: INSTALL.bat  -  Portable Dev Environment Bootstrapper (Python Refactored)
::
:: This script bootstraps a minimal Python environment using curl/tar
:: and then delegates the full installation to _sys\core\setup.py.
:: ================================================================

set "PY_VER=3.13.4"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-embed-amd64.zip"
set "PY_DIR=%~dp0_sys\env\python"
set "PY_EXE=%PY_DIR%\python.exe"

echo ^>^>^> Checking for Portable Python...

if not exist "%PY_EXE%" (
    echo [i] Python not found. Bootstrapping Python %PY_VER%...
    if not exist "%~dp0_sys\data\setup-files" mkdir "%~dp0_sys\data\setup-files"
    
    set "ZIP_PATH=%~dp0_sys\data\setup-files\python-bootstrap.zip"
    
    echo [i] Downloading Python embeddable zip...
    curl -L "%PY_URL%" -o "!ZIP_PATH!"
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
    echo [i] Installing pip...
    curl -L https://bootstrap.pypa.io/get-pip.py -o "%~dp0_sys\data\setup-files\get-pip.py"
    "%PY_EXE%" "%~dp0_sys\data\setup-files\get-pip.py" --no-warn-script-location
)

echo [OK] Python is ready. Handing over to setup.py...
"%PY_EXE%" "%~dp0_sys\core\setup.py" %* || (echo [FATAL] Setup failed. & pause & exit /b 1)

echo [OK] Setup completed successfully.
endlocal
