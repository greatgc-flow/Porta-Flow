import pytest
import os
import json
from pathlib import Path
from _sys.core import env_loader

def test_load_environment_from_json(tmp_path):
    # Setup mock environment.json
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    env_json = config_dir / "environment.json"
    
    config_data = {
        "paths": {
            "base": str(tmp_path).replace("\\", "/"),
            "sys": "{base}/_sys",
            "shared": "{base}/_shared",
            "workspace_template": "{sys}/templates/workspace-base"
        },
        "env_vars": {
            "PYTHONUTF8": "1",
            "TEST_VAR": "SUCCESS"
        }
    }
    env_json.write_text(json.dumps(config_data))

    # Load via updated env_loader
    env_loader.load_json_env(env_json)

    # Verify resolution (no hardcoding)
    assert os.environ.get("TEST_VAR") == "SUCCESS"
    assert os.environ.get("PYTHONUTF8") == "1"
    
    # Check paths resolve correctly
    expected_sys = str(tmp_path / "_sys").replace("\\", "/")
    actual_sys = os.environ.get("SYS_DIR", "").replace("\\", "/")
    assert expected_sys == actual_sys
