@echo off
set "STAMP=%date:~0,4%%date:~5,2%%date:~8,2%%time:~0,2%%time:~3,2%%time:~6,2%"
set "STAMP=%STAMP: =0%"

echo [1/4] Renaming current _sys to _sys_old_rollback_%STAMP%...
ren _sys _sys_old_rollback_%STAMP%
if %errorlevel% neq 0 (echo FAIL: Renaming _sys failed & exit /b 1)

echo [2/4] Promoting _sys_new to _sys...
ren _sys_new _sys
if %errorlevel% neq 0 (echo FAIL: Renaming _sys_new failed & exit /b 1)

echo [3/4] Re-applying junctions...
tmp\venv_swap\Scripts\python.exe _sys\core\virtualizer.py apply --force
if %errorlevel% neq 0 (echo FAIL: Junction application failed & exit /b 1)

echo [4/4] Verifying baseline...
_sys\env\venv\Scripts\python.exe -m pytest _sys\tests\unit -q --tb=short
if %errorlevel% neq 0 (echo FAIL: Baseline tests failed & exit /b 1)

echo SUCCESS: ROOT SWAP COMPLETED.
