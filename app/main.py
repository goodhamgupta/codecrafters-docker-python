import subprocess
import sys
import os
import shutil
import tempfile


def create_tmp_dir(command):
    tmp_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp_dir, "/usr/local/bin"), exist_ok=True)
    combined_path = os.path.join(tmp_dir, os.path.basename(command))
    print(combined_path)
    print(os.listdir(combined_path))
    shutil.copy(command, f"{tmp_dir}{command}")
    os.chroot(tmp_dir)
    command = os.path.join(tmp_dir, os.path.basename(command))
    print(command)


def main():
    command = sys.argv[3]
    args = sys.argv[4:]
    create_tmp_dir(command)
    completed_process = subprocess.run([command, *args], capture_output=True)
    print(completed_process.stdout.decode("utf-8").strip())
    sys.stderr.write(completed_process.stderr.decode("utf-8"))
    sys.exit(completed_process.returncode)


if __name__ == "__main__":
    main()
