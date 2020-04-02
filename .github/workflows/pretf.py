import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

docker_image = "claranet/direnv-asdf:latest"

top = Path(__file__).parent.parent.parent
home = os.environ["HOME"]
uid = os.getuid()
gid = os.getgid()

# Use a temporary file for the AWS credentials file,
# so it will be automatically deleted afterwards.
with NamedTemporaryFile() as aws_creds_file:
    aws_creds_file.write(os.environ["AWS_CREDENTIALS_FILE"])
    aws_creds_file.flush()

    # Create these directories before Docker runs,
    # otherwise Docker will create them as the root user.
    os.makedirs(f"{top}/.direnv", exist_ok=True)
    os.makedirs(f"{top}/.docker/.direnv", exist_ok=True)
    os.makedirs(f"{top}/.docker/home", exist_ok=True)

    # Build the Docker command and then run it.
    cmd = ["docker", "run", "--rm"]
    volumes = (
        f"{top}:/src",
        f"{top}/.docker/.direnv:/src/.direnv",
        f"{top}/.docker/home:{home}",
        f"{aws_creds_file.name}:/tmp/aws:ro",
        "/etc/passwd:/etc/passwd:ro",
    )
    for volume in volumes:
        cmd.extend(["--volume", volume])
    cmd.extend(["--env", "AWS_SHARED_CREDENTIALS_FILE=/tmp/aws"])
    cmd.extend(["--user", f"{uid}:{gid}"])
    cmd.extend(["--workdir", "/src/vpc/dev"])
    cmd.extend([docker_image])
    cmd.extend(["pretf", "validate"])
    subprocess.run(cmd, check=True)
