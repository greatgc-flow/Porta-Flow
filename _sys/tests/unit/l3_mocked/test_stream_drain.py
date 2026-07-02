import os
import sys
import subprocess
import threading
import time
import pytest
from pathlib import Path

# Add core to sys.path to import hub
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core import hub

def test_stream_process_output_drain(tmp_path):
    """
    Test that _stream_process_output fully drains stdout and stderr
    even if the process exits quickly or produces a lot of stderr.
    """
    script_path = tmp_path / "dummy.py"
    script_path.write_text("""
import sys
import time

print("STDOUT 1")
print("STDERR 1", file=sys.stderr)
sys.stderr.flush()
sys.stdout.flush()
time.sleep(0.1)
print("STDOUT 2")
print("STDERR 2", file=sys.stderr)
""", encoding="utf-8")

    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    output_bytes, process_err_bytes = hub._stream_process_output(
        proc=proc,
        cmd=["dummy.py"],
        input_bytes=None,
        heartbeat_sec=1.0,
        zombie_timeout_sec=5.0,
        startup_timeout_sec=5.0,
        timeout_sec=5.0,
        ai_root=tmp_path,
        to="dummy",
        lease_timeout_sec=5.0
    )
    
    output_str = output_bytes.decode('utf-8')
    process_err_str = process_err_bytes.decode('utf-8')

    assert "STDOUT 1" in output_str
    assert "STDOUT 2" in output_str
    assert "STDERR 1" in process_err_str
    assert "STDERR 2" in process_err_str
