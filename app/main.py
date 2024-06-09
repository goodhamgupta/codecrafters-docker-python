import subprocess
import sys
import os
import shutil
import tempfile
import ctypes


def create_tmp_dir(command):
    tmp_dir = tempfile.TemporaryDirectory()
    os.makedirs(os.path.join(tmp_dir.name, "usr/local/bin"), exist_ok=True)
    shutil.copy(command, f"{tmp_dir.name}{command}")
    os.chroot(tmp_dir.name)


def main():
    command = sys.argv[3]
    args = sys.argv[4:]
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    libc.unshare(0x200000)
    create_tmp_dir(command)
    completed_process = subprocess.run([command, *args], capture_output=True)
    print(completed_process.stdout.decode("utf-8").strip())
    sys.stderr.write(completed_process.stderr.decode("utf-8"))
    sys.exit(completed_process.returncode)


if __name__ == "__main__":
    main()
