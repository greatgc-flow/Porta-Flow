"""
manage.py - Unified Sandbox Environment Manager (Python Refactored)
Handles PC registration, drive mapping, registry context menus, and Gemini portability.
"""
import os
import sys
import json
import re
import shutil
import subprocess
import winreg
from pathlib import Path

def get_base_dir():
    # Assume script is in _sys/cli/manage.py or similar
    return Path(__file__).parent.parent.parent.resolve()

def get_registry_key_name(base_dir):
    leaf = base_dir.name
    parent = base_dir.parent.name if base_dir.parent else ""
    drive = base_dir.drive.replace(":", "")
    
    key_base = f"{drive}_{parent}_{leaf}" if parent and len(parent) > 2 else f"{drive}_{leaf}"
    safe_key = re.sub(r'[\/:]', '_', key_base)
    return f"SandboxRun_{safe_key}"

def set_gemini_portability(base_dir):
    gemini_host = Path(os.environ["USERPROFILE"]) / ".gemini"
    gemini_portable = base_dir / "_sys" / "gemini" / "config"
    
    gemini_portable.mkdir(parents=True, exist_ok=True)
    
    if gemini_host.exists():
        # Check if it's already a junction to the right place
        if os.path.islink(gemini_host) or (gemini_host.is_dir() and gemini_host.stat().st_reparse_tag == 0xA0000003): # IO_REPARSE_TAG_MOUNT_POINT
            # Using low-level check or just rmdir and recreate
            pass
        else:
            backup = gemini_host.with_suffix(".host_backup")
            if not backup.exists():
                shutil.move(str(gemini_host), str(backup))
                print(f"  [Info] Backed up host Gemini config to {backup.name}")
            else:
                print("  [Warning] .gemini and .gemini.host_backup both exist. Skipping junction.")
                return

    # Create Junction via CMD
    try:
        subprocess.run(["cmd", "/c", f"mklink /J \"{gemini_host}\" \"{gemini_portable}\""], check=True, capture_output=True)
        print("  [OK] Gemini Portability enabled (Junction created)")
    except subprocess.CalledProcessError as e:
        print(f"  [Fail] Could not create Gemini junction: {e}")

def remove_gemini_portability(base_dir):
    gemini_host = Path(os.environ["USERPROFILE"]) / ".gemini"
    gemini_portable = base_dir / "_sys" / "gemini" / "config"
    
    if gemini_host.exists():
        # Check if it's a junction
        if os.path.islink(gemini_host) or (gemini_host.is_dir() and getattr(gemini_host.stat(), 'st_reparse_tag', 0) == 0xA0000003):
            # Remove junction
            try:
                subprocess.run(["cmd", "/c", f"rmdir \"{gemini_host}\""], check=True)
                print("  [OK] Gemini Portability disabled (Junction removed)")
                
                backup = gemini_host.with_suffix(".host_backup")
                if backup.exists():
                    shutil.move(str(backup), str(gemini_host))
                    print(f"  [Info] Restored host Gemini config from {backup.name}")
            except Exception as e:
                print(f"  [Fail] Error removing junction: {e}")

def global_cleanup(base_dir):
    leaf = base_dir.name
    print(f"  [Info] Performing global cleanup for {leaf}...")
    
    # 1. SUBST cleanup
    try:
        out = subprocess.check_output(["subst"], text=True)
        for line in out.splitlines():
            match = re.match(r'^([A-Z]):.*' + re.escape(str(base_dir)), line, re.IGNORECASE)
            if match:
                drive = match.group(1)
                subprocess.run(["subst", f"{drive}:", "/D"])
                print(f"  [OK] Released SUBST: {drive}:")
    except Exception:
        pass

    # 2. Registry cleanup
    roots = [
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\Background\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\lnkfile\shell")
    ]
    
    target_pattern = rf"SandboxRun_.*({leaf}|_D_D_)"
    
    for hkey, path in roots:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_ALL_ACCESS) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if re.search(target_pattern, subkey_name, re.IGNORECASE):
                            # Recursively delete subkey
                            subprocess.run(["reg", "delete", f"{path}\\{subkey_name}", "/f"], capture_output=True)
                            print(f"  [OK] Removed Orphan Registry: {subkey_name}")
                            # i doesn't increment because we deleted the key
                        else:
                            i += 1
                    except OSError:
                        break
        except Exception:
            pass

def action_register(base_dir):
    print(f"\n{'='*50}")
    print(f" Registering: {base_dir.name}")
    print(f"{'='*50}")

    global_cleanup(base_dir)
    set_gemini_portability(base_dir)

    # 1. Drive Mapping
    assigned_letter = None
    prefer = base_dir.name[0].upper()
    reserved = ['A', 'B', 'C']
    candidates = [prefer] + [chr(x) for x in range(65, 91) if chr(x) not in reserved and chr(x) != prefer]
    
    for letter in candidates:
        drive_path = f"{letter}:\\"
        if not os.path.exists(drive_path):
            try:
                subprocess.run(["subst", f"{letter}:", str(base_dir)], check=True)
                assigned_letter = letter
                print(f"  [OK] Mapped {base_dir} to {letter}:")
                break
            except Exception:
                continue
    
    # 2. Context Menu
    target_key = get_registry_key_name(base_dir)
    menu_label = f"Open in Sandbox: {base_dir.name}" + (f" ({base_dir} -> {assigned_letter}:)" if assigned_letter else f" ({base_dir})")

    # SUBST 경로 사용: 한글/공백 포함 물리 경로는 cmd.exe 코드페이지 문제로 레지스트리 명령 실패
    # SUBST가 성공한 경우 P:\ 같은 단순 경로로 대체
    if assigned_letter:
        cmd_base = Path(f"{assigned_letter}:\\")
    else:
        cmd_base = base_dir
        print("  [Warning] No SUBST assigned — registry command uses physical path (Korean/spaces may fail)")

    launch_script = cmd_base / "_sys" / "cli" / "launch.bat"
    code_path = cmd_base / "_sys" / "env" / "vscode" / "Code.exe"

    reg_paths = [
        (r"Software\Classes\Directory\Background\shell", "%V"),
        (r"Software\Classes\Directory\shell", "%V"),
        (r"Software\Classes\*\shell", "%1"),
        (r"Software\Classes\lnkfile\shell", "%1")
    ]

    for path_base, arg in reg_paths:
        full_path = f"{path_base}\\{target_key}"
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, full_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, menu_label)
            winreg.SetValueEx(key, "HasLUAShield", 0, winreg.REG_SZ, "")
            if os.path.exists(str(code_path)):
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(code_path))

            cmd_key = winreg.CreateKey(key, "command")
            cmd_str = f"cmd.exe /c \"{launch_script}\" \"{arg}\""
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_str)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"  [Warning] Registry error on {full_path}: {e}")
            
    print(f"  [OK] Context Menu registered: {menu_label}")

    # 3. State Saving
    config_path = base_dir / "_sys" / "local.config.bat"
    auto_block = [
        ":: [/auto] Generated by manage.py - do not edit this block",
        f"set \"SUBST_DRIVE_LETTER={assigned_letter or ''}\"",
        "set \"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1\"",
        ":: [/auto]"
    ]
    
    user_lines = []
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        user_lines = [line for line in content.splitlines() if "[/auto]" not in line and "set \"" not in line or "BASE_DIR_PHYS" not in line]
        # Very crude filter, but okay for now
    
    new_config = "\n".join(auto_block) + "\n\n" + "\n".join(user_lines)
    config_path.write_text(new_config.replace("\n", "\r\n"), encoding="utf-8")
    print("  [OK] State saved to local.config.bat")
    print("\n Registration complete!")

def action_unregister(base_dir):
    print(f"\n{'='*50}")
    print(f" Unregistering: {base_dir.name}")
    print(f"{'='*50}")

    global_cleanup(base_dir)
    remove_gemini_portability(base_dir)

    config_path = base_dir / "_sys" / "local.config.bat"
    if config_path.exists():
        # Keep only user lines
        content = config_path.read_text(encoding="utf-8")
        user_lines = [line for line in content.splitlines() if "[/auto]" not in line and "set \"" not in line]
        if any(l.strip() for l in user_lines):
            config_path.write_text("\n".join(user_lines).replace("\n", "\r\n"), encoding="utf-8")
        else:
            config_path.unlink()
        print("  [OK] local.config.bat cleaned")

    print("\n Unregistration complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["Register", "Unregister"])
    parser.add_argument("--base-dir", type=str)
    args = parser.parse_args()

    bdir = Path(args.base_dir).resolve() if args.base_dir else get_base_dir()
    
    if args.action == "Register":
        action_register(bdir)
    else:
        action_unregister(bdir)
