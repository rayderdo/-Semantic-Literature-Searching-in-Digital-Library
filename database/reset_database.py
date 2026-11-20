"""DELETE the database and all its data (then run start_database.py to recreate it)."""

import os
import shutil
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent



DOCKER_FOLDERS = [
    "/usr/local/bin", "/opt/homebrew/bin", str(Path.home() / ".docker" / "bin"),
    "/Applications/Docker.app/Contents/Resources/bin", "/usr/bin",
    r"C:\Program Files\Docker\Docker\resources\bin",
]


env = os.environ.copy()
env["PATH"] = os.pathsep.join([env.get("PATH", "")] + DOCKER_FOLDERS)
docker = shutil.which("docker", path=env["PATH"])

if docker is None:
    raise RuntimeError("Docker was not found")


if input("This DELETES the whole database. Type yes to continue: ").strip().lower() == "yes":
    result = subprocess.run([docker, "compose", "down", "-v"], cwd=PROJECT, env=env,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Docker couldnt delete the database:\n" + result.stderr)
    print("Database deleted. Run start_database.py to continue")
else:
    print("Cancelled.")