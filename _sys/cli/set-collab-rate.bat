@echo off
:: ================================================================
:: set-collab-rate.bat [0-10]
::
:: Sets collab_rate in _sys\ai\protocol.json (primary) and
:: _sys\ai\config.json (backward-compat sync).
::
:: Anchors: [0]=Solo [3]=Guard [5]=Partner [8]=Strict [10]=Sync
:: ================================================================

for %%I in ("%~dp0..\ai\protocol.json") do set "_PROTO=%%~fI"
for %%I in ("%~dp0..\ai\config.json")    do set "_CFG=%%~fI"

if "%~1"=="" (
    echo Usage: set-collab-rate.bat [0-10]
    echo Anchors: 0=Solo 3=Guard 5=Partner 8=Strict 10=Sync
    echo.
    echo Current collab_rate:
    powershell -NoProfile -Command "(Get-Content '%_PROTO:\=\\%' -Raw | ConvertFrom-Json).collab_rate.current"
    goto :DONE
)

set "_N=%~1"
if %_N% LSS 0 set "_N=0"
if %_N% GTR 10 set "_N=10"

powershell -NoProfile -Command "$n=[int]'%_N%'; $p=Get-Content '%_PROTO:\=\\%' -Raw|ConvertFrom-Json; $p.collab_rate.current=$n; $p.active_constraints.current_collab_rate=$n; [System.IO.File]::WriteAllText('%_PROTO:\=\\%',($p|ConvertTo-Json -Depth 5),(New-Object System.Text.UTF8Encoding($false)))"

powershell -NoProfile -Command "$n=[int]'%_N%'; try { $c=Get-Content '%_CFG:\=\\%' -Raw|ConvertFrom-Json } catch { $c=[pscustomobject]@{ratio=5;review_interval_min=5;last_review_ts=$null} }; $c|Add-Member -NotePropertyName ratio -NotePropertyValue $n -Force; [System.IO.File]::WriteAllText('%_CFG:\=\\%',($c|ConvertTo-Json -Depth 3),(New-Object System.Text.UTF8Encoding($false)))"

echo [set-collab-rate] collab_rate set to %_N%

:DONE
set "_PROTO=" & set "_CFG=" & set "_N="