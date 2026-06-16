import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path("D:/PortableDev (v2.0)")
OLD_SYS = BASE_DIR / "_sys"
NEW_SYS = BASE_DIR / "_sys_new"

def run_cmd(cmd):
    print(f"Running: {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def migrate():
    # 1. Create NEW_SYS
    if NEW_SYS.exists():
        print(f"Removing existing {NEW_SYS}...")
        run_cmd(f'rmdir /s /q "{NEW_SYS}"')
    
    NEW_SYS.mkdir(parents=True, exist_ok=True)
    print(f"Created {NEW_SYS}")

    # 2. Junction Stubs (env/tools)
    print("Creating junction stubs...")
    run_cmd(f'mklink /J "{NEW_SYS / "env"}" "{OLD_SYS / "env"}"')
    run_cmd(f'mklink /J "{NEW_SYS / "tools"}" "{OLD_SYS / "tools"}"')

    # 3. Create To-Be Root Dirs
    roots = ["config", "core", "peers", "knowledge", "protocol", "runtime", "common", "templates", "tests", "data"]
    for r in roots:
        (NEW_SYS / r).mkdir(parents=True, exist_ok=True)

    # 4. Define Migration Mapping (from sys-restructure-plan.md §4-2)
    # Mapping: OLD_REL_PATH -> NEW_REL_PATH (relative to OLD_SYS / NEW_SYS)
    mapping = {
        # Configs
        "runtimes.json": "config/general/runtimes.json",
        "dispatch.json": "config/integrations/dispatch.json",
        "context_menu.json": "config/integrations/context-menu.json",
        "ai/protocol.json": "config/protocol/protocol.json",
        "ai/peers.json": "config/peers/registry.json",
        "ai/orchestration.json": "config/integrations/orchestration.json",
        "ai/lifecycle_policy.json": "config/protocol/lifecycle.json",
        "ai/model_profiles.json": "config/protocol/model-profiles.json",
        "ai/governance_params.json": "config/protocol/governance.json",
        "ai/status_checks.json": "config/integrations/status-checks.json",
        "ai/traceability_map.json": "config/integrations/traceability.json",
        "ai/infra.json": "config/integrations/infra.json",
        "core/hub_config.json": "config/integrations/hub-config.json",
        "ai/knowledge.config.json": "config/protocol/knowledge-policy.json",
        "ai/collaboration_policy.schema.json": "knowledge/schemas/collaboration_policy.schema.json",
        "ai/runtime-directives.jsonl": "data/state/runtime-directives.jsonl",
        "ai/user-directives.md": "common/user-directives.md",
        
        # Peer Dirs (Selective migration)
        "claude/health.json": "peers/cc/health.json",
        "gemini/health.json": "peers/gc/health.json",
        "codex/health.json": "peers/cx/health.json",
        "antigravity/health.json": "peers/ag/health.json",
        "gemini/session_state.json": "peers/gc/session_state.json",
        "codex/session_state.json": "peers/cx/session_state.json",
        
        # Docs -> Protocol (Using history as source for protocol files)
        "docs/history/DEBATE_PROTOCOL.md": "protocol/general/DEBATE_PROTOCOL.md",
        "docs/history/DEBATE_LOG.md": "protocol/general/DEBATE_LOG.md",
        "docs/history/PROTOCOL_INVARIANTS.md": "protocol/general/PROTOCOL_INVARIANTS.md",
        "docs/history/collaboration_protocol.md": "protocol/general/collaboration.md",
        "docs/history/protocol-health.md": "protocol/general/health.md",
        "docs/history/protocol-session.md": "protocol/general/session.md",
        "docs/history/protocol-codex.md": "protocol/peer-specific/cx/CODEX.md",
        "docs/history/protocol-antigravity.md": "protocol/peer-specific/ag/AGY.md",
        "docs/user/USER_MANUAL.md": "protocol/reference/USER_MANUAL.md",
        "docs/history/TAXONOMY_v11.md": "protocol/reference/TAXONOMY_v11.md",
        
        # Runtime (CLI/Hooks/Checks)
        "cli": "runtime/cli",
        "hooks": "runtime/hooks",
        "checks": "runtime/checks",
        
        # Core & Common & Templates
        "core": "core",
        "ai/common": "common",
        "ai/knowledge": "knowledge",
        "templates": "templates",
        "tests": "tests",
        "data": "data"
    }

    print("Migrating files...")
    for old_rel, new_rel in mapping.items():
        src = OLD_SYS / old_rel
        dst = NEW_SYS / new_rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                print(f"Copying DIR {old_rel} -> {new_rel}")
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                print(f"Copying FILE {old_rel} -> {new_rel}")
                shutil.copy2(src, dst)
        else:
            print(f"Skipping missing source: {old_rel}")

    # 5. Create peer-specific peer.json files
    print("Creating peer.json files...")
    peer_data = {
        "gc": {"display_name": "Gemini CLI", "sys_subdir": "peers/gc", "glue_file": "runtime/config/GEMINI.md", "glue_source": "protocol/peer-specific/gc/GEMINI.md"},
        "cc": {"display_name": "Claude Code", "sys_subdir": "peers/cc", "glue_file": "runtime/config/CLAUDE.md", "glue_source": "protocol/peer-specific/cc/CLAUDE.md"},
        "cx": {"display_name": "Codex", "sys_subdir": "peers/cx", "glue_file": "runtime/config/CODEX.md", "glue_source": "protocol/peer-specific/cx/CODEX.md"},
        "ag": {"display_name": "Antigravity", "sys_subdir": "peers/ag", "glue_file": "runtime/config/AGY.md", "glue_source": "protocol/peer-specific/ag/AGY.md"}
    }
    for p_id, p_info in peer_data.items():
        dst_p = NEW_SYS / "peers" / p_id / "peer.json"
        import json
        with open(dst_p, "w", encoding="utf-8") as f:
            json.dump(p_info, f, indent=2)

    # 6. Build Phase 1+2 PART B: Config Centralization
    # (Already mostly done by mapping above)
    
    # 7. Add recovery scripts
    (NEW_SYS / "runtime/recovery").mkdir(parents=True, exist_ok=True)
    # We will create these separately or copy them.
    
    print("Build Phase completed in _sys_new.")

if __name__ == "__main__":
    migrate()
