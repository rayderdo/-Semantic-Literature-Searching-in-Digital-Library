#Reads the project settings from .env
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT / ".env") #copies the KEY=value lines into os.environ

DATABASE_URL = os.getenv("DATABASE_URL",
                         "postgresql://postgres:postgres@localhost:5432/semantic_search")

OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "").strip().strip('"').strip("'")
OPENALEX_BASE_URL = "https://api.openalex.org"
