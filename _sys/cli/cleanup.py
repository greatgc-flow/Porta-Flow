"""
cleanup.py - Portable Dev Environment Space Optimizer

Tier 1  Light     — 캐시·임시파일·로그 (안전, 재설치 불필요)
Tier 2  Soft      — Tier 1 + 설치 아카이브·venv·로컬 설정
Tier 3  Reset     — Tier 2 + 런타임·도구·AI 인증·Junction [확인 필요]
Tier 4  ZeroBase  — Tier 3 + 워크스페이스·아카이브·AI Peer 시스템 전체 [확인 필요]
Tier 5  Purge     — Tier 4 + Python (완전 초기화, INSTALL.bat 재실행 필요) [확인 필요]

AI peer 항목은 _sys/ai/peers.json 주도 — 코드 수정 없이 피어 추가 가능.
"""
import os
import json
import shutil
import stat
import subprocess
from pathlib import Path


def on_rm_error(func, path, exc_info):
    """read-only 파일(.git 등) 강제 삭제 핸들러."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def get_dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in Path(path).rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception:
        pass
    return total


def format_size(b: int) -> str:
    if b >= 1024**3: return f"{b/(1024**3):.2f} GB"
    if b >= 1024**2: return f"{b/(1024**2):.2f} MB"
    if b >= 1024:    return f"{b/1024:.2f} KB"
    return f"{b} B"


def load_peers(sys_dir: Path) -> dict:
    peers_path = sys_dir / "ai" / "peers.json"
    if peers_path.exists():
        try:
            return json.loads(peers_path.read_text(encoding="utf-8")).get("peers", {})
        except Exception:
            pass
    return {}


def remove_junction_safe(path: Path, label: str, dry_run: bool = False) -> None:
    path = Path(path)
    try:
        st = path.lstat()
    except FileNotFoundError:
        return
    is_junction = os.path.islink(path) or getattr(st, "st_reparse_tag", 0) == 0xA0000003
    if not is_junction:
        return
    if dry_run:
        print(f"  [Wait] {label} — Junction 해제 예정")
        return
    try:
        subprocess.run(f'rmdir "{path}"', shell=True, check=True, capture_output=True)
        print(f"  [OK] {label} — Junction 해제됨")
    except Exception as e:
        print(f"  [Fail] Could not remove junction {label}: {e}")


def remove_path_safe(path: Path, label: str, dry_run: bool = False) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    size = get_dir_size(path)
    if dry_run:
        print(f"  [Wait] {label} — {format_size(size)} 삭제 예정")
        return size
    try:
        if path.is_dir():
            shutil.rmtree(path, onerror=on_rm_error)
        else:
            try:
                path.unlink()
            except OSError:
                os.chmod(path, stat.S_IWRITE)
                path.unlink()
        print(f"  [OK] {label} — {format_size(size)} 삭제됨")
        return size
    except Exception as e:
        print(f"  [Fail] Could not remove {label}: {e}")
        return 0


def _confirm(msg: str, all_yes: bool, dry_run: bool = False) -> bool:
    if all_yes or dry_run:
        return True
    return input(msg).lower().startswith("y")


def run_cleanup(tier: int = 1, all_yes: bool = False, dry_run: bool = False, base_dir=None) -> None:
    if base_dir is None:
        sys_dir = Path(__file__).parent.parent.resolve()
        base_dir = sys_dir.parent
    else:
        base_dir = Path(base_dir)
        sys_dir = base_dir / "_sys"
    env_dir  = sys_dir / "env"
    data_dir = sys_dir / "data"
    peers    = load_peers(sys_dir)

    total_freed = 0

    print(f"\n{'='*54}")
    print(f"  Portable Dev Cleanup — Tier {tier}")
    if dry_run:
        print("  ※ 미리보기 모드 — 실제 삭제 안 함")
    print(f"{'='*54}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Tier 1: Light — 캐시·임시파일·로그 (재설치 불필요)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[Tier 1] 가벼운 정리 (안전)")

    # 패키지 캐시
    total_freed += remove_path_safe(env_dir / "python" / "pip-cache", "pip 캐시", dry_run)
    total_freed += remove_path_safe(env_dir / "nodejs" / "npm-cache", "npm 캐시", dry_run)

    # 임시·IPC·에디터 상태
    total_freed += remove_path_safe(data_dir / "temp",      r"임시 파일 (_sys/data/temp)", dry_run)
    total_freed += remove_path_safe(base_dir / ".ai",       r"AI IPC 통신 로그 (.ai)", dry_run)
    total_freed += remove_path_safe(base_dir / ".vscode",   r"VS Code 임시 설정 (.vscode)", dry_run)
    total_freed += remove_path_safe(base_dir / "_state",    r"AI 임시 상태 (_state)", dry_run)
    total_freed += remove_path_safe(base_dir / "WORKLOG.md", "임시 작업 로그 (WORKLOG.md)", dry_run)

    # 런처 로그 (최근 5개 보존)
    archive_logs = base_dir / "_archive" / "logs"
    if archive_logs.exists():
        logs = sorted(archive_logs.glob("start_*.log"), key=os.path.getmtime, reverse=True)
        to_del = list(logs)[5:]
        if to_del:
            del_sz = sum(l.stat().st_size for l in to_del)
            if not dry_run:
                for l in to_del: l.unlink()
            print(f"  [OK] 런처 로그 — {len(to_del)}개 삭제 ({format_size(del_sz)})")
            total_freed += del_sz

    # 테스트 캐시·결과
    total_freed += remove_path_safe(base_dir / ".pytest_cache",                              "pytest 캐시 (root)", dry_run)
    total_freed += remove_path_safe(sys_dir  / "tests" / ".pytest_cache",                    "pytest 캐시 (tests)", dry_run)
    total_freed += remove_path_safe(sys_dir  / "tests" / "unit" / ".pytest_cache",           "pytest 캐시 (unit)", dry_run)
    total_freed += remove_path_safe(sys_dir  / "tests" / "results",                          "테스트 결과물", dry_run)
    total_freed += remove_path_safe(sys_dir  / "tests" / "local_test_tmp",                   "로컬 통합 테스트 임시", dry_run)
    total_freed += remove_path_safe(sys_dir  / "tests" / "integration" / "parallel_test_tmp","병렬 테스트 임시", dry_run)

    # Python 바이트코드
    pycache_count, pycache_size = 0, 0
    for p in base_dir.rglob("__pycache__"):
        if p.is_dir():
            sz = get_dir_size(p)
            pycache_size += sz
            if not dry_run:
                shutil.rmtree(p)
            pycache_count += 1
    if pycache_count > 0:
        print(f"  [OK] __pycache__ — {pycache_count}개 삭제 ({format_size(pycache_size)})")
        total_freed += pycache_size

    # 오래된 로그 (최근 5개 보존)
    log_path = data_dir / "logs"
    if log_path.exists():
        logs = sorted(log_path.glob("*.log"), key=os.path.getmtime, reverse=True)
        to_del = list(logs)[5:]
        if to_del:
            del_sz = sum(l.stat().st_size for l in to_del)
            if not dry_run:
                for l in to_del: l.unlink()
            print(f"  [OK] 오래된 로그 — {len(to_del)}개 삭제 ({format_size(del_sz)})")
            total_freed += del_sz

    # AI Peer 경량 정리 (상태·임시 파일 — peers.json 주도)
    for peer_id, cfg in peers.items():
        peer_dir = sys_dir / cfg.get("sys_subdir", peer_id)
        cfg_dir  = peer_dir / "config"
        cleanup  = cfg.get("cleanup", {})

        total_freed += remove_path_safe(peer_dir / "status.json", f"{peer_id} 상태 파일", dry_run)

        for rel in cleanup.get("peer_paths", []):
            total_freed += remove_path_safe(peer_dir / rel, f"{peer_id} {rel}", dry_run)
        for pattern in cleanup.get("peer_globs", []):
            for f in peer_dir.glob(pattern):
                total_freed += remove_path_safe(f, f"{peer_id} {f.name}", dry_run)
        for rel in cleanup.get("config_paths", []):
            total_freed += remove_path_safe(cfg_dir / rel, f"{peer_id} config/{rel}", dry_run)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Tier 2: Soft — 설치 아카이브·venv·로컬 설정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if tier >= 2:
        print("\n[Tier 2] Soft 정리 (재다운로드/재생성 필요)")

        total_freed += remove_path_safe(data_dir / "setup-files", "설치 아카이브 (zip/exe)", dry_run)
        total_freed += remove_path_safe(env_dir  / "venv",        "Python 가상환경 (venv)", dry_run)

        # 호스트별 로컬 설정 (config.json, settings.local.json)
        total_freed += remove_path_safe(sys_dir / "config.json", "시스템 로컬 설정 (config.json)", dry_run)
        for peer_id, cfg in peers.items():
            peer_dir = sys_dir / cfg.get("sys_subdir", peer_id)
            total_freed += remove_path_safe(
                peer_dir / "project" / "settings.local.json",
                f"{peer_id} 로컬 설정 (settings.local.json)", dry_run
            )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Tier 3: Reset — 런타임·도구·AI 인증·Junction
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if tier >= 3:
        if not _confirm("\n  [?] 런타임·도구·AI 인증 삭제 (전체 재설치 필요) 계속할까요? [y/N]: ", all_yes, dry_run):
            _print_summary(total_freed, dry_run)
            return

        print("\n[Tier 3] Runtime Reset (전체 재설치 필요)")

        # 런타임 (python 제외 — Tier 5에서 처리)
        if env_dir.exists():
            for item in env_dir.iterdir():
                if item.name not in ("python", "python.purge", "venv"):
                    total_freed += remove_path_safe(item, f"Runtime ({item.name})", dry_run)

        # CLI 도구 바이너리
        tools_dir = sys_dir / "tools"
        if tools_dir.exists():
            for item in tools_dir.iterdir():
                if item.name != "apps":
                    total_freed += remove_path_safe(item, f"Tool ({item.name})", dry_run)

        # AI Peer: 인증 데이터 + Junction 해제 (peers.json 주도)
        for peer_id, cfg in peers.items():
            if not cfg.get("enabled"):
                continue
            peer_dir = sys_dir / cfg.get("sys_subdir", peer_id)
            cfg_dir  = peer_dir / "config"

            if cfg_dir.exists() and not cfg_dir.is_symlink():
                total_freed += remove_path_safe(cfg_dir, f"{peer_id} 인증 데이터", dry_run)

            if cfg.get("project_junction"):
                root_dir = cfg.get("root_dir", f".{peer_id}")
                remove_junction_safe(base_dir / root_dir, f"{peer_id} 프로젝트 Junction ({root_dir})", dry_run)

            if cfg.get("host_junction"):
                hj = cfg["host_junction"]
                host_path = Path(os.environ.get(hj.get("host_env", "USERPROFILE"), "")) / hj.get("host_dirname", f".{peer_id}")
                remove_junction_safe(host_path, f"{peer_id} 호스트 Junction ({host_path.name})", dry_run)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Tier 4: ZeroBase — 워크스페이스·아카이브·AI Peer 시스템
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if tier >= 4:
        if not _confirm("\n  [!] 경고: 워크스페이스·아카이브·AI Peer 시스템 전체 삭제 계속할까요? [y/N]: ", all_yes, dry_run):
            _print_summary(total_freed, dry_run)
            return

        print("\n[Tier 4] ZeroBase (사용자 데이터 + AI Peer 시스템 삭제)")

        total_freed += remove_path_safe(base_dir / "workspace", "워크스페이스 데이터", dry_run)
        total_freed += remove_path_safe(base_dir / "_archive",  "아카이브/로그 전체", dry_run)

        for f in base_dir.glob("*.md"):
            sz = f.stat().st_size
            if not dry_run:
                f.unlink()
            else:
                print(f"  [Wait] 문서 — {f.name} 삭제 예정")
            total_freed += sz
            if not dry_run:
                print(f"  [OK] 문서 삭제 — {f.name}")

        local_config = sys_dir / "local.config.bat"
        if local_config.exists():
            total_freed += local_config.stat().st_size
            if not dry_run:
                local_config.unlink()

        # AI Peer 시스템 디렉토리 전체 (scripts·project 포함)
        for peer_id, cfg in peers.items():
            if not cfg.get("enabled"):
                continue
            peer_dir = sys_dir / cfg.get("sys_subdir", peer_id)
            if peer_dir.exists():
                total_freed += remove_path_safe(peer_dir, f"{peer_id} 시스템 전체 ({peer_dir.name}/)", dry_run)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Tier 5: Purge — Python 삭제 (완전 초기화)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if tier >= 5:
        if not _confirm("\n  [!!!] 최종 경고: Python 삭제 (INSTALL.bat 재실행 필수) 계속할까요? [y/N]: ", all_yes, dry_run):
            _print_summary(total_freed, dry_run)
            return

        print("\n[Tier 5] Purge — Python 런타임 삭제")

        py_dir = env_dir / "python"
        if py_dir.exists():
            py_size = get_dir_size(py_dir)
            if dry_run:
                print(f"  [Wait] Python 런타임 — {format_size(py_size)} 삭제 예정 (백그라운드)")
            else:
                purge_dir = env_dir / "python.purge"
                try:
                    if purge_dir.exists():
                        shutil.rmtree(purge_dir, onerror=on_rm_error)
                    py_dir.rename(purge_dir)
                    bat = (
                        "@echo off\r\n"
                        f"timeout /T 5 /NOBREAK >nul\r\n"
                        f"rmdir /s /q \"{purge_dir}\"\r\n"
                        f"del \"%~f0\"\r\n"
                    )
                    bat_path = Path(os.environ.get("TEMP", str(env_dir))) / "_purge_python.bat"
                    bat_path.write_text(bat, encoding="mbcs")
                    subprocess.Popen(
                        ["cmd", "/c", str(bat_path)],
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_CONSOLE,
                        close_fds=True,
                    )
                    print(f"  [OK] Python 런타임 — {format_size(py_size)} 백그라운드 삭제 예약됨")
                    total_freed += py_size
                except Exception as e:
                    print(f"  [Fail] Python 삭제 실패: {e}")
                    print(f"         수동 삭제: {py_dir}")

    _print_summary(total_freed, dry_run)


def _print_summary(total_freed: int, dry_run: bool) -> None:
    print(f"\n{'='*54}")
    if dry_run:
        print(f"  미리보기: 총 {format_size(total_freed)} 확보 예정")
    else:
        print(f"  정리 완료: 총 {format_size(total_freed)} 확보됨")
    print(f"{'='*54}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Portable Dev Environment Cleanup")
    parser.add_argument("--tier", type=int, default=None)
    parser.add_argument("--all", "-y", action="store_true", help="확인 프롬프트 건너뜀 (CI용)")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 (실제 삭제 안 함)")
    args = parser.parse_args()

    tier = args.tier
    if tier is None:
        print("=" * 54)
        print("  Portable Dev - Cleanup Utility")
        print("=" * 54)
        print("  1. Light    — 캐시·임시파일·로그 (안전)")
        print("  2. Soft     — Tier 1 + 설치 아카이브·venv·로컬 설정")
        print("  3. Reset    — Tier 2 + 런타임·도구·AI 인증·Junction")
        print("  4. ZeroBase — Tier 3 + 워크스페이스·AI Peer 시스템")
        print("  5. Purge    — Tier 4 + Python (완전 초기화)")
        print("=" * 54)
        try:
            choice = input("  선택 (1-5, 기본값=1): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"
        tier = int(choice) if choice in ("1", "2", "3", "4", "5") else 1

    run_cleanup(tier=tier, all_yes=args.all, dry_run=args.dry_run)
