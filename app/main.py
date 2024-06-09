import subprocess
import sys
import os
import shutil
import tempfile
import ctypes
import urllib.request
import json
import time


def create_tmp_dir(command):
    """
    Creates a temporary directory and sets it up for executing the given command.

    Args:
        command (str): The command to be executed in the temporary directory.

    Returns:
        None
    """
    tmp_dir = tempfile.TemporaryDirectory()
    path = f"{tmp_dir.name}{'/'.join(command.split('/')[:-1])}"
    os.makedirs(path, exist_ok=True)
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    libc.unshare(0x20000000)  # CLONE_NEWNS | CLONE_NEWPID
    shutil.copy(command, f"{tmp_dir.name}{command}")
    os.chroot(tmp_dir.name)
    return tmp_dir.name

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

def pull_layer(repository, digest, auth_token, save_path):
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
    url = f'https://registry-1.docker.io/v2/library/{repository}/blobs/{digest}'
    print("PULL LAYER URL: ", url)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {auth_token}")
    print(req.headers)
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            with urllib.request.urlopen(req, timeout=600) as response:
                if response.status != 200:
                    raise Exception(f'Failed to get layer: {response.status} {response.reason}')

                print("RESPONSE STATUS: ", response.status)
                with open(save_path, 'wb') as f:
                    f.write(response.read())
                return
        except urllib.error.URLError as e:
            retry_count += 1
            print(f"Error occurred while pulling layer: {e}. Retrying ({retry_count}/{max_retries})...")
            time.sleep(1)  # Add a small delay before retrying
        except Exception as e:
            raise Exception(f"Unexpected error occurred while pulling layer: {e}")

    raise Exception(f"Failed to pull layer after {max_retries} retries.")
def pull_layers(image_name, tmp_dir_name, auth_token, manifest):
    """
    Pulls the layers of a Docker image and saves them to the specified temporary directory.

    Args:
        image_name (str): The name of the Docker image.
        tmp_dir_name (str): The name of the temporary directory where the layers will be saved.
        manifest (dict): The manifest of the Docker image containing the layers information.

    Returns:
        None
    """
    print("Pulling layers... Manifest: ", manifest)
    for layer in manifest['layers']:
        print(layer)
        digest = layer['digest']
        filename = digest.replace(':', '_')  # Replace ':' with '_' for valid filenames
        save_path = os.path.join(tmp_dir_name, filename)
        print(f'Pulling layer {digest}...')
        pull_layer(image_name, digest, auth_token, save_path)
        print(f'Saved to {save_path}')

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
