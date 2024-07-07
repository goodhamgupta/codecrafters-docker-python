import subprocess
import sys
import os
import shutil
import tempfile
import ctypes
import urllib.request
import json
import tarfile


def create_tmp_dir(command: str) -> str:
    tmp_dir = tempfile.mkdtemp()
    path = f"{tmp_dir}{'/'.join(command.split('/')[:-1])}"
    os.makedirs(path, exist_ok=True)
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    libc.unshare(0x20000000)  # CLONE_NEWNS | CLONE_NEWPID
    shutil.copy(command, f"{tmp_dir}{command}")
    os.chroot(tmp_dir)
    return tmp_dir


def get_token(image_name: str) -> str:
    url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/{image_name}:pull"
    res = urllib.request.urlopen(url)
    res_json = json.loads(res.read().decode())
    return res_json["token"]


def get_manifest(token: str, image_name: str) -> dict:
    manifest_url = (
        f"https://registry.hub.docker.com/v2/library/{image_name}/manifests/latest"
    )
    request = urllib.request.Request(
        manifest_url,
        headers={
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
            "Authorization": f"Bearer {token}",
        },
    )
    res = urllib.request.urlopen(request)
    res_json = json.loads(res.read().decode())
    return res_json


def pull_layers(image: str, token: str, layers: list) -> str:
    dir_path = tempfile.mkdtemp()
    for layer in layers:
        url = f"https://registry.hub.docker.com/v2/library/{image}/blobs/{layer['digest']}"
        sys.stderr.write(url)
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.docker.distribution.manifest.v2+json",
                "Authorization": f"Bearer {token}",
            },
        )
        res = urllib.request.urlopen(request)
        tmp_file = os.path.join(dir_path, "manifest.tar")
        with open(tmp_file, "wb") as f:
            shutil.copyfileobj(res, f)
        with tarfile.open(tmp_file) as tar:
            tar.extractall(dir_path)
    os.remove(tmp_file)
    return dir_path


def run_command(command: str, args: list, dir_path: str) -> None:
    os.chroot(dir_path)
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    libc.unshare(0x20000000)
    parent_process = subprocess.Popen(
        [command, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    stdout, stderr = parent_process.communicate()
    if stderr:
        print(stderr.decode("utf-8"), file=sys.stderr, end="")
    if stdout:
        print(stdout.decode("utf-8"), end="")
    sys.exit(parent_process.returncode)


def main() -> int:
    image = sys.argv[2]
    command = sys.argv[3]
    args = sys.argv[4:]
    token = get_token(image_name=image)
    manifest = get_manifest(image_name=image, token=token)
    dir_path = pull_layers(image, token, manifest["layers"])
    run_command(command, args, dir_path)


if __name__ == "__main__":
    main()
