import subprocess
import sys
import os

def create_tmp_dir():
    os.makedirs("/tmp/runner", exist_ok=True)
    os.chroot("/tmp/runner")

def main():
    command = sys.argv[3]
    args = sys.argv[4:]
    create_tmp_dir()
    completed_process = subprocess.run([command, *args], capture_output=True)
    print(completed_process.stdout.decode("utf-8").strip())
    sys.stderr.write(completed_process.stderr.decode("utf-8"))
    sys.exit(completed_process.returncode)

if __name__ == "__main__":
    main()
