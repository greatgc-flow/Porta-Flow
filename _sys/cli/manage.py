import os
import sys
import json
import re
import shutil
import subprocess
import winreg
import traceback
from pathlib import Path

# Add sys path to allow importing core modules
sys_dir = Path(__file__).parent.parent.resolve()
if str(sys_dir) not in sys.path:
    sys.path.insert(0, str(sys_dir))

from core.config import config

def get_base_dir():
    return config.get_base_dir()

def get_registry_key_name(base_dir):
    leaf = base_dir.name
    parent = base_dir.parent.name if base_dir.parent else ""
    drive = base_dir.drive.replace(":", "")

    key_base = f"{drive}_{parent}_{leaf}" if parent and len(parent) > 2 else f"{drive}_{leaf}"
    safe_key = re.sub(r'[^A-Za-z0-9]', '_', key_base)
    safe_key = re.sub(r'_+', '_', safe_key).strip('_')
    return f"SandboxRun_{safe_key}"


def get_relay_path(ascii_key: str) -> Path:
    localappdata = Path(os.environ.get("LOCALAPPDATA", ""))
    return localappdata / f"{ascii_key}.bat"


def write_relay_bat(base_dir: Path, ascii_key: str) -> Path:
    relay_path = get_relay_path(ascii_key)
    # The relay simply calls the newly refactored launcher with the target
    content = (
        "@echo off\r\n"
        f"set \"SANDBOX_ROOT={base_dir}\"\r\n"
        "call \"%SANDBOX_ROOT%\\start.bat\" \"%~1\"\r\n"
    )
    relay_path.write_bytes(content.encode("mbcs"))
    return relay_path


def delete_relay_bat(ascii_key: str) -> None:
    relay_path = get_relay_path(ascii_key)
    if relay_path.exists():
        relay_path.unlink()
        print(f"  [OK] Relay removed: {relay_path.name}")

def get_subst_mappings():
    mappings = {}
    try:
        out = subprocess.check_output(["subst"], text=True, encoding='oem')
        for line in out.splitlines():
            match = re.match(r'^([A-Z]):\\: => (.*)$', line, re.IGNORECASE)
            if match:
                mappings[match.group(1).upper()] = Path(match.group(2).strip())
    except Exception:
        pass
    return mappings

def set_gemini_portability(base_dir):
    gemini_host = Path(os.environ["USERPROFILE"]) / ".gemini"
    gemini_portable = base_dir / "_sys" / "gemini" / "config"
    
    gemini_portable.mkdir(parents=True, exist_ok=True)
    
    host_exists = False
    is_junction = False
    try:
        st = gemini_host.lstat()
        host_exists = True
        if os.path.islink(gemini_host) or getattr(st, 'st_reparse_tag', 0) == 0xA0000003:
            is_junction = True
    except FileNotFoundError:
        pass
    except Exception:
        pass

    if host_exists:
        if is_junction:
            try:
                gemini_host.unlink()
                print(f"  [Info] Removed existing junction: {gemini_host}")
            except Exception as e:
                print(f"  [Warning] Could not remove existing junction: {e}")
                return
        else:
            backup = gemini_host.with_suffix(".host_backup")
            if not backup.exists():
                try:
                    shutil.move(str(gemini_host), str(backup))
                    print(f"  [Info] Backed up host Gemini config to {backup.name}")
                except Exception as e:
                    print(f"  [Warning] Could not backup host Gemini config: {e}")
                    return
            else:
                print("  [Warning] .gemini and .gemini.host_backup both exist. Skipping junction to prevent data loss.")
                return

    try:
        subprocess.run(["cmd", "/c", f"mklink /J \"{gemini_host}\" \"{gemini_portable}\""], check=True, capture_output=True)
        print("  [OK] Gemini Portability enabled (Junction created)")
    except subprocess.CalledProcessError as e:
        print(f"  [Fail] Could not create Gemini junction: {e}")

def remove_gemini_portability(base_dir):
    gemini_host = Path(os.environ["USERPROFILE"]) / ".gemini"
    gemini_portable = base_dir / "_sys" / "gemini" / "config"
    
    host_exists = False
    is_junction = False
    try:
        st = gemini_host.lstat()
        host_exists = True
        if os.path.islink(gemini_host) or getattr(st, 'st_reparse_tag', 0) == 0xA0000003:
            is_junction = True
    except FileNotFoundError:
        pass
    except Exception:
        pass

    if host_exists:
        if is_junction:
            try:
                subprocess.run(["cmd", "/c", f"rmdir \"{gemini_host}\""], check=True)
                print("  [OK] Gemini Portability disabled (Junction removed)")
                
                backup = gemini_host.with_suffix(".host_backup")
                if backup.exists():
                    shutil.move(str(backup), str(gemini_host))
                    print(f"  [Info] Restored host Gemini config from {backup.name}")
            except Exception as e:
                print(f"  [Fail] Error removing junction: {e}")

def update_claude_settings(base_dir, drive_letter):
    if not drive_letter:
        return
    settings_path = base_dir / ".claude" / "settings.local.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    
    patterns = [
        f"Bash(cmd /c \"{drive_letter}:\\_sys\\cli\\msg.bat\" *)",
        f"PowerShell(cmd /c \"{drive_letter}:\\_sys\\cli\\msg.bat\" *)",
        f"PowerShell(cmd /c \"{drive_letter}:\\_sys\\cli\\msg.bat\" ask *)",
        f"PowerShell(Get-ChildItem \"{drive_letter}:\\_sys\\ *)",
        f"PowerShell(Get-Content \"{drive_letter}:\\ *)"
    ]
    
    c_config = {"permissions": {"allow": patterns}}
    settings_path.write_text(json.dumps(c_config, indent=4), encoding="utf-8")
    print(f"  [OK] .claude/settings.local.json updated (Drive {drive_letter}:)")

def global_cleanup(base_dir):
    leaf = base_dir.name
    print(f"  [Info] Performing global cleanup for {leaf}...")
    
    try:
        out = subprocess.check_output(["subst"], text=True, encoding='oem')
        for line in out.splitlines():
            match = re.match(r'^([A-Z]):.*' + re.escape(str(base_dir)), line, re.IGNORECASE)
            if match:
                drive = match.group(1)
                subprocess.run(["subst", f"{drive}:", "/D"])
                print(f"  [OK] Released SUBST: {drive}:")
    except Exception:
        pass

    roots = [
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\Background\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell"),
        (winreg.HKEY_CURRENT_USER, r"Software\Classes\lnkfile\shell")
    ]
    
    current_key_name = get_registry_key_name(base_dir)
    
    for hkey, path in roots:
        to_delete = []
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if subkey_name.startswith("SandboxRun_"):
                            is_target = (subkey_name == current_key_name)
                            
                            is_orphan = False
                            if not is_target:
                                ascii_key = subkey_name
                                relay_path = get_relay_path(ascii_key)
                                if not relay_path.exists():
                                    is_orphan = True
                                else:
                                    content = relay_path.read_text(encoding="mbcs", errors="ignore")
                                    match = re.search(r'set "SANDBOX_ROOT=(.*?)"', content, re.IGNORECASE)
                                    if match:
                                        sandbox_root = Path(match.group(1))
                                        if not sandbox_root.exists():
                                            is_orphan = True
                                    else:
                                        is_orphan = True
                                        
                            if is_target or is_orphan:
                                to_delete.append(subkey_name)
                        i += 1
                    except OSError:
                        break
        except Exception:
            continue

        for subkey_name in to_delete:
            full_reg_path = f"HKCU\\{path}\\{subkey_name}"
            res = subprocess.run(["reg", "delete", full_reg_path, "/f"], capture_output=True)
            if res.returncode == 0:
                print(f"  [OK] Removed Registry: {subkey_name}")
                delete_relay_bat(subkey_name)
            else:
                print(f"  [Warning] Failed to delete registry key: {subkey_name}")

def action_register(base_dir):
    print(f"\n{'='*50}")
    print(f" Registering: {base_dir.name}")
    print(f"{'='*50}")

    global_cleanup(base_dir)
    set_gemini_portability(base_dir)

    assigned_letter = None
    subst_map = get_subst_mappings()
    
    for letter, path in subst_map.items():
        if path.resolve() == base_dir.resolve():
            assigned_letter = letter
            print(f"  [OK] Reusing existing mapping: {letter}: -> {base_dir}")
            break
            
    if not assigned_letter:
        prefer = base_dir.name[0].upper()
        if not ('A' <= prefer <= 'Z'):
            prefer = 'P'
        reserved = ['A', 'B', 'C']
        candidates = [prefer] + [chr(x) for x in range(65, 91) if chr(x) not in reserved and chr(x) != prefer]
        
        for letter in candidates:
            if letter in subst_map:
                mapped_path = subst_map[letter]
                if not mapped_path.exists():
                    print(f"  [Info] Drive {letter}: points to dead path. Releasing.")
                    subprocess.run(["subst", f"{letter}:", "/D"], capture_output=True)
                else:
                    continue

            drive_path = f"{letter}:\\"
            if not os.path.exists(drive_path):
                try:
                    subprocess.run(["subst", f"{letter}:", str(base_dir)], check=True)
                    assigned_letter = letter
                    print(f"  [OK] Mapped {base_dir} to {letter}:")
                    break
                except Exception:
                    continue
    
    if assigned_letter:
        update_claude_settings(base_dir, assigned_letter)

    target_key = get_registry_key_name(base_dir)
    menu_label = f"Open in Sandbox: {base_dir.name}" + (f" ({base_dir} -> {assigned_letter}:)" if assigned_letter else f" ({base_dir})")

    code_path = base_dir / "_sys" / "env" / "vscode" / "Code.exe"

    reg_paths = [
        (r"Software\Classes\Directory\Background\shell", "%V"),
        (r"Software\Classes\Directory\shell", "%V"),
        (r"Software\Classes\*\shell", "%1"),
        (r"Software\Classes\lnkfile\shell", "%1")
    ]

    relay_path = write_relay_bat(base_dir, target_key)
    print(f"  [OK] Relay created: {relay_path}")

    for path_base, arg in reg_paths:
        full_path = f"{path_base}\\{target_key}"
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, full_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, menu_label)
            winreg.SetValueEx(key, "HasLUAShield", 0, winreg.REG_SZ, "")
            if os.path.exists(str(code_path)):
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(code_path))

            cmd_key = winreg.CreateKey(key, "command")
            cmd_str = f'cmd.exe /c ""{relay_path}" "{arg}.""'
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_str)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"  [Warning] Registry error on {full_path}: {e}")
            
    print(f"  [OK] Context Menu registered: {menu_label}")

    # State Saving via ConfigManager
    config.set("SUBST_DRIVE_LETTER", assigned_letter)
    print("  [OK] State saved to config.json")
    
    # Optional cleanup of legacy file
    legacy_config = base_dir / "_sys" / "local.config.bat"
    if legacy_config.exists():
        legacy_config.unlink()
        print("  [OK] Legacy local.config.bat removed.")

    print("\n Registration complete!")

def action_unregister(base_dir):
    print(f"\n{'='*50}")
    print(f" Unregistering: {base_dir.name}")
    print(f"{'='*50}")

    delete_relay_bat(get_registry_key_name(base_dir))
    global_cleanup(base_dir)
    remove_gemini_portability(base_dir)

    settings_path = base_dir / ".claude" / "settings.local.json"
    if settings_path.exists():
        settings_path.unlink()
        print("  [OK] .claude/settings.local.json removed")

    # Clear SUBST mapping from config
    config.set("SUBST_DRIVE_LETTER", None)
    print("  [OK] config.json cleared of drive mapping")

    print("\n Unregistration complete.")

def action_cleanup(base_dir):
    # Delegate to cleanup.py
    cleanup_py = base_dir / "_sys" / "cli" / "cleanup.py"
    if cleanup_py.exists():
        subprocess.run([sys.executable, str(cleanup_py)] + sys.argv[2:])
    else:
        print("[Error] cleanup.py not found.")
        sys.exit(1)

def main():
    try:
        import argparse
        parser = argparse.ArgumentParser()
        # Accept 'register', 'unregister', 'cleanup' (case-insensitive due to batch %~n0)
        parser.add_argument("action", type=str)
        parser.add_argument("--base-dir", type=str, default="")
        # Allow trailing unknown args for cleanup
        args, unknown = parser.parse_known_args()

        action = args.action.lower()
        bdir = Path(args.base_dir).resolve() if args.base_dir else get_base_dir()
        
        if action == "register":
            action_register(bdir)
        elif action == "unregister":
            action_unregister(bdir)
        elif action == "cleanup":
            action_cleanup(bdir)
        else:
            print(f"[Error] Unknown action: {action}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[FATAL ERROR] An unexpected error occurred:")
        print(f"  {e}\n")
        print("--- Stack Trace ---")
        traceback.print_exc()
        print("-------------------")
        print("\nPress any key to exit...")
        os.system("pause >nul")
        sys.exit(1)

if __name__ == "__main__":
    main()
