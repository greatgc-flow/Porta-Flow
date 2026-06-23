import subprocess
import pytest
from pathlib import Path

def test_global_exception_trap(tmp_path):
    # Create a dummy script that imports hub and raises an exception
    script = tmp_path / "crash.py"
    script.write_text("""
import sys
from pathlib import Path
# Add _sys to path
sys.path.insert(0, r'P:\\_sys\\core')
import hub
raise ValueError("Intentional crash for TDD")
""")
    
    result = subprocess.run([r"P:\_sys\env\venv\Scripts\python.exe", str(script)], capture_output=True, text=True)
    
    # Verify the output matches our 5-Whys format
    assert "[SYSTEM_FATAL_ERROR]" in result.stderr
    assert "Intentional crash for TDD" in result.stderr
    assert "--- 5-Whys Root Cause Analysis Template ---" in result.stderr
    assert result.returncode == 1
