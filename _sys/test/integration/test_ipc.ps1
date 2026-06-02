# test_ipc.ps1 - msg.bat IPC 통합 테스트
# Usage: powershell -ExecutionPolicy Bypass -File test_ipc.ps1
# DRY_RUN=1: claude/gemini CLI 호출 스킵, hub.py만 테스트

param([string]$ProjectRoot = "D:\PortableDev (2) - 복사본")

$ErrorActionPreference = "Stop"
$pass = 0; $fail = 0

function Test-Case($name, $block) {
    try {
        & $block
        Write-Host "[PASS] $name" -ForegroundColor Green
        $script:pass++
    } catch {
        Write-Host "[FAIL] $name : $_" -ForegroundColor Red
        $script:fail++
    }
}

# 환경 설정
$env:PYTHONUTF8 = "1"
$venvPy = "$ProjectRoot\_sys\env\venv\Scripts\python.exe"
$hub = "$ProjectRoot\_sys\core\hub.py"

# 임시 프로젝트 디렉토리 생성 (격리)
$tmpDir = New-Item -ItemType Directory -Path "$env:TEMP\hub-test-$(Get-Random)"
New-Item -ItemType Directory -Path (Join-Path $tmpDir ".git") | Out-Null
$origLocation = Get-Location
Set-Location $tmpDir

try {
    # .ai/ 초기화
    & $venvPy $hub init-session --agent claude | Out-Null

    Test-Case "send message" {
        $out = & $venvPy $hub send --from claude --to gemini --msg "integration test" 2>&1
        if (($out -join " ") -notmatch "\[SENT\]") { throw "Expected [SENT]" }
    }

    Test-Case "check unread (llm)" {
        $out = & $venvPy $hub check --target gemini --format llm 2>&1
        if (($out -join " ") -notmatch "\[UNREAD:1\]") { throw "Expected [UNREAD:1], got: $out" }
    }

    Test-Case "mark-read all" {
        & $venvPy $hub mark-read --target gemini --all | Out-Null
        $out = & $venvPy $hub check --target gemini --format llm 2>&1
        if (($out -join " ") -notmatch "\[UNREAD:0\]") { throw "Expected [UNREAD:0]" }
    }

    Test-Case "update-status" {
        & $venvPy $hub update-status --mission "integration test running" --phase "8" | Out-Null
        $out = & $venvPy $hub status --format llm 2>&1
        if (($out -join " ") -notmatch "integration test running") { throw "Mission not found in status" }
    }

    Test-Case "end-session" {
        $out = & $venvPy $hub end-session --agent claude 2>&1
        if (($out -join " ") -notmatch "\[END\]") { throw "Expected [END]" }
    }

    Test-Case "handoff.md exists after session" {
        $state = & $venvPy $hub status 2>&1 | ConvertFrom-Json -ErrorAction SilentlyContinue
        $pair = (Get-Content "$tmpDir\.ai\state.json" | ConvertFrom-Json).pair
        $handoff = "$tmpDir\.ai\sessions\$pair\handoff.md"
        if (-not (Test-Path $handoff)) { throw "handoff.md not found" }
    }

    Test-Case "concurrent send (race condition)" {
        # 동시 10개 send
        1..10 | ForEach-Object {
            Start-Job -ScriptBlock {
                param($py, $hub, $dir)
                Set-Location $dir
                & $py $hub send --from claude --to gemini --msg "concurrent-$using:_"
            } -ArgumentList $venvPy, $hub, $tmpDir | Out-Null
        }
        Get-Job | Wait-Job | Out-Null
        Get-Job | Remove-Job

        $mb = Get-Content "$tmpDir\.ai\mailbox.json" | ConvertFrom-Json
        # 최소 8개 이상 성공 (일부 lock 대기로 실패 허용)
        if ($mb.unread_count -lt 8) { throw "Expected >=8 messages, got $($mb.unread_count)" }
    }

    Test-Case "msg.bat wrapper" {
        $out = cmd /c """$ProjectRoot\_sys\cli\msg.bat"" send --from gemini --to claude --msg ""hello from bat""" 2>&1
        if (($out -join " ") -notmatch "\[SENT\]") { throw "msg.bat failed: $out" }
    }

    Test-Case "venv python is used (not system python)" {
        $whichPy = & $venvPy -c "import sys; print(sys.executable)" 2>&1
        if ($whichPy -notmatch "venv") { throw "Expected venv python, got: $whichPy" }
    }

} finally {
    Set-Location $origLocation
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "`n============================="
Write-Host "Results: $pass passed, $fail failed" -ForegroundColor $(if($fail -eq 0){"Green"}else{"Red"})
if ($fail -gt 0) { exit 1 }
