#Step 1 of ingestion: DOWNLOAD papers from the OpenAlex API 

import logging
import random
import time
from typing import Any, Iterator

import httpx

logger = logging.getLogger(__name__)

#fields we store: smaller and faster answers
SELECT_FIELDS = ("id,doi,title,display_name,publication_year,cited_by_count,type,"
                 "abstract_inverted_index,authorships,primary_location,best_oa_location")



class OpenAlexError(RuntimeError):
    """OpenAlex could not give us an answer (wrong key, bad filter, budget used up...)."""



class OpenAlexClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openalex.org",
                 max_retries: int = 5):
        self.max_retries = max_retries
        self.requests_made = 0                
        self.last_budget_left = None    
        headers = {"User-Agent": "semantic-literature-search (student project)"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(base_url=base_url, timeout=30, headers=headers)

    def __enter__(self) -> "OpenAlexClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self._http.close()

    def _backoff(self, attempt: int) -> float:
        return random.random() * min(30.0, 2.0 ** attempt)

    def get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        problem = ""
        for attempt in range(self.max_retries + 1):
            try:
                self.requests_made += 1
                response = self._http.get(path, params=params)
            except httpx.TransportError as exc:
                problem = f"network error: {exc}"
                wait = self._backoff(attempt)
            else:
                status = response.status_code
                if status == 200:
                    self.last_budget_left = response.headers.get("X-RateLimit-Remaining-USD")
                    return response.json()
                if status in (401, 403):
                    raise OpenAlexError(
                        f"OpenAlex refused the key (HTTP {status}). Check OPENALEX_API_KEY in "
                        f".env and that your key is activated. Details: {response.text[:300]}")
                if status != 429 and status < 500:
                    raise OpenAlexError(f"HTTP {status} for {path}: {response.text[:300]}")
                problem = f"HTTP {status}"
                retry_after = response.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    wait = float(retry_after)
                    if wait > 60:
                        raise OpenAlexError("OpenAlex daily budget is used up (HTTP 429). "
                                            "It resets at midnight UTC; run again after that.")
                else:
                    wait = self._backoff(attempt)
            if attempt < self.max_retries:
                logger.warning("OpenAlex %s, retrying in %.1f s", problem, wait)
                time.sleep(wait)
        raise OpenAlexError(f"{self.max_retries + 1} failed attemps ({problem}).")

    def count(self, filters: str) -> int:
        data = self.get_json("/works", {"filter": filters, "per_page": 1, "select": "id"})
        return data["meta"]["count"]

    def iter_pages(self, filters: str, per_page: int = 100,
                   sort: str | None = None) -> Iterator[list[dict[str, Any]]]:
        cursor = "*"
        while cursor:
            params = {"filter": filters, "select": SELECT_FIELDS,
                      "per_page": per_page, "cursor": cursor}
            if sort:
                params["sort"] = sort
            data = self.get_json("/works", params)
            results = data.get("results") or []
            if not results:
                return
            yield results
            cursor = data["meta"].get("next_cursor")
