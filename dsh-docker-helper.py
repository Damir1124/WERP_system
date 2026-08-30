import sys
import subprocess
import json
import re

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), -1

def show_ps():
    print("=== MONITORING DOCKER CONTAINER STATUS ===")
    stdout, stderr, code = run_command("docker compose ps")
    if code != 0:
        stdout, stderr, code = run_command("docker ps")
    
    if code == 0:
        print(stdout)
    else:
        print(f"Error checking status: {stderr}", file=sys.stderr)

def scan_tracebacks():
    print("=== SCANNING FOR RECENT PY-TRACEBACKS ===")
    stdout, stderr, code = run_command("docker compose logs --tail=200")
    if code != 0:
        print(f"Error reading logs: {stderr}", file=sys.stderr)
        return

    lines = stdout.split('\n')
    tracebacks = []
    current_tb = []
    recording = False

    for line in lines:
        if "Traceback (most recent call last)" in line:
            recording = True
            current_tb = [line]
        elif recording:
            current_tb.append(line)
            if len(line) > 0 and not line.startswith(' ') and not line.startswith('\t') and not re.match(r'^\s*File\s+"', line):
                if any(x in line for x in ["Error", "Exception", "Fail", "Critical"]):
                    recording = False
                    tracebacks.append("\n".join(current_tb))
                    current_tb = []

    if current_tb:
        tracebacks.append("\n".join(current_tb))

    if not tracebacks:
        print("No active Python traceback logs detected in the last 200 lines.")
    else:
        print(f"Detected {len(tracebacks)} traceback(s):")
        for i, tb in enumerate(tracebacks, 1):
            print(f"\n--- TRACEBACK #{i} ---")
            print(tb)

def exec_in_container(container, cmd):
    print(f"=== RUNNING COMMAND IN '{container}' ===")
    full_cmd = f"docker compose exec {container} {cmd}"
    stdout, stderr, code = run_command(full_cmd)
    if code == 0:
        print(stdout)
    else:
        print(f"Command failed (Exit code {code}):\n{stderr}", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print("Usage: python dsh-docker-helper.py [ps | tracebacks | exec <service> <command>]")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "ps":
        show_ps()
    elif action in ["tracebacks", "traceback", "logs"]:
        scan_tracebacks()
    elif action == "exec":
        if len(sys.argv) < 4:
            print("Usage: python dsh-docker-helper.py exec <service_name> <command>")
            sys.exit(1)
        service = sys.argv[2]
        cmd = " ".join(sys.argv[3:])
        exec_in_container(service, cmd)
    else:
        print(f"Unknown command: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
