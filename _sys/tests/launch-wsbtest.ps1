# launch-wsbtest.ps1 — Run MECE tests inside Windows Sandbox (WSB)
# Usage: powershell -ExecutionPolicy Bypass -File launch-wsbtest.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SysDir    = Split-Path -Parent $ScriptDir
$BaseDir   = Split-Path -Parent $SysDir
$ResultsDir = Join-Path $ScriptDir "results"

if (-not (Test-Path $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
}

# Resolve physical path (handles SUBST drives)
$PhysicalBaseDir = $BaseDir
$Drive = ($BaseDir -replace '^([A-Za-z]):.*', '$1').ToUpper()
$SubstLines = subst 2>&1
foreach ($line in $SubstLines) {
    if ($line -match "^${Drive}:\\:\s+=>\s+(.+)$") {
        $PhysicalBase = $Matches[1].Trim().TrimEnd('\')
        $Relative = $BaseDir.Substring(2)
        if ($Relative -ne "" -and $Relative[0] -ne '\') { $Relative = "\" + $Relative }
        $PhysicalBaseDir = $PhysicalBase + $Relative
        break
    }
}
$PhysicalBaseDir = $PhysicalBaseDir.TrimEnd('\')
$PhysicalResultsDir = Join-Path $PhysicalBaseDir "_sys\tests\results"

Write-Host "[WSB Test] Host base path  : $PhysicalBaseDir"
Write-Host "[WSB Test] Results folder  : $PhysicalResultsDir"

$Timestamp = Get-Date -Format "yyyyMMddHHmmss"
$TempWsb = Join-Path $env:TEMP "porta-wsbtest-$Timestamp.wsb"

$WsbXml = @"
<Configuration>
  <VGpu>Disable</VGpu>
  <Networking>Default</Networking>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$PhysicalBaseDir</HostFolder>
      <SandboxFolder>C:\PortableDev</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>$PhysicalResultsDir</HostFolder>
      <SandboxFolder>C:\TestResults</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>cmd /c "C:\PortableDev\_sys\tests\wsb-entry.bat > C:\TestResults\wsb_log.txt 2>&amp;1"</Command>
  </LogonCommand>
</Configuration>
"@

Set-Content -Path $TempWsb -Value $WsbXml -Encoding utf8
Write-Host "[WSB Test] Launching Windows Sandbox..."
Write-Host "[WSB Test] Note: Networking is enabled to test setup.py downloads."

$ResultFile = Join-Path $ResultsDir "result.txt"
if (Test-Path $ResultFile) { Remove-Item $ResultFile -Force }
$SummaryFile = Join-Path $ResultsDir "summary.txt"
if (Test-Path $SummaryFile) { Remove-Item $SummaryFile -Force }

Start-Process $TempWsb
Write-Host "[WSB Test] Waiting for sandbox tests to complete (timeout 15 min)..."

$Deadline = (Get-Date).AddMinutes(30)
while (-not (Test-Path $ResultFile) -and (Get-Date) -lt $Deadline) {
    Start-Sleep -Seconds 20
    Write-Host "  ...waiting"
}

if (Test-Path $ResultFile) {
    Write-Host "`n========== WSB TEST RESULTS =========="
    if (Test-Path $SummaryFile) {
        Get-Content $SummaryFile | Write-Host
    }
    Write-Host "Detailed reports (pytest, lifecycle logs) available in: $ResultsDir"
    Remove-Item $TempWsb -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "[WSB Test] TIMEOUT — no result file received."
}
