@echo off
:: Compatibility diagnostic. Lifecycle is authoritative in orchestration.json;
:: this script no longer creates or reads gemini/status.json.
set "GEMINI_MODE=OFF"
set "GEMINI_OFF_REASON=disabled"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$o=Get-Content '%~dp0..\ai\orchestration.json' -Raw|ConvertFrom-Json; $n=$o.hub_nodes|Where-Object node_id -eq 'gc'; if($n.enabled -ne $false){'ON'}else{'OFF'}"`) do set "GEMINI_MODE=%%I"
if /i "%GEMINI_MODE%"=="ON" set "GEMINI_OFF_REASON="
echo [GATE] gemini=%GEMINI_MODE%
exit /b 0
