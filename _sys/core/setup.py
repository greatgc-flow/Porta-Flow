"""
setup.py - Portable Dev Environment Bootstrapper (Python Refactored)
Handles downloading and installing all components: Node.js, FFmpeg, Git, VS Code, etc.
"""
import os
import sys
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

# --- Versions ---
V = {
    "Python": "3.13.4",
    "NodeJS": "22.22.3",
    "Git": "2.49.0",
    "VSCode": "1.100.2",
    "Pwsh": "7.6.2"
}

URLS = {
    "NodeJS": f"https://nodejs.org/dist/v{V['NodeJS']}/node-v{V['NodeJS']}-win-x64.zip",
    "Git": f"https://github.com/git-for-windows/git/releases/download/v{V['Git']}.windows.1/PortableGit-{V['Git']}-64-bit.7z.exe",
    "FFmpeg": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip",
    "VSCode": f"https://update.code.visualstudio.com/{V['VSCode']}/win32-x64-archive/stable",
    "Pwsh": f"https://github.com/PowerShell/PowerShell/releases/download/v{V['Pwsh']}/PowerShell-{V['Pwsh']}-win-x64.zip"
}

def get_paths():
    sys_dir = Path(__file__).parent.parent.resolve()
    base_dir = sys_dir.parent
    return {
        "base": base_dir,
        "sys": sys_dir,
        "env": sys_dir / "env",
        "tools": sys_dir / "tools",
        "data": sys_dir / "data",
        "setup": sys_dir / "data" / "setup-files",
        "claude": sys_dir / "claude"
    }

def download_file(url, dest, label):
    print(f"  [i] Downloading {label}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  [OK] Downloaded: {dest.name} ({size_mb:.1f} MB)")

def extract_zip(zip_path, dest_dir):
    print(f"  [i] Extracting {zip_path.name}...")
    # Use built-in shutil or tar CLI
    try:
        shutil.unpack_archive(str(zip_path), str(dest_dir))
        print(f"  [OK] Extracted to {dest_dir.name}")
    except Exception as e:
        print(f"  [Fail] Extraction failed: {e}")
        # Fallback to tar CLI if available
        subprocess.run(["tar", "-xf", str(zip_path), "-C", str(dest_dir)], check=True)

def run_setup(force=False, skip_vscode=False, skip_claude=False):
    paths = get_paths()
    print(f"\n>>> Starting Setup (Force={force})")

    # 1. Folder Structure
    print("\n>>> Folder structure")
    dirs = [
        paths["env"], paths["env"] / "python", paths["env"] / "nodejs",
        paths["env"] / "ffmpeg", paths["env"] / "git", paths["env"] / "vscode",
        paths["env"] / "venv", paths["env"] / "pwsh",
        paths["tools"], paths["tools"] / "apps",
        paths["claude"] / "config", paths["claude"] / "agent",
        paths["data"] / "logs", paths["data"] / "temp", paths["setup"],
        paths["base"] / "workspace"
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("  [OK] Folder structure ready")

    # 2. NodeJS
    print(f"\n>>> Node.js {V['NodeJS']}")
    node_exe = paths["env"] / "nodejs" / "node.exe"
    if force or not node_exe.exists():
        zip_path = paths["setup"] / "nodejs.zip"
        if force or not zip_path.exists():
            download_file(URLS["NodeJS"], zip_path, "Node.js")
        
        tmp_dir = paths["setup"] / "_nodejs_tmp"
        tmp_dir.mkdir(exist_ok=True)
        extract_zip(zip_path, tmp_dir)
        
        # Move nested folder content
        extracted = next(tmp_dir.iterdir())
        if extracted.is_dir():
            for item in extracted.iterdir():
                dest = paths["env"] / "nodejs" / item.name
                if dest.exists():
                    if dest.is_dir(): shutil.rmtree(dest)
                    else: dest.unlink()
                shutil.move(str(item), str(paths["env"] / "nodejs"))
        shutil.rmtree(tmp_dir)
        print("  [OK] Node.js ready")
    else:
        print("  [--] Node.js (already installed)")

    # 3. Git
    print(f"\n>>> Git {V['Git']} (portable)")
    git_exe = paths["env"] / "git" / "cmd" / "git.exe"
    if force or not git_exe.exists():
        exe_path = paths["setup"] / "PortableGit.7z.exe"
        if force or not exe_path.exists():
            download_file(URLS["Git"], exe_path, "Git Portable")
        
        print("  [i] Extracting Git (self-extracting archive)...")
        # Git portable is a self-extracting 7z archive
        subprocess.run([str(exe_path), f"-o{paths['env'] / 'git'}", "-y"], check=True)
        print("  [OK] Git ready")
    else:
        print("  [--] Git (already installed)")

    # 4. VS Code
    if not skip_vscode:
        print(f"\n>>> VS Code {V['VSCode']} (portable)")
        vsc_exe = paths["env"] / "vscode" / "Code.exe"
        if force or not vsc_exe.exists():
            zip_path = paths["setup"] / "vscode.zip"
            if force or not zip_path.exists():
                download_file(URLS["VSCode"], zip_path, "VS Code")
            extract_zip(zip_path, paths["env"] / "vscode")
            (paths["env"] / "vscode" / "data").mkdir(exist_ok=True)
            print("  [OK] VS Code ready")
    
    # 5. Python venv
    print("\n>>> Python virtual environment")
    venv_dir = paths["env"] / "venv"
    venv_py = venv_dir / "Scripts" / "python.exe"
    if force or not venv_py.exists():
        print("  [i] Creating venv...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("  [OK] venv created")
    
    # 6. Install filelock
    print("  [i] Installing filelock...")
    subprocess.run([str(venv_py), "-m", "pip", "install", "filelock", "--quiet"], check=True)
    print("  [OK] filelock installed")

    # 7. Claude Code CLI
    if not skip_claude:
        print("\n>>> Claude Code CLI")
        npm_global = paths["env"] / "nodejs" / "npm-global"
        npm_global.mkdir(exist_ok=True)
        
        env = os.environ.copy()
        env["NPM_CONFIG_PREFIX"] = str(npm_global)
        env["NPM_CONFIG_CACHE"] = str(paths["env"] / "nodejs" / "npm-cache")
        env["PATH"] = str(paths["env"] / "nodejs") + os.pathsep + env["PATH"]
        
        claude_cmd = npm_global / "claude.cmd"
        if force or not claude_cmd.exists():
            print("  [i] npm install -g @anthropic-ai/claude-code ...")
            npm_exe = paths["env"] / "nodejs" / "npm.cmd"
            subprocess.run([str(npm_exe), "install", "-g", "@anthropic-ai/claude-code"], env=env, check=True)
            print("  [OK] Claude Code CLI ready")

    # 8. Finalize with Registry
    print("\n>>> Finalizing with Registry context menu")
    manage_py = paths["sys"] / "cli" / "manage.py"
    subprocess.run([sys.executable, str(manage_py), "Register"], check=True)

    print("\n======================================================")
    print("  Setup complete! All components installed.")
    print("======================================================")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-vscode", action="store_true")
    parser.add_argument("--skip-claude", action="store_true")
    args = parser.parse_args()
    
    run_setup(force=args.force, skip_vscode=args.skip_vscode, skip_claude=args.skip_claude)
