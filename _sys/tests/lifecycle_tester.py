import sys
import os
import subprocess
import winreg
import re
from pathlib import Path

def log(msg):
    print(msg, flush=True)

def check_registry(leaf):
    pattern = rf"SandboxRun_.*({leaf}|_D_D_)"
    roots = [
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\Background\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\lnkfile\shell")
    ]
    for hkey, path in roots:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, i)
                        if re.search(pattern, sub, re.IGNORECASE):
                            return True
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass
    return False

def get_subst_drive(target_path):
    try:
        out = subprocess.check_output(["subst"], text=True)
        for line in out.splitlines():
            if str(target_path).lower() in line.lower():
                match = re.match(r'^([A-Z]):', line, re.IGNORECASE)
                if match: return match.group(1)
    except:
        pass
    return None

def main(target_dir):
    tgt = Path(target_dir).resolve()
    leaf = tgt.name
    manage_bat = tgt / "_sys" / "cli" / "manage.bat"
    install_bat = tgt / "install.bat"

    log(f"=== Starting MECE Lifecycle Test on {tgt} ===")

    log("\n=== 1. Test Register ===")
    subprocess.run([str(manage_bat), "Register", "--base-dir", str(tgt)], cwd=tgt, check=True)
    if not get_subst_drive(tgt): raise AssertionError("SUBST drive not created!")
    if not check_registry(leaf): raise AssertionError("Registry NOT found!")
    if not (tgt / "_sys" / "local.config.bat").exists(): raise AssertionError("local.config.bat not generated!")
    log("Register passed.")

    log("\n=== 2. Test Unregister ===")
    subprocess.run([str(manage_bat), "Unregister", "--base-dir", str(tgt)], cwd=tgt, check=True)
    if get_subst_drive(tgt): raise AssertionError("SUBST drive still exists!")
    if check_registry(leaf): raise AssertionError("Registry still exists!")
    log("Unregister passed.")

    log("\n=== 3. Test ZeroBase Cleanup (Tier 4) ===")
    cleanup_py = tgt / "_sys" / "cli" / "cleanup.py"
    py_exe = tgt / "_sys" / "env" / "python" / "python.exe"
    subprocess.run([str(py_exe), str(cleanup_py), "--tier", "4", "--all"], cwd=tgt, check=True)
    if (tgt / "_sys" / "env").exists(): raise AssertionError("_sys/env not deleted!")
    if (tgt / "workspace").exists(): raise AssertionError("workspace not deleted!")
    if list(tgt.glob("*.md")): raise AssertionError("Root markdown files not deleted!")
    log("ZeroBase Cleanup passed.")

    log("\n=== 4. Test Install (Setup) ===")
    # Using --skip-vscode and --skip-claude to speed up testing in WSB
    subprocess.run([str(install_bat), "--skip-vscode", "--skip-claude"], cwd=tgt, check=True)
    if not (tgt / "_sys" / "env" / "python" / "python.exe").exists(): raise AssertionError("Python not installed!")
    if not (tgt / "_sys" / "env" / "venv" / "Scripts" / "python.exe").exists(): raise AssertionError("venv not created!")
    if not (tgt / "_sys" / "env" / "nodejs" / "node.exe").exists(): raise AssertionError("NodeJS not installed!")
    log("Install passed.")

    log("\nALL LIFECYCLE TESTS PASSED.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lifecycle_tester.py <target_dir>")
        sys.exit(1)
    main(sys.argv[1])
