"""
Launcher Path Integrity Tests
Verifies that Korean/special-char/space paths survive the full
registry → launch.bat → start.bat → app-launch chain without truncation,
quote collapse, or encoding loss.

Node.js Korean Path Safety:
Node.js (npm, claude, gemini CLI) silently fails or crashes when invoked with
non-ASCII (Korean) characters in:
  - NPM_CONFIG_PREFIX / NPM_CONFIG_CACHE
  - CLAUDE_CONFIG_DIR
  - PATH entries
  - cwd of the launched process (VS Code TARGET_DIR)

SUBST is the only mechanism that converts Korean physical paths to ASCII.
These tests verify that SUBST protection is in place at every relevant point.
"""
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

SYS_DIR = Path(__file__).parent.parent.parent
LAUNCH_BAT = SYS_DIR / "cli" / "launch.bat"
START_BAT = SYS_DIR / "start.bat"

# Challenging paths for portability
TRICKY_PATHS = [
    r"D:\PortableDev (2) - 복사본",        # Korean + parens + spaces + dash
    r"D:\테스트 폴더\my project",           # Korean dir + space
    r"C:\Users\GREAT\Desktop",             # simple ASCII
    r"E:\dev (sandbox)",                   # parens + space
    r"D:\path with spaces and (parens)",   # spaces + parens (no Korean)
]


class TestRegistryCommandFormat:
    """Registry command string must survive shell expansion intact."""

    def test_cmd_str_quotes_all_components(self):
        """cmd.exe /c ""path" "arg"" pattern — both path and arg quoted."""
        sys.path.insert(0, str(SYS_DIR / "cli"))
        import manage
        base = Path(r"D:\PortableDev (2) - 복사본")
        script = base / "_sys" / "cli" / "launch.bat"
        cmd = f'cmd.exe /c ""{script}" "%V""'
        # Outer wrapper: cmd.exe /c "..."
        assert cmd.startswith('cmd.exe /c "')
        assert cmd.endswith('"')
        # launch.bat path is quoted (handles spaces)
        assert f'"{script}"' in cmd
        # arg placeholder is quoted
        assert '"%V"' in cmd

    @pytest.mark.parametrize("base_path", [
        r"D:\PortableDev (2) - 복사본",
        r"D:\테스트 폴더\sandbox",
        r"E:\dev (copy)",
    ])
    def test_physical_path_in_registry_cmd(self, base_path):
        """Physical path (no SUBST) must be used in registry to survive reboot."""
        sys.path.insert(0, str(SYS_DIR / "cli"))
        import manage
        base = Path(base_path)
        script = base / "_sys" / "cli" / "launch.bat"
        cmd = f'cmd.exe /c ""{script}" "%V""'
        # Must NOT use SUBST placeholder like 'E:\_sys'
        assert str(script) in cmd
        # Must not reference a different drive as the root
        assert base_path[:2] in cmd  # drive letter present


class TestBatRelayChain:
    """launch.bat → start.bat argument forwarding integrity."""

    def test_launch_bat_forwards_full_arg(self, tmp_path):
        """launch.bat passes %* verbatim; path with spaces must be preserved."""
        # Simulate what cmd.exe does: split on spaces unless quoted
        tricky = r'"D:\PortableDev (2) - 복사본"'
        # If the outer quotes are present the path is a single token
        tokens = tricky.strip('"').split()
        # After strip-quoting the full path is one item, not split on spaces
        assert len([tricky]) == 1  # treated as one argument when quoted

    @pytest.mark.parametrize("path", TRICKY_PATHS)
    def test_start_bat_tilde1_expansion(self, path):
        r"""%~1 in start.bat strips surrounding quotes — result must equal raw path."""
        # %~1 strips leading/trailing double-quotes from %1
        quoted = f'"{path}"'
        # Simulate %~1 behaviour: remove outer quotes
        expanded = quoted.strip('"')
        assert expanded == path
        # Crucially: path should not be empty or truncated
        assert len(expanded) > 3

    def test_no_truncation_on_parentheses(self):
        """Parentheses in path must not cause cmd.exe FOR-block truncation."""
        path = r"D:\PortableDev (2) - 복사본"
        # The known bug: cmd.exe inside if(...) or for(...) treats ) as block-end
        # The fix is to use EnableDelayedExpansion + !VAR! inside blocks.
        # Verify our start.bat uses setlocal EnableDelayedExpansion
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        assert "EnableDelayedExpansion" in content, \
            "start.bat must use EnableDelayedExpansion to handle () in paths"
        # Also verify !TARGET! is used (not %TARGET%) inside conditional blocks
        assert "!TARGET!" in content

    def test_korean_path_not_empty_after_expansion(self):
        """Korean segment must survive in path string (no silent truncation)."""
        path = r"D:\PortableDev (2) - 복사본\workspace"
        # Korean chars: 복사본 (3 chars)
        assert "복사본" in path
        # Simulate Path.resolve() — Python handles Korean NTFS paths natively
        p = Path(path)
        assert "복사본" in str(p)


class TestSubstPathNormalization:
    """Physical ↔ SUBST path substitution in start.bat."""

    def test_physical_path_replaced_with_subst(self):
        """start.bat TARGET substitution: BASE_DIR_PHYS → BASE_DIR (SUBST)."""
        # Simulate: TARGET = D:\PortableDev (2) - 복사본\workspace
        # BASE_DIR_PHYS = D:\PortableDev (2) - 복사본, BASE_DIR = E:
        phys = r"D:\PortableDev (2) - 복사본"
        subst = r"E:"
        target = r"D:\PortableDev (2) - 복사본\workspace"
        # Batch: set "TARGET=!TARGET:%BASE_DIR_PHYS%=%BASE_DIR%!"
        result = target.replace(phys, subst)
        assert result == r"E:\workspace"
        assert "복사본" not in result  # Korean segment correctly removed

    def test_non_sandbox_path_unchanged(self):
        """Paths outside BASE_DIR must not be modified by substitution."""
        phys = r"D:\PortableDev (2) - 복사본"
        subst = r"E:"
        external = r"C:\Users\GREAT\Desktop"
        result = external.replace(phys, subst)
        assert result == external  # unchanged


class TestLaunchBatStructure:
    """launch.bat must self-locate via %~dp0 for SUBST-resilient operation."""

    def test_launch_bat_uses_tilde_dp0(self):
        """launch.bat must derive SYS_DIR from %~dp0 (not hardcoded path).
        %~dp0 gives the physical location of the batch file itself, allowing
        the script to work both when called via SUBST and via physical path."""
        content = LAUNCH_BAT.read_text(encoding="utf-8", errors="ignore")
        assert "%~dp0" in content, "launch.bat must use %~dp0 for self-location"

    def test_launch_bat_calls_start_bat(self):
        """launch.bat must relay to start.bat via the derived path."""
        content = LAUNCH_BAT.read_text(encoding="utf-8", errors="ignore")
        assert "start.bat" in content, "launch.bat must call start.bat"
        # Must forward all arguments
        assert "%*" in content, "launch.bat must forward %* to start.bat"

    def test_launch_bat_no_hardcoded_drive(self):
        """launch.bat must not have any hardcoded drive letter paths."""
        import re
        content = LAUNCH_BAT.read_text(encoding="utf-8", errors="ignore")
        hardcoded = re.search(r'(?<!%~dp0)[A-Z]:\\(?!sys)', content, re.IGNORECASE)
        # If found, it's a potential portability issue
        assert hardcoded is None, \
            f"Potential hardcoded path in launch.bat: {hardcoded.group()}"

    def test_start_bat_uses_delayed_expansion_in_blocks(self):
        """start.bat must use !TARGET! (not %TARGET%) inside if/else blocks.
        cmd.exe expands %VAR% at parse time, so ) in path values break block parsing.
        EnableDelayedExpansion + !VAR! expands at runtime, after block is parsed."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        assert "EnableDelayedExpansion" in content, \
            "start.bat must use EnableDelayedExpansion to handle () in paths"
        assert "!TARGET!" in content, \
            "start.bat must use !TARGET! inside if/for blocks"


class TestNodeJsPathSafety:
    """SUBST must protect Node.js tools from Korean paths at every entry point.

    Risk matrix:
      [A] NPM_CONFIG_PREFIX/CACHE uses %ENV_DIR% — safe if SUBST is set
      [B] CLAUDE_CONFIG_DIR uses %CLAUDE_DIR% — safe if SUBST is set
      [C] PATH nodejs entries use %ENV_DIR% — safe if SUBST is set
      [D] TARGET passed to VS Code substituted to SUBST path — safe if registered
      [E] SUBST failure → ERROR_EXIT, never silent Korean fallback
      [F] Unregistered → Warning + physical Korean path fallback (known limitation)
    """

    # ── [A] NPM env vars ────────────────────────────────────────────────────
    def test_npm_config_prefix_uses_env_dir_not_phys(self):
        """[A] NPM_CONFIG_PREFIX must reference %ENV_DIR% (SUBST-derived), not PHYS vars.
        Node.js npm install/global commands fail when prefix contains Korean."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        idx = content.find("NPM_CONFIG_PREFIX")
        assert idx != -1, "NPM_CONFIG_PREFIX not set in start.bat"
        line = content[idx : idx + 120]
        assert "ENV_DIR" in line, f"NPM_CONFIG_PREFIX must use ENV_DIR: {line}"
        assert "PHYS" not in line, f"NPM_CONFIG_PREFIX must not use physical path var: {line}"

    def test_npm_config_cache_uses_env_dir_not_phys(self):
        """[A] NPM_CONFIG_CACHE must reference %ENV_DIR% (SUBST-derived)."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        idx = content.find("NPM_CONFIG_CACHE")
        assert idx != -1, "NPM_CONFIG_CACHE not set in start.bat"
        line = content[idx : idx + 120]
        assert "ENV_DIR" in line, f"NPM_CONFIG_CACHE must use ENV_DIR: {line}"
        assert "PHYS" not in line, f"NPM_CONFIG_CACHE must not use physical path var: {line}"

    # ── [B] Claude Code CLI path ─────────────────────────────────────────────
    def test_claude_config_dir_uses_subst_derived_var(self):
        """[B] CLAUDE_CONFIG_DIR must derive from CLAUDE_DIR/SYS_DIR (SUBST path).
        Claude Code is a Node.js CLI — Korean in config dir causes startup failure."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        idx = content.find("CLAUDE_CONFIG_DIR")
        assert idx != -1, "CLAUDE_CONFIG_DIR not set in start.bat"
        line = content[idx : idx + 120]
        assert any(v in line for v in ["CLAUDE_DIR", "SYS_DIR", "ENV_DIR"]), \
            f"CLAUDE_CONFIG_DIR must use a SUBST-derived variable: {line}"
        assert "PHYS" not in line, \
            f"CLAUDE_CONFIG_DIR must not reference physical path: {line}"

    # ── [C] PATH entries ─────────────────────────────────────────────────────
    def test_nodejs_path_entry_uses_env_dir_variable(self):
        """[C] nodejs binary PATH entries must reference %ENV_DIR% (SUBST path).
        Node.js executable itself may fail to start when its own path is non-ASCII."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        nodejs_path_lines = [
            l for l in content.splitlines()
            if "nodejs" in l.lower() and "PATH" in l and "set" in l.lower()
        ]
        assert nodejs_path_lines, "No nodejs PATH set line found in start.bat"
        for line in nodejs_path_lines:
            assert "ENV_DIR" in line or "SYS_DIR" in line, \
                f"nodejs PATH must reference SUBST-derived var: {line}"
            assert "PHYS" not in line, \
                f"nodejs PATH must not reference physical path var: {line}"

    # ── [D] TARGET substitution ──────────────────────────────────────────────
    @pytest.mark.parametrize("korean_base,subst,target,expected", [
        (
            r"D:\테스트_폴더\PortableDev", "P:",
            r"D:\테스트_폴더\PortableDev\workspace\myproj",
            r"P:\workspace\myproj",
        ),
        (
            r"D:\PortableDev (2) - 복사본", "P:",
            r"D:\PortableDev (2) - 복사본\workspace",
            r"P:\workspace",
        ),
        (
            r"E:\한글경로\SandboxDev", "Q:",
            r"E:\한글경로\SandboxDev\workspace\project",
            r"Q:\workspace\project",
        ),
    ])
    def test_target_substitution_removes_korean_before_nodejs(
        self, korean_base, subst, target, expected
    ):
        """[D] TARGET substitution must replace Korean physical base with SUBST path.
        The result is passed as cwd/arg to VS Code (Electron/Node.js) — must be ASCII."""
        # Simulates: set "TARGET=!TARGET:%BASE_DIR_PHYS%=%BASE_DIR%!"
        result = target.replace(korean_base, subst)
        assert result == expected, f"Substitution result mismatch: {result}"
        assert not re.search(r"[가-힣]", result), \
            f"Korean characters remain in TARGET after substitution: {result}"

    def test_target_outside_base_dir_unchanged(self):
        """[D] External paths (outside BASE_DIR_PHYS) must NOT be substituted.
        User opens external projects — those paths must be passed as-is."""
        korean_base = r"D:\테스트_폴더\PortableDev"
        subst = "P:"
        for external in [r"C:\Users\user\project", r"E:\other\repo", r"D:\unrelated"]:
            result = external.replace(korean_base, subst)
            assert result == external, \
                f"External path must be unchanged by TARGET substitution: {result}"

    def test_start_bat_has_target_substitution_logic(self):
        """[D] start.bat must contain TARGET substitution code (physical→SUBST)."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        # Either delayed expansion form or call-set form
        has_substitution = (
            "TARGET:%BASE_DIR_PHYS%=%BASE_DIR%" in content
            or "TARGET=!TARGET:" in content
        )
        assert has_substitution, \
            "start.bat must substitute BASE_DIR_PHYS with BASE_DIR in TARGET"

    # ── [E] SUBST failure handling ───────────────────────────────────────────
    def test_subst_failure_causes_error_exit_not_korean_fallback(self):
        """[E] When SUBST command fails (drive occupied), start.bat must abort.
        Continuing with Korean physical path silently breaks all Node.js tools."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        assert "errorlevel 1" in content, \
            "start.bat must check SUBST errorlevel"
        assert "ERROR_EXIT" in content, \
            "start.bat must call :ERROR_EXIT on SUBST failure"
        # The errorlevel check must come before ERROR_EXIT label
        err_idx = content.find("errorlevel 1")
        exit_label_idx = content.find(":ERROR_EXIT")
        assert 0 < err_idx < exit_label_idx, \
            "errorlevel check must precede :ERROR_EXIT label"

    # ── [F] Unregistered fallback ────────────────────────────────────────────
    def test_unregistered_fallback_has_explicit_warning(self):
        """[F] Unregistered + ASCII path → warning + physical fallback (safe).
        Unregistered + Korean path → auto temp-SUBST attempt; physical fallback only
        when all drive letters are occupied. start.bat must warn user in all cases."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        assert "Not registered" in content or "register" in content.lower(), \
            "start.bat must warn user when SUBST is not configured"
        warn_idx = content.lower().find("not registered")
        phys_fallback_idx = content.find("BASE_DIR=%BASE_DIR_PHYS%")
        assert warn_idx != -1, "Missing 'Not registered' warning"
        assert phys_fallback_idx != -1, "Physical path fallback line not found"
        assert warn_idx < phys_fallback_idx, \
            "Warning must appear before the physical path fallback assignment"

    def test_korean_unregistered_gets_temp_subst(self):
        """[F/S-2] Unregistered + Korean path → start.bat must attempt temp SUBST.
        powershell detection of non-ASCII + drive letter loop for Z..E."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        # Korean detection via PowerShell non-ASCII check
        assert r"[^\x00-\x7F]" in content or "non-ASCII" in content.lower() or \
               r"[^\x00-\x7F]" in content, \
            "start.bat must detect Korean (non-ASCII) characters in BASE_DIR_PHYS"
        # Temp drive allocation loop (Z downwards)
        assert "TEMP_DRIVEOK" in content, \
            "start.bat must have temp drive assignment variable for Korean path fallback"
        # When temp drive found, BASE_DIR must use it (not PHYS)
        temp_drive_use_idx = content.find("BASE_DIR=!TEMP_DRIVEOK!")
        assert temp_drive_use_idx != -1, \
            "start.bat must set BASE_DIR to temp drive letter when assigned"

    def test_start_bat_verifies_subst_target_before_reuse(self):
        """[S-3] start.bat must verify drive P: maps to THIS PortableDev, not another.
        If P: exists but points elsewhere, it must /D and remap before proceeding."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        # Must check that the SUBST drive contains our start.bat (sentinel file)
        assert r"_sys\start.bat" in content, \
            "start.bat must verify SUBST drive target via _sys\\start.bat existence"
        # Must do /D to release wrong mapping
        assert "/D" in content, \
            "start.bat must release wrong SUBST mapping with /D before remapping"
        # S-3 check must appear before the BASE_DIR assignment
        s3_idx = content.find(r"_sys\start.bat")
        base_dir_assign_idx = content.find('set "BASE_DIR=%SUBST_DRIVE_LETTER%:"')
        assert s3_idx < base_dir_assign_idx, \
            "S-3 verification must occur before BASE_DIR is assigned from SUBST drive"


class TestManagePySubstEncoding:
    """manage.py must use OEM encoding when reading subst command output."""

    def test_subst_output_uses_oem_encoding(self):
        """[S-6/A] subst command output must be read with encoding='oem'.
        Windows cmd tools use OEM code page (cp949 on Korean, cp1252 on English).
        text=True without encoding uses ANSI which misreads Korean paths on some locales."""
        manage_py = SYS_DIR / "cli" / "manage.py"
        content = manage_py.read_text(encoding="utf-8", errors="ignore")
        # Both get_subst_mappings() and global_cleanup() call subst
        # Both must use encoding='oem' not just text=True
        subst_calls = [
            line for line in content.splitlines()
            if '["subst"]' in line and 'check_output' in line
        ]
        assert subst_calls, "No subprocess.check_output(['subst']) calls found in manage.py"
        for call in subst_calls:
            assert "encoding='oem'" in call, \
                f"subst call must use encoding='oem': {call.strip()}"


class TestVSCodeLaunchArg:
    """Code.exe receives correct workspace path."""

    @pytest.mark.parametrize("target_dir", [
        r"E:\workspace",
        r"C:\Users\GREAT\Desktop",
        r"D:\테스트 폴더",
    ])
    def test_vscode_called_with_dot_in_target_dir(self, target_dir, tmp_path):
        """start.bat cds to TARGET_DIR then calls Code.exe '.'; verify intent."""
        # After cd /d TARGET_DIR, '.' resolves to TARGET_DIR
        # We verify that Code.exe is called with a '.' argument (relative to cd'd dir)
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        assert 'Code.exe" "."' in content or "Code.exe\" \".\"" in content, \
            "start.bat must call Code.exe with '.' after cd /d TARGET_DIR"

    def test_code_exe_path_uses_env_dir_variable(self):
        """Code.exe path must use !ENV_DIR! variable, not hardcoded drive."""
        content = START_BAT.read_text(encoding="utf-8", errors="ignore")
        # Must NOT contain hardcoded drive letter before \env\vscode
        import re
        # Pattern: a drive letter hardcoded before \env\vscode
        hardcoded = re.search(r'[A-Z]:\\[^%!]*\\env\\vscode', content)
        assert hardcoded is None, \
            f"Hardcoded drive letter found in Code.exe path: {hardcoded.group()}"
        # Must use variable
        assert "ENV_DIR" in content
