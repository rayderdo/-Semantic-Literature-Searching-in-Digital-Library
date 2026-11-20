"""Share the database with the team: "export" = make the dump file, "import" = load it."""

ACTION = "export"

import os
import shutil
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DUMP = PROJECT / "semantic_search.dump"



DOCKER_FOLDERS = [
    "/usr/local/bin", "/opt/homebrew/bin", str(Path.home() / ".docker" / "bin"),
    "/Applications/Docker.app/Contents/Resources/bin", "/usr/bin",
    r"C:\Program Files\Docker\Docker\resources\bin",
]


env = os.environ.copy()
env["PATH"] = os.pathsep.join([env.get("PATH", "")] + DOCKER_FOLDERS)
docker = shutil.which("docker", path=env["PATH"])
if docker is None:
    raise RuntimeError("Docker not found")


def compose(*args):
    result = subprocess.run([docker, "compose", *args], cwd=PROJECT, env=env,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Docker failed:\n" + result.stderr)


if ACTION == "export":
    compose("exec", "-T", "db", "pg_dump", "-U", "postgres", "-d", "semantic_search",
            "-Fc", "-f", "/tmp/semantic_search.dump") 
    compose("cp", "db:/tmp/semantic_search.dump", str(DUMP)) 
    print("Exported:", DUMP)
elif ACTION == "import":
    compose("cp", str(DUMP), "db:/tmp/semantic_search.dump") 
    compose("exec", "-T", "db", "pg_restore", "-U", "postgres", "-d", "semantic_search",
            "--clean", "--if-exists", "--no-owner", "/tmp/semantic_search.dump") 
    print("done, check with database/check_data.py")