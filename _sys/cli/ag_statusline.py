import sys
import subprocess
import json

def main():
    # Read stdin data passed by Antigravity CLI
    stdin_data = ""
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read()
        except:
            pass

    # Call the new unified bash script for Antigravity
    with open('D:/PortableDev (v2.0)/_sys/cli/ag_stdin.log', 'w') as f:
        f.write(stdin_data)

    # The bash script is at P:\_sys\antigravity\config\statusline-command.sh
    # We pass the stdin_data to it
    try:
        result = subprocess.run(
            ['bash', 'P:/_sys/antigravity/config/statusline-command.sh'],
            input=stdin_data,
            text=True,
            capture_output=True,
            encoding='utf-8',
            check=False
        )
        if result.stdout:
            print(result.stdout, end="")
        else:
            # Fallback if bash script fails
            data = json.loads(stdin_data) if stdin_data else {}
            model = data.get('model', 'Unknown Model')
            print(f"ag:{model} | (unified script err)")
            
    except Exception as e:
        print(f"ag:error | {str(e)[:30]}", end="")

if __name__ == "__main__":
    main()
