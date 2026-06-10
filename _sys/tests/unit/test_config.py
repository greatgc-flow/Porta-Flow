import pytest
import os
import json
from pathlib import Path
import sys

# Ensure core is reachable
sys_dir = Path(__file__).parent.parent.parent.resolve()
if str(sys_dir) not in sys.path:
    sys.path.insert(0, str(sys_dir))

from core.config import ConfigManager

def test_config_singleton():
    c1 = ConfigManager()
    c2 = ConfigManager()
    assert c1 is c2

def test_config_lazy_load_and_save(tmp_path):
    # Override config path for testing
    ConfigManager._config_path = tmp_path / "config.json"
    ConfigManager._config = None # Reset
    
    # Test fallback to empty
    assert ConfigManager.get("SOME_KEY", "default") == "default"
    
    # Test save
    ConfigManager.set("TEST_KEY", "VALUE")
    
    assert (tmp_path / "config.json").exists()
    
    with open(tmp_path / "config.json", "r") as f:
        data = json.load(f)
    assert data["TEST_KEY"] == "VALUE"
