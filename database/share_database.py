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

#Docker Compose exists in 2 forms: "docker compose" (new, part of Docker Desktop)
#or "docker-compose" (old, separate program). We use whichever this computer has.
if subprocess.run([docker, "compose", "version"], env=env, capture_output=True).returncode == 0:
    COMPOSE = [docker, "compose"]
elif shutil.which("docker-compose", path=env["PATH"]):
    COMPOSE = [shutil.which("docker-compose", path=env["PATH"])]
else:
    raise RuntimeError("Docker Compose was not found (neither 'docker compose' nor 'docker-compose').")


def run(command):
    result = subprocess.run(command, cwd=PROJECT, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Docker failed:\n" + result.stderr)
    return result.stdout


#id of the database container ("docker cp" works with both forms of Compose)
container = run(COMPOSE + ["ps", "-q", "db"]).strip()
if not container:
    raise RuntimeError("The database is not running: run database/start_database.py first.")


if ACTION == "export":
    run(COMPOSE + ["exec", "-T", "db", "pg_dump", "-U", "postgres", "-d", "semantic_search",
                   "-Fc", "-f", "/tmp/semantic_search.dump"])
    run([docker, "cp", container + ":/tmp/semantic_search.dump", str(DUMP)])
    print("Exported:", DUMP)
elif ACTION == "import":
    run([docker, "cp", str(DUMP), container + ":/tmp/semantic_search.dump"])
    run(COMPOSE + ["exec", "-T", "db", "pg_restore", "-U", "postgres", "-d", "semantic_search",
                   "--clean", "--if-exists", "--no-owner", "/tmp/semantic_search.dump"])
    print("done, check with database/check_data.py")
