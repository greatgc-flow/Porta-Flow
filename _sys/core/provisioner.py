"""
provisioner.py - Binary installation for Portable Dev Environment.
All versions/URLs sourced from runtimes.json. No hardcoding.
"""
import os
import sys
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path


def _load_runtimes(sys_dir: Path) -> tuple[dict, dict, dict]:
    path = sys_dir / "runtimes.json"
    if not path.exists():
        raise FileNotFoundError(f"[Error] runtimes.json not found at {path}")
    raw  = json.loads(path.read_text(encoding="utf-8"))
    data = raw.get("runtimes", {})
    V = {
        "Python": data.get("python", {}).get("version", ""),
        "NodeJS": data.get("nodejs", {}).get("version", ""),
        "Git":    data.get("git",    {}).get("version", ""),
        "VSCode": data.get("vscode", {}).get("version", ""),
        "Pwsh":   data.get("pwsh",   {}).get("version", ""),
    }
    URLS = {
        "NodeJS": data.get("nodejs",  {}).get("url", ""),
        "Git":    data.get("git",     {}).get("url", ""),
        "FFmpeg": data.get("ffmpeg",  {}).get("url", ""),
        "VSCode": data.get("vscode",  {}).get("url", ""),
        "Pwsh":   data.get("pwsh",    {}).get("url", ""),
    }
    return V, URLS, raw.get("tools", {})


def _download(url: str, dest: Path, label: str) -> None:
    print(f"  [i] Downloading {label}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    print(f"  [OK] {dest.name} ({dest.stat().st_size / 1024**2:.1f} MB)")


def _extract(zip_path: Path, dest: Path) -> None:
    print(f"  [i] Extracting {zip_path.name}...")
    try:
        shutil.unpack_archive(str(zip_path), str(dest))
    except Exception:
        subprocess.run(["tar", "-xf", str(zip_path), "-C", str(dest)], check=True)
    print(f"  [OK] Extracted to {dest.name}")


def _load_peers(sys_dir: Path) -> dict:
    p = sys_dir / "ai" / "peers.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("peers", {})
        except Exception:
            pass
    return {}


def _check_python_version(V: dict) -> None:
    running  = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    expected = V.get("Python", "")
    if expected and running != expected:
        print(f"  [!] Python 버전 불일치: 실행={running}, 기대={expected}")
    else:
        print(f"  [OK] Python {running}")


def _install_tools(TOOLS: dict, env_dir: Path, setup_dir: Path, force: bool) -> list:
    installed = []
    if not TOOLS:
        print("  [--] No tools defined in runtimes.json")
        return installed
    tools_dir = env_dir.parent / "tools"
    for name, cfg in TOOLS.items():
        url      = cfg.get("url", "")
        kind     = cfg.get("type", "zip")
        bin_name = cfg.get("bin", f"{name}.exe")
        dest_dir = tools_dir / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        sentinel = dest_dir / bin_name
        if not force and sentinel.exists():
            print(f"  [--] {name} (already installed)")
            installed.append(name)
            continue
        print(f"\n>>> Tool: {name} v{cfg.get('version', '?')}")
        if kind == "exe":
            dl = setup_dir / f"{name}-dl.exe"
            _download(url, dl, name)
            shutil.copy2(str(dl), str(sentinel))
            dl.unlink()
        else:
            zp = setup_dir / f"{name}.zip"
            _download(url, zp, name)
            tmp = setup_dir / f"_{name}_tmp"
            tmp.mkdir(exist_ok=True)
            _extract(zp, tmp)
            for exe in tmp.rglob("*.exe"):
                shutil.copy2(str(exe), str(dest_dir / exe.name))
            shutil.rmtree(tmp)
            zp.unlink(missing_ok=True)
        for extra in cfg.get("extras", []):
            _install_extra(name, extra, dest_dir, setup_dir)
        installed.append(name)
        print(f"  [OK] {name} ready")
    return installed


def _install_extra(tool_name: str, extra: dict, dest_dir: Path, setup_dir: Path) -> None:
    url       = extra.get("url", "")
    kind      = extra.get("type", "zip")
    subfolder = extra.get("dest", "extra")
    extra_dir = dest_dir / subfolder
    if not url:
        return
    extra_dir.mkdir(parents=True, exist_ok=True)
    if kind == "zip":
        zp = setup_dir / f"{tool_name}-extra-{subfolder}.zip"
        _download(url, zp, f"{tool_name}/{subfolder}")
        _extract(zp, extra_dir)
        zp.unlink(missing_ok=True)
        print(f"  [OK] {tool_name}/{subfolder} ready")


def _install_ai_peers(peers: dict, npm_exe: Path, npm_global: Path, env: dict, force: bool) -> list:
    installed = []
    for peer_id, cfg in peers.items():
        if not cfg.get("enabled"):
            continue
        pkg = cfg.get("npm_package")
        if not pkg:
            continue
        print(f"\n>>> AI Peer: {cfg.get('description', peer_id)}")
        peer_cmd = npm_global / f"{peer_id}.cmd"
        if force or not peer_cmd.exists():
            subprocess.run([str(npm_exe), "install", "-g", pkg], env=env, check=True)
            print(f"  [OK] {peer_id} CLI ready")
        else:
            print(f"  [--] {peer_id} CLI (already installed)")
        installed.append(peer_id)
    return installed


def deploy(ctx: dict) -> None:
    """Install all runtimes, tools, and AI peer CLIs."""
    args       = ctx["args"]
    force      = "--force" in args
    skip_vsc   = "--skip-vscode" in args
    skip_ai    = "--skip-ai" in args or "--skip-claude" in args
    sys_dir    = ctx["sys_dir"]
    base_dir   = ctx["base_dir"]
    env_dir    = sys_dir / "env"
    setup_dir  = sys_dir / "data" / "setup-files"
    setup_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n>>> Starting Provisioner (force={force})")
    V, URLS, TOOLS = _load_runtimes(sys_dir)
    peers = _load_peers(sys_dir)
    _check_python_version(V)

    # ── Folder structure ─────────────────────────────────────────
    print("\n>>> Folder structure")
    dirs = [
        env_dir / "python", env_dir / "nodejs", env_dir / "ffmpeg",
        env_dir / "git", env_dir / "vscode", env_dir / "venv", env_dir / "pwsh",
        sys_dir / "tools" / "apps",
        sys_dir / "data" / "logs", sys_dir / "data" / "temp",
        sys_dir / "data" / "state", sys_dir / "data" / "generated",
        base_dir / "workspace",
        sys_dir / "ai" / "common" / "agents",
        sys_dir / "ai" / "common" / "skills",
        sys_dir / "ai" / "common" / "mcp",
        sys_dir / "common" / "scripts",
        sys_dir / "common" / "assets",
    ]
    for peer_id, cfg in peers.items():
        sub = sys_dir / cfg.get("sys_subdir", peer_id)
        dirs += [sub / "config", sub / "project"]
        if cfg.get("sys_subdir"):
            dirs.append(sub / "templates")
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("  [OK] Folder structure ready")

    installed = []

    # ── Node.js ──────────────────────────────────────────────────
    print(f"\n>>> Node.js {V['NodeJS']}")
    node_exe = env_dir / "nodejs" / "node.exe"
    if force or not node_exe.exists():
        zp = setup_dir / "nodejs.zip"
        if force or not zp.exists():
            _download(URLS["NodeJS"], zp, "Node.js")
        tmp = setup_dir / "_nodejs_tmp"
        tmp.mkdir(exist_ok=True)
        _extract(zp, tmp)
        extracted = next(tmp.iterdir())
        if extracted.is_dir():
            for item in extracted.iterdir():
                dest = env_dir / "nodejs" / item.name
                if dest.exists():
                    shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
                shutil.move(str(item), str(env_dir / "nodejs"))
        shutil.rmtree(tmp)
        print("  [OK] Node.js ready")
    else:
        print("  [--] Node.js (already installed)")
    installed.append("nodejs")

    # ── Git ──────────────────────────────────────────────────────
    print(f"\n>>> Git {V['Git']} (portable)")
    git_exe = env_dir / "git" / "cmd" / "git.exe"
    if force or not git_exe.exists():
        exe_path = setup_dir / "PortableGit.7z.exe"
        if force or not exe_path.exists():
            _download(URLS["Git"], exe_path, "Git Portable")
        subprocess.run([str(exe_path), f"-o{env_dir / 'git'}", "-y"], check=True)
        print("  [OK] Git ready")
    else:
        print("  [--] Git (already installed)")
    installed.append("git")

    # ── VS Code ──────────────────────────────────────────────────
    if not skip_vsc:
        print(f"\n>>> VS Code {V['VSCode']} (portable)")
        vsc_exe = env_dir / "vscode" / "Code.exe"
        if force or not vsc_exe.exists():
            zp = setup_dir / "vscode.zip"
            if force or not zp.exists():
                _download(URLS["VSCode"], zp, "VS Code")
            _extract(zp, env_dir / "vscode")
            (env_dir / "vscode" / "data").mkdir(exist_ok=True)
            print("  [OK] VS Code ready")
        else:
            print("  [--] VS Code (already installed)")
        installed.append("vscode")

    # ── Python venv ──────────────────────────────────────────────
    print("\n>>> Python venv")
    venv_py = env_dir / "venv" / "Scripts" / "python.exe"
    if force or not venv_py.exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "virtualenv", "--quiet"], check=True)
        subprocess.run([sys.executable, "-m", "virtualenv", str(env_dir / "venv")], check=True)
        print("  [OK] venv created")
    else:
        print("  [--] venv (already exists)")
    for pkg in ["filelock", "pywinpty"]:
        subprocess.run([str(venv_py), "-m", "pip", "install", pkg, "--quiet"], check=True)
        print(f"  [OK] {pkg} installed")
    installed.append("venv")

    # ── CLI Tools ────────────────────────────────────────────────
    print("\n>>> CLI Tools")
    installed += _install_tools(TOOLS, env_dir, setup_dir, force)

    # ── AI Peer CLIs ─────────────────────────────────────────────
    if not skip_ai:
        print("\n>>> AI Peer CLIs")
        npm_global = env_dir / "nodejs" / "npm-global"
        npm_global.mkdir(exist_ok=True)
        npm_env = os.environ.copy()
        npm_env["NPM_CONFIG_PREFIX"] = str(npm_global)
        npm_env["NPM_CONFIG_CACHE"]  = str(env_dir / "nodejs" / "npm-cache")
        npm_env["PATH"]              = str(env_dir / "nodejs") + os.pathsep + npm_env["PATH"]
        npm_exe = env_dir / "nodejs" / "npm.cmd"
        installed += _install_ai_peers(peers, npm_exe, npm_global, npm_env, force)

    ctx["state"]["installed"] = installed
    print("\n======================================================")
    print("  Provisioner complete.")
    print("======================================================")


if __name__ == "__main__":
    import argparse
    import traceback

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-vscode", action="store_true")
    parser.add_argument("--skip-ai", action="store_true")
    args, _ = parser.parse_known_args()

    # standalone run: build minimal ctx
    _sys = Path(__file__).parent.parent.resolve()
    ctx = {
        "base_dir": _sys.parent,
        "sys_dir":  _sys,
        "paths":    {"state": _sys / "data" / "state", "generated": _sys / "data" / "generated"},
        "args":     sys.argv[1:],
        "state":    {},
    }
    try:
        deploy(ctx)
    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
        sys.exit(1)
