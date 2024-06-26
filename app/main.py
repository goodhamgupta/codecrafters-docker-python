import subprocess
import sys
import os
import shutil
import tempfile
import ctypes
import urllib.request
import json
import urllib.error
import time


def create_tmp_dir(command: str) -> str:
    """
    Creates a temporary directory and sets it up for executing the given command.

    Args:
        command (str): The command to be executed in the temporary directory.

    Returns:
        str: The path of the created temporary directory.
    """
    tmp_dir = tempfile.TemporaryDirectory()
    path = f"{tmp_dir.name}{'/'.join(command.split('/')[:-1])}"
    os.makedirs(path, exist_ok=True)
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    libc.unshare(0x20000000)  # CLONE_NEWNS | CLONE_NEWPID
    shutil.copy(command, f"{tmp_dir.name}{command}")
    os.chroot(tmp_dir.name)
    return tmp_dir.name


def generate_auth_token(image_name: str) -> str:
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
    return data["token"]


def fetch_image_manifest(auth_token: str, image_name: str) -> dict:
    """
    Fetches the manifest for a Docker image using an authentication token.

    Args:
        auth_token (str): The authentication token.
        image_name (str): The name of the Docker image.

    Returns:
        dict: The manifest of the Docker image.
    """
    url = f"https://registry-1.docker.io/v2/library/{image_name}/manifests/latest"
    print("MANIFEST URL: ", url)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {auth_token}")
    try:
        with urllib.request.urlopen(req) as response:
            manifest = json.loads(response.read().decode())
        return manifest
    except urllib.error.URLError as e:
        print(f"Error fetching image manifest: {e}. Retrying in 5 seconds...")


def pull_layer(repository: str, digest: str, auth_token: str, save_path: str) -> None:
    """
    Pulls a single layer of a Docker image and saves it to the specified path.

    Args:
        repository (str): The name of the Docker image repository.
        digest (str): The digest of the layer to be pulled.
        auth_token (str): The authentication token for accessing the Docker image.
        save_path (str): The path where the pulled layer will be saved.

    Returns:
        None
    """
    url = f"https://registry-1.docker.io/v2/library/{repository}/blobs/{digest}"
    print("PULL LAYER URL: ", url)
    print("AUTH TOKEN: ", auth_token)
    headers = {
        "Authorization": f"Bearer {auth_token.strip()}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Encoding": "gzip, deflate, br, tar",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                raise Exception(
                    f"Failed to get layer: {response.status} {response.reason}"
                )
            print("RESPONSE STATUS: ", response.status)
            with open(save_path, "wb") as f:
                f.write(response.read())
    except urllib.error.URLError as e:
        print(f"Error fetching layer: {e}")


def pull_layers(
    image_name: str, tmp_dir_name: str, auth_token: str, manifest: dict
) -> None:
    """
    Pulls the layers of a Docker image and saves them to the specified temporary directory.

    Args:
        image_name (str): The name of the Docker image.
        tmp_dir_name (str): The name of the temporary directory where the layers will be saved.
        auth_token (str): The authentication token for accessing the Docker image.
        manifest (dict): The manifest of the Docker image containing the layers information.

    Returns:
        None
    """
    print("Pulling layers... Manifest: ", manifest)
    for layer in manifest["fsLayers"]:
        digest = layer["blobSum"]
        filename = digest.replace(":", "_")  # Replace ':' with '_' for valid filenames
        save_path = os.path.join(tmp_dir_name, filename)
        print(f"Pulling layer {digest}...")
        pull_layer(image_name, digest, auth_token, save_path)
        print(f"Saved to {save_path}")


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
    tmp_dir_name = create_tmp_dir(command)
    pull_layers(sys.argv[2], tmp_dir_name, token, manifest)
    completed_process = subprocess.run([command, *args], capture_output=True)
    print(completed_process.stdout.decode("utf-8").strip())
    sys.stderr.write(completed_process.stderr.decode("utf-8"))
    sys.exit(completed_process.returncode)


if __name__ == "__main__":
    main()
