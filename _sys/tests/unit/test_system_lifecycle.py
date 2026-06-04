"""
시스템 라이프사이클 테스트 (SYS)
Register, Unregister, Cleanup 기능의 MECE 시나리오 검증.
"""
import os
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# 테스트 대상 모듈 로드 (절대 경로)
import sys
sys_path = Path(__file__).parent.parent.parent / "cli"
sys.path.append(str(sys_path))
import manage
import cleanup

class TestSystemLifecycle:

    @pytest.fixture
    def mock_env(self, tmp_path):
        """테스트를 위한 모의 환경 (BASE_DIR 및 관련 폴더)."""
        base_dir = tmp_path / "PortableDev"
        sys_dir = base_dir / "_sys"
        sys_dir.mkdir(parents=True)
        (sys_dir / "cli").mkdir()
        (sys_dir / "env").mkdir()
        (sys_dir / "data").mkdir()
        (sys_dir / "tools").mkdir()
        (base_dir / "workspace").mkdir()
        (base_dir / "_archive").mkdir()
        
        # 더미 파일 생성
        (base_dir / "README.md").write_text("dummy", encoding="utf-8")
        (sys_dir / "local.config.bat").write_text(":: user config", encoding="utf-8")
        
        return base_dir

    @patch("winreg.CreateKey")
    @patch("winreg.SetValueEx")
    @patch("subprocess.run")
    @patch("subprocess.check_output", return_value="")
    @patch("winreg.OpenKey", side_effect=OSError)
    def test_registration_flow_sys_r1_r2(self, mock_open_key, mock_check_out, mock_run, mock_set_val, mock_create_key, mock_env):
        """SYS-R1, SYS-R2: 등록 및 해제 흐름 검증."""
        os.environ.setdefault("USERPROFILE", str(mock_env.parent))
        # 1. Register 실행
        manage.action_register(mock_env)
        
        # subst 호출 확인
        assert any("subst" in str(call.args[0]) for call in mock_run.call_args_list)
        # registry 호출 확인
        assert mock_create_key.called
        assert mock_set_val.called
        
        # local.config.bat 생성 확인
        config = (mock_env / "_sys" / "local.config.bat").read_text(encoding="utf-8")
        assert "SUBST_DRIVE_LETTER" in config
        assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" in config

        # 2. Unregister 실행
        mock_run.reset_mock()
        mock_check_out.reset_mock()
        manage.action_unregister(mock_env)

        # local.config.bat 정리 확인 (auto 블록 삭제됨)
        config_after = (mock_env / "_sys" / "local.config.bat").read_text(encoding="utf-8")
        assert "SUBST_DRIVE_LETTER" not in config_after
        assert ":: user config" in config_after

    def test_cleanup_tiers_sys_c1(self, mock_env):
        """SYS-C1: 클린업 티어별 MECE 검증."""
        # 더미 데이터 생성
        (mock_env / "_sys" / "data" / "temp").mkdir()
        (mock_env / "_sys" / "data" / "temp" / "junk.tmp").write_text("junk")
        (mock_env / "_sys" / "env" / "venv").mkdir()

        # 1. Tier 1 (Light) - 임시 파일 삭제 확인
        cleanup.run_cleanup(tier=1, all_yes=True, base_dir=mock_env)
        assert not (mock_env / "_sys" / "data" / "temp").exists()
        assert (mock_env / "_sys" / "env" / "venv").exists()  # Tier 1에선 유지

        # 2. Tier 2 (Hard) - venv 삭제 확인
        cleanup.run_cleanup(tier=2, all_yes=True, base_dir=mock_env)
        assert not (mock_env / "_sys" / "env" / "venv").exists()
        assert (mock_env / "workspace").exists()  # Tier 2에선 유지

        # 3. Tier 4 (ZeroBase) - 전체 삭제 확인
        cleanup.run_cleanup(tier=4, all_yes=True, base_dir=mock_env)
        assert not (mock_env / "workspace").exists()
        assert not (mock_env / "_archive").exists()
        assert not (mock_env / "README.md").exists()  # 루트 문서 삭제됨
        assert not (mock_env / "_sys" / "local.config.bat").exists()

    @patch("manage.global_cleanup")
    @patch("manage.set_gemini_portability")
    @patch("winreg.CreateKey")
    @patch("winreg.SetValueEx")
    @patch("subprocess.run")
    @patch("subprocess.check_output", return_value="")
    def test_registration_migration_sys_r3(self, mock_co, mock_run, mock_set_val, mock_create_key, mock_sgp, mock_gc, mock_env, tmp_path):
        """SYS-R3: 경로 이동 후 재등록 시 이전 정보 정리 검증."""
        # 1. 첫 번째 경로 등록
        manage.action_register(mock_env)

        # 2. 경로 이동 모의 (새로운 경로에서 Register 호출)
        new_env = tmp_path / "MovedPortableDev"
        shutil.copytree(mock_env, new_env)

        # 새로운 경로에서 등록 시 global_cleanup이 호출되는지 확인
        manage.action_register(new_env)
        assert mock_gc.called
