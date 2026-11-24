"""Start the project database!
Docker Desktop must be open first.
What is done here =
- creates personal .env from .env.example
- docker compuse up -d : starts PostgreSQL
- prints valuable info of the database for the embedding : pgvector extensioin available or not, tables created (to verify if it is consistent)
"""


#imports

import os
import shutil
import subprocess
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

#absolute paths for resilient work = does not care about the parents of the files (ignore)
PROJECT = Path(__file__).resolve().parent.parent

#.env file settings 
env_file = PROJECT / ".env"
if not env_file.exists():
    shutil.copy(PROJECT / ".env.example", env_file)
    print("Personal settings file:", env_file)
    print("please enter you personal API key in this file")
load_dotenv(env_file) #copies the KEY=value lines into os.environ
database_url = os.environ["DATABASE_URL"]



#DATABASE WITH DOCKER

#this is  to locate docker whatever your compuetr might be, as not everybody has a mac as me
#Docker needs to be accessible from the computer's command line

DOCKER_FOLDERS = [
    #MAC standard
    "/usr/local/bin",
    #MAC Homebrew
    "/opt/homebrew/bin",
    #MAC inside app
    "/Applications/Docker.app/Contents/Resources/bin",
    #Linux
    "/usr/bin",
    #Windows
    r"C:\Program Files\Docker\Docker\resources\bin",
]

#please make the ajustements if something is missing for the above!

#add these folders to the PATH created before
env = os.environ.copy()
env["PATH"] = os.pathsep.join([env.get("PATH", "")] + DOCKER_FOLDERS)

#check whether Docker is installed, opened bef spyder
docker = shutil.which("docker", path=env["PATH"])

if docker is None:
    raise RuntimeError("Docker was not found. Please verify if you have the app and wether its opened or not, engine running")

#Docker Compose exists in 2 forms: "docker compose" (new, part of Docker Desktop)
#or "docker-compose" (old, separate program). We use whichever this computer has.
if subprocess.run([docker, "compose", "version"], env=env, capture_output=True).returncode == 0:
    COMPOSE = [docker, "compose"]
elif shutil.which("docker-compose", path=env["PATH"]):
    COMPOSE = [shutil.which("docker-compose", path=env["PATH"])]
else:
    raise RuntimeError("Docker Compose was not found (neither 'docker compose' nor 'docker-compose').")

print("Starting the database")

result = subprocess.run(COMPOSE + ["up", "-d"], cwd=PROJECT, env=env,
                        capture_output=True, text=True)
print((result.stdout + result.stderr).strip())
if result.returncode != 0:
    raise RuntimeError("Docker could not start the database...is Docker Desktop open and showing 'Engine running'?")

#waits for the answer (60s) and checks
for attempt in range(60): #try for 60s
    try:
        conn = psycopg.connect(database_url, connect_timeout=2)
        break
    except psycopg.OperationalError:
        time.sleep(1)
else:
    raise RuntimeError("The code has waited for 60s for the database from Docker to answer. It did not work.",
                       "Is Docker Desktop running?")

with conn:
    version = conn.execute("SHOW server_version").fetchone()[0]
    pgvector = conn.execute("SELECT default_version FROM pg_available_extensions "
                            "WHERE name = 'vector'").fetchone()
    tables = [row[0] for row in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name")]

print("\nDONE: the database is running!")
print("  pgvector available:", f"yes (version {pgvector[0]})" if pgvector else "NO")
print("  tables:", ", ".join(tables) if tables else "none yet")
