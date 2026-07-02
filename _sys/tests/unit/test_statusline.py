"""
Statusline Unification Tests — TDD for unified statusline architecture.

Validates:
1. Schema file exists and is well-formed
2. Unified script exists
3. All peer adapters exist and reference the unified script
4. infra.json registers all statusline paths
5. Codex config.toml follows unified field order
6. Hub status command still works
"""
import json
import subprocess
import pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
SYS_DIR = ROOT / "_sys"


class TestStatuslineSchema:
    """Validate the unified statusline schema."""

    def test_schema_exists(self):
        schema_path = SYS_DIR / "ai" / "common" / "statusline" / "statusline-schema.json"
        assert schema_path.exists(), f"Missing: {schema_path}"

    def test_schema_valid_json(self):
        schema_path = SYS_DIR / "ai" / "common" / "statusline" / "statusline-schema.json"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "fields" in data
        assert "peer_mapping" in data
        assert "separator" in data

    def test_schema_has_required_fields(self):
        schema_path = SYS_DIR / "ai" / "common" / "statusline" / "statusline-schema.json"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        field_ids = [f["id"] for f in data["fields"]]
        assert "peer_model" in field_ids
        assert "context" in field_ids
        assert "location" in field_ids
        assert "rate_limits" in field_ids

    def test_schema_has_all_peers(self):
        schema_path = SYS_DIR / "ai" / "common" / "statusline" / "statusline-schema.json"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        peers = data["peer_mapping"]
        assert "cc" in peers
        assert "ag" in peers
        assert "cx" in peers

    def test_schema_peer_mechanisms(self):
        schema_path = SYS_DIR / "ai" / "common" / "statusline" / "statusline-schema.json"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        peers = data["peer_mapping"]
        assert peers["cc"]["mechanism"] == "command_script"
        assert peers["ag"]["mechanism"] == "command_script"
        assert peers["cx"]["mechanism"] == "builtin_enum"


class TestStatuslineScripts:
    """Validate that all statusline scripts exist."""

    def test_unified_script_exists(self):
        unified = SYS_DIR / "ai" / "common" / "statusline" / "statusline-unified.sh"
        assert unified.exists(), f"Missing unified script: {unified}"

    def test_cc_adapter_exists(self):
        cc = SYS_DIR / "claude" / "config" / "statusline-command.sh"
        assert cc.exists(), f"Missing cc adapter: {cc}"

    def test_ag_adapter_exists(self):
        ag = SYS_DIR / "antigravity" / "config" / "statusline-command.sh"
        assert ag.exists(), f"Missing ag adapter: {ag}"

    def test_cc_adapter_references_unified(self):
        cc = SYS_DIR / "claude" / "config" / "statusline-command.sh"
        content = cc.read_text(encoding="utf-8")
        assert "statusline-unified.sh" in content, "cc adapter must reference unified script"

    def test_ag_adapter_references_unified(self):
        ag = SYS_DIR / "antigravity" / "config" / "statusline-command.sh"
        content = ag.read_text(encoding="utf-8")
        assert "statusline-unified.sh" in content, "ag adapter must reference unified script"

    def test_cc_adapter_uses_peer_id_cc(self):
        cc = SYS_DIR / "claude" / "config" / "statusline-command.sh"
        content = cc.read_text(encoding="utf-8")
        assert '"cc"' in content, "cc adapter must pass peer_id 'cc'"

    def test_ag_adapter_uses_peer_id_ag(self):
        ag = SYS_DIR / "antigravity" / "config" / "statusline-command.sh"
        content = ag.read_text(encoding="utf-8")
        assert '"ag"' in content, "ag adapter must pass peer_id 'ag'"


class TestStatuslineConfig:
    """Validate peer configuration files reference statusline."""

    def test_cc_settings_has_statusline(self):
        settings = SYS_DIR / "claude" / "config" / "settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        assert "statusLine" in data
        assert data["statusLine"]["type"] == "command"

    def test_ag_settings_has_statusline(self):
        settings = SYS_DIR / "antigravity" / "config" / "settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        assert "statusLine" in data
        assert data["statusLine"]["type"] == "command"
        assert data["statusLine"].get("enabled") is True

    def test_cx_config_has_status_line(self):
        config = SYS_DIR / "codex" / "config" / "config.toml"
        content = config.read_text(encoding="utf-8")
        assert "status_line" in content
        assert "model-with-reasoning" in content

    def test_cx_field_order_model_first(self):
        """Codex status_line should start with model (unified order)."""
        config = SYS_DIR / "codex" / "config" / "config.toml"
        content = config.read_text(encoding="utf-8")
        # Find the status_line array
        for line in content.splitlines():
            if line.strip().startswith("status_line"):
                # model-with-reasoning should be first
                assert line.index("model-with-reasoning") > 0  # Should be in the line
                if "current-dir" in line:
                    model_pos = line.index("model-with-reasoning")
                    dir_pos = line.index("current-dir")
                    assert model_pos < dir_pos, "model must come before dir in unified order"
                break


class TestInfraRegistration:
    """Validate infra.json has all statusline paths registered."""

    def test_infra_cc_statusline(self):
        infra = json.loads((SYS_DIR / "ai" / "infra.json").read_text(encoding="utf-8"))
        assert "statusline" in infra["config_registry"]["cc"]

    def test_infra_ag_statusline(self):
        infra = json.loads((SYS_DIR / "ai" / "infra.json").read_text(encoding="utf-8"))
        assert "statusline" in infra["config_registry"]["ag"]

    def test_infra_cx_statusline(self):
        infra = json.loads((SYS_DIR / "ai" / "infra.json").read_text(encoding="utf-8"))
        assert "statusline_config" in infra["config_registry"]["cx"]

    def test_infra_common_unified(self):
        infra = json.loads((SYS_DIR / "ai" / "infra.json").read_text(encoding="utf-8"))
        assert "statusline_unified" in infra["config_registry"]["common"]
        assert "statusline_schema" in infra["config_registry"]["common"]

    def test_infra_statusline_paths_exist(self):
        """All registered statusline paths must point to real files."""
        infra = json.loads((SYS_DIR / "ai" / "infra.json").read_text(encoding="utf-8"))
        base = ROOT
        paths_to_check = [
            infra["config_registry"]["cc"]["statusline"],
            infra["config_registry"]["ag"]["statusline"],
            infra["config_registry"]["cx"]["statusline_config"],
            infra["config_registry"]["common"]["statusline_unified"],
            infra["config_registry"]["common"]["statusline_schema"],
        ]
        for rel_path in paths_to_check:
            full = base / rel_path
            assert full.exists(), f"Registered path missing: {rel_path} → {full}"


class TestStatuslineHubIntegration:
    """Validate the hub status command still works (regression)."""

    @pytest.fixture
    def test_env(self, tmp_path):
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir(exist_ok=True)
        venv_py = ROOT / "_sys" / "env" / "venv" / "Scripts" / "python.exe"
        hub_py = ROOT / "_sys" / "core" / "hub.py"
        return {"root": tmp_path, "venv_py": venv_py, "hub_py": hub_py}

    def test_status_still_works(self, test_env):
        res = subprocess.run(
            [str(test_env["venv_py"]), str(test_env["hub_py"]), "status"],
            cwd=test_env["root"],
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )
        assert res.returncode == 0
