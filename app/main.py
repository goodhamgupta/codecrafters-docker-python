import subprocess
import sys
import os
import shutil

def create_tmp_dir():
    print("Old root: ", os.getcwd())
    os.mkdir("/tmp/runner")
    shutil.copy("/usr/local/bin/docker-explorer", "/tmp/runner/docker-explorer")
    os.chroot("/tmp/runner")
    print("New root: ", os.getcwd())


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
