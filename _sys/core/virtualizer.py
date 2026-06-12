"""
virtualizer.py - SUBST drive mapping and directory junction management.
All peer junction mappings sourced from peers.json. No hardcoding.
"""
import os
import re
import json
import shutil
import subprocess
from pathlib import Path


def _load_peers(sys_dir: Path) -> dict:
    p = sys_dir / "ai" / "peers.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("peers", {})
        except Exception:
            pass
    return {}


def _load_state(ctx: dict) -> dict:
    state_file = ctx["paths"]["state"] / "register.state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return ctx.get("prior_state", {})


def _cmd(command: str) -> None:
    subprocess.run(command, shell=True, check=True, capture_output=True)


def _get_subst_mappings() -> dict:
    mappings = {}
    try:
        out = subprocess.check_output(["subst"], text=True, encoding="oem")
        for line in out.splitlines():
            m = re.match(r"^([A-Z]):\\: => (.*)$", line, re.IGNORECASE)
            if m:
                mappings[m.group(1).upper()] = Path(m.group(2).strip())
    except Exception:
        pass
    return mappings


def _assign_subst(base_dir: Path, sys_dir: Path) -> str | None:
    """Assign a SUBST drive letter. Returns the letter or None."""
    import json as _json
    orch_path = sys_dir / "ai" / "orchestration.json"
    orch = {}
    if orch_path.exists():
        try:
            orch = _json.loads(orch_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    subst_cfg = orch.get("subst", {})
    reserved  = subst_cfg.get("reserved_letters", ["A", "B", "C"])
    default_prefer = subst_cfg.get("default_preference_letter", "P")

    subst_map = _get_subst_mappings()

    # Reuse existing mapping if already ours
    for letter, path in subst_map.items():
        if path.resolve() == base_dir.resolve():
            print(f"  [OK] Reusing SUBST mapping: {letter}: → {base_dir}")
            return letter

    prefer = base_dir.name[0].upper()
    if not ("A" <= prefer <= "Z"):
        prefer = default_prefer
    candidates = [prefer] + [chr(x) for x in range(65, 91) if chr(x) not in reserved and chr(x) != prefer]

    for letter in candidates:
        if letter in subst_map:
            mapped = subst_map[letter]
            if not mapped.exists():
                subprocess.run(["subst", f"{letter}:", "/D"], capture_output=True)
            else:
                continue
        if not os.path.exists(f"{letter}:\\"):
            try:
                subprocess.run(["subst", f"{letter}:", str(base_dir)], check=True)
                print(f"  [OK] SUBST: {base_dir} → {letter}:")
                return letter
            except Exception:
                continue
    print("  [Warning] No SUBST drive could be assigned — continuing without virtual drive")
    return None


def _release_subst(base_dir: Path) -> None:
    subst_map = _get_subst_mappings()
    for letter, path in subst_map.items():
        if path.resolve() == base_dir.resolve():
            subprocess.run(["subst", f"{letter}:", "/D"], capture_output=True)
            print(f"  [OK] Released SUBST: {letter}:")
            return
    # Also try from saved state
    # (handled by caller via prior_state)


def _ensure_junction(host: Path, portable: Path) -> None:
    """Create host → portable junction. Migrates existing real directory."""
    portable.mkdir(parents=True, exist_ok=True)
    is_reparse = False
    try:
        st = host.lstat()
        if os.path.islink(host) or getattr(st, "st_reparse_tag", 0) == 0xA0000003:
            is_reparse = True
    except FileNotFoundError:
        pass

    if is_reparse:
        _cmd(f'rmdir "{host}"')
    elif host.exists():
        for item in list(host.iterdir()):
            if item.name == "settings.local.json":
                item.unlink()
                continue
            dest = portable / item.name
            if dest.exists():
                shutil.rmtree(str(dest)) if dest.is_dir() else dest.unlink()
            shutil.move(str(item), str(portable))
        host.rmdir()
    _cmd(f'mklink /J "{host}" "{portable}"')


def _remove_junction(host: Path) -> None:
    try:
        st = host.lstat()
        is_reparse = os.path.islink(host) or getattr(st, "st_reparse_tag", 0) == 0xA0000003
    except Exception:
        return
    if is_reparse:
        try:
            host.unlink()
        except Exception:
            try:
                os.rmdir(host)
            except Exception as e:
                print(f"  [Fail] Could not remove junction {host}: {e}")


def _set_peer_junctions(base_dir: Path, peer_id: str, peer: dict, sys_dir: Path) -> list:
    """Create host + project junctions for a peer. Returns list of created junction records."""
    records = []
    sub = sys_dir / peer.get("sys_subdir", peer_id)

    host_j = peer.get("host_junction")
    if host_j:
        host_env     = host_j.get("host_env")
        host_dirname = host_j.get("host_dirname")
        portable_sub = host_j.get("portable_subpath", "config")
        if host_env in os.environ:
            host_path     = Path(os.environ[host_env]) / host_dirname
            portable_path = sub / portable_sub
            portable_path.mkdir(parents=True, exist_ok=True)
            try:
                _ensure_junction(host_path, portable_path)
                print(f"  [OK] {peer_id}: host junction {host_dirname} → _sys/{sub.name}/{portable_sub}")
                records.append({"kind": "host", "host": str(host_path), "target": str(portable_path)})
            except Exception as e:
                print(f"  [Fail] {peer_id}: host junction: {e}")

    proj_j = peer.get("project_junction")
    if proj_j:
        portable_sub = proj_j.get("portable_subpath", "project")
        root_dir     = peer.get("root_dir", f".{peer_id}")
        try:
            _ensure_junction(base_dir / root_dir, sub / portable_sub)
            print(f"  [OK] {peer_id}: project junction {root_dir} → _sys/{sub.name}/{portable_sub}")
            records.append({"kind": "project", "host": str(base_dir / root_dir), "target": str(sub / portable_sub)})
        except Exception as e:
            print(f"  [Fail] {peer_id}: project junction: {e}")

    return records


def _remove_peer_junctions(base_dir: Path, peer_id: str, peer: dict, sys_dir: Path) -> None:
    sub = sys_dir / peer.get("sys_subdir", peer_id)

    host_j = peer.get("host_junction")
    if host_j:
        host_env     = host_j.get("host_env")
        host_dirname = host_j.get("host_dirname")
        if host_env in os.environ:
            host_path = Path(os.environ[host_env]) / host_dirname
            _remove_junction(host_path)
            backup = host_path.with_suffix(".host_backup")
            if backup.exists():
                shutil.move(str(backup), str(host_path))
                print(f"  [Info] {peer_id}: restored host config from backup")
            else:
                print(f"  [OK] {peer_id}: host junction removed ({host_dirname})")

    proj_j = peer.get("project_junction")
    if proj_j:
        root_dir = peer.get("root_dir", f".{peer_id}")
        _remove_junction(base_dir / root_dir)
        print(f"  [OK] {peer_id}: project junction removed ({root_dir})")


def _apply_local_settings(base_dir: Path, peer_id: str, peer_cfg: dict, drive: str, sys_dir: Path) -> None:
    """Write per-peer local settings files (e.g. settings.local.json with drive-specific paths)."""
    peer_subdir = sys_dir / peer_cfg.get("sys_subdir", peer_id)
    base_esc    = str(base_dir).replace("\\", "\\\\")
    for spec in peer_cfg.get("local_settings", []):
        target_rel = spec.get("target", "")
        if not target_rel:
            continue
        target_path = peer_subdir / target_rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content_str = json.dumps(spec.get("content", {}))
        content_str = content_str.replace("{DRIVE}", drive).replace("{BASE_DIR}", base_esc)
        target_path.write_text(json.dumps(json.loads(content_str), indent=4), encoding="utf-8")
        print(f"  [OK] {peer_id}: {target_rel} written")


def mount(ctx: dict) -> None:
    """Assign SUBST drive and create peer junctions."""
    base_dir = ctx["base_dir"]
    sys_dir  = ctx["sys_dir"]
    peers    = _load_peers(sys_dir)

    print(f"\n{'='*50}")
    print(f" Virtualizer: mount — {base_dir.name}")
    print(f"{'='*50}")

    # Peer junctions
    junctions = []
    for peer_id, peer in peers.items():
        if peer.get("enabled", True):
            junctions += _set_peer_junctions(base_dir, peer_id, peer, sys_dir)

    # SUBST drive
    drive = _assign_subst(base_dir, sys_dir)

    # Per-peer local settings
    eff_drive = drive or base_dir.drive.rstrip(":")
    for peer_id, peer_cfg in peers.items():
        if peer_cfg.get("enabled", True) and peer_cfg.get("local_settings"):
            _apply_local_settings(base_dir, peer_id, peer_cfg, eff_drive, sys_dir)

    ctx["state"]["subst_drive"]  = drive
    ctx["state"]["junctions"]    = junctions
    print("\n  Mount complete.")


def unmount(ctx: dict) -> None:
    """Release SUBST drive and remove peer junctions."""
    base_dir    = ctx["base_dir"]
    sys_dir     = ctx["sys_dir"]
    peers       = _load_peers(sys_dir)
    prior_state = _load_state(ctx)

    print(f"\n{'='*50}")
    print(f" Virtualizer: unmount — {base_dir.name}")
    print(f"{'='*50}")

    # Release SUBST
    drive = prior_state.get("subst_drive")
    if drive:
        subprocess.run(["subst", f"{drive}:", "/D"], capture_output=True)
        print(f"  [OK] Released SUBST: {drive}:")
    else:
        _release_subst(base_dir)

    # Remove peer junctions
    for peer_id, peer in peers.items():
        _remove_peer_junctions(base_dir, peer_id, peer, sys_dir)

    # Remove per-peer local settings
    for peer_id, peer_cfg in peers.items():
        sub = sys_dir / peer_cfg.get("sys_subdir", peer_id)
        settings = sub / "project" / "settings.local.json"
        if settings.exists():
            settings.unlink()
            print(f"  [OK] {peer_id}: settings.local.json removed")

    print("\n  Unmount complete.")
