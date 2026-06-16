import os
from pathlib import Path

BASE_DIR = Path("D:/PortableDev (v2.0)")
NEW_SYS = BASE_DIR / "_sys_new"
HUB_PY = NEW_SYS / "core/hub.py"

def patch_hub():
    if not HUB_PY.exists():
        print(f"Error: {HUB_PY} not found")
        return

    content = HUB_PY.read_text(encoding="utf-8")
    
    # 1. Update load functions
    replacements = {
        'Path(__file__).parent.parent / "ai" / "orchestration.json"': 'Path(__file__).parent.parent / "config" / "integrations" / "orchestration.json"',
        'Path(__file__).parent.parent / "ai" / "protocol.json"': 'Path(__file__).parent.parent / "config" / "protocol" / "protocol.json"',
        'Path(__file__).parent.parent / "ai" / "lifecycle_policy.json"': 'Path(__file__).parent.parent / "config" / "protocol" / "lifecycle.json"',
        'Path(__file__).parent.parent / "ai" / "model_profiles.json"': 'Path(__file__).parent.parent / "config" / "protocol" / "model-profiles.json"',
        'Path(__file__).parent.parent / "ai" / "peers.json"': 'Path(__file__).parent.parent / "config" / "peers" / "registry.json"',
        'sys_dir / "ai" / "status_checks.json"': 'sys_dir / "config" / "integrations" / "status-checks.json"',
        'Path(__file__).parent.parent / "ai" / "user-directives.md"': 'Path(__file__).parent.parent / "common" / "user-directives.md"',
        'Path(__file__).parent.parent / "ai" / "runtime-directives.jsonl"': 'ai_root / "state" / "runtime-directives.jsonl"', # Corrected for dual write/data
        'Path(__file__).parent.parent / "ai" / "knowledge"': 'Path(__file__).parent.parent / "knowledge"',
        'Path(__file__).parent.parent / subdir': 'Path(__file__).parent.parent / "peers" / peer_id',
    }

    # Special handling for _peer_sys_dir to match the new structure: peers/{id}
    new_peer_sys_dir = """def _peer_sys_dir(peer_id: str) -> Path:
    \"\"\"registry.json의 sys_subdir로 _sys/peers/{id} 해석.\"\"\"
    return Path(__file__).parent.parent / "peers" / peer_id
"""
    # Find the old function and replace it
    import re
    content = re.sub(r'def _peer_sys_dir\(peer_id: str\) -> Path:.*?return Path\(__file__\)\.parent\.parent / subdir', new_peer_sys_dir, content, flags=re.DOTALL)

    for old, new in replacements.items():
        content = content.replace(old, new)

    # 2. Update _runtime_directives_path to data/state
    content = content.replace('return Path(__file__).parent.parent / "ai" / "runtime-directives.jsonl"', 'return ai_root / "state" / "runtime-directives.jsonl" if ai_root else Path(__file__).parent.parent / "data" / "state" / "runtime-directives.jsonl"')

    HUB_PY.write_text(content, encoding="utf-8")
    print(f"Patched {HUB_PY}")

if __name__ == "__main__":
    patch_hub()
