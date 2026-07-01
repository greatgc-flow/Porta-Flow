import sys
import subprocess
import json
from pathlib import Path


CLI_DIR = Path(__file__).resolve().parent
SYS_DIR = CLI_DIR.parent
STATUSLINE_SCRIPT = SYS_DIR / "antigravity" / "config" / "statusline-command.sh"
STDIN_LOG = CLI_DIR / "ag_stdin.log"


def main():
    # Read stdin data passed by Antigravity CLI
    stdin_data = ""
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read()
        except Exception:
            pass

    # Call the unified bash script for Antigravity.
    with STDIN_LOG.open("w", encoding="utf-8") as f:
        f.write(stdin_data)

    # Pass stdin_data to the portable statusline adapter.
    try:
        result = subprocess.run(
            ["bash", STATUSLINE_SCRIPT.as_posix()],
            input=stdin_data,
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        if result.stdout:
            print(result.stdout, end="")
        else:
            # Fallback if bash script fails
            data = json.loads(stdin_data) if stdin_data else {}
            model = data.get("model", "Unknown Model")
            print(f"ag:{model} | (unified script err)")
    except Exception as e:
        print(f"ag:error | {str(e)[:30]}", end="")


if __name__ == "__main__":
    main()
