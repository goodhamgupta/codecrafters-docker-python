import subprocess
import sys
import os
import shutil
import tempfile
import ctypes
import urllib.request
import json


def create_tmp_dir(command):
    """
    Creates a temporary directory and sets it up for executing the given command.

    Args:
        command (str): The command to be executed in the temporary directory.

    Returns:
        None
    """
    tmp_dir = tempfile.TemporaryDirectory()
    os.makedirs(os.path.join(tmp_dir.name, "usr/local/bin"), exist_ok=True)
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    libc.unshare(0x20000000)  # CLONE_NEWNS | CLONE_NEWPID
    shutil.copy(command, f"{tmp_dir.name}{command}")
    os.chroot(tmp_dir.name)

def generate_auth_token(image_name):
    """
    Generates an authentication token for accessing a Docker image.

    Args:
        image_name (str): The name of the Docker image.

    Returns:
        str: The authentication token.
    """
    url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/{image_name}:pull"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read())
    return data['token']

def fetch_image_manifest(auth_token, image_name):
    """
    Fetches the manifest for a Docker image using an authentication token.

    Args:
        auth_token (str): The authentication token.
        image_name (str): The name of the Docker image.

    Returns:
        dict: The manifest of the Docker image.
    """
    manifest_type = "application/vnd.docker.distribution.manifest.v2+json"
    url = f"https://registry-1.docker.io/v2/library/{image_name}/manifests/latest"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {auth_token}")
    req.add_header("Accept", manifest_type)
    with urllib.request.urlopen(req) as response:
        manifest = json.loads(response.read().decode())
    print(manifest)
    return manifest


def main():
    """
    Main function to execute the Docker image command.

    Args:
        None

    Returns:
        None
    """
    command = sys.argv[3]
    args = sys.argv[4:]
    token = generate_auth_token(sys.argv[2])
    manifest = fetch_image_manifest(token, sys.argv[2])
    create_tmp_dir(command)
    completed_process = subprocess.run([command, *args], capture_output=True)
    print(completed_process.stdout.decode("utf-8").strip())
    sys.stderr.write(completed_process.stderr.decode("utf-8"))
    sys.exit(completed_process.returncode)


if __name__ == "__main__":
    main()
