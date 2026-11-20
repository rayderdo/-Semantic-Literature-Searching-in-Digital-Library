"""
Step 2 of ingestion: CLEANning of the DATA

"""

from __future__ import annotations 

import html
import re
from dataclasses import dataclass, field
from typing import Any

'''regex - i just went on their website and searched for the perfect regex annotation for keeping only the valuable part of the openalex id
3 types of regex used :
    - https://openalex.org/W123 → W123
    - https://doi.org/10.1/abc → 10.1/abc
    - 10.1145/3422622 → valid, hello → invalid
'''

#format : https://openalex.org/W123 → W123
_ID_RE = re.compile(r"(?:https?://openalex\.org/)?([WA]\d+)")

def short_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _ID_RE.fullmatch(value.strip())
    return match.group(1) if match else None


#format : https://doi.org/10.1/abc → 10.1/abc
_DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)\s*", re.IGNORECASE)

#Shape of a valid DOI
#format : 10.1145/3422622 → valid, hello → invalid
_DOI_SHAPE_RE = re.compile(r"^10\.\d{4,9}/\S+$")


def normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    doi = _DOI_PREFIX_RE.sub("", value.strip()).strip().lower()
    return doi if _DOI_SHAPE_RE.match(doi) else None


#remove HTML tags, decode &amp;, spaces etc...
_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")

#tags that separate blocks of text (paragraph, line break, list item...) must become a space
_BLOCK_TAG_RE = re.compile(r"</?(?:br|p|div|li|jats:p|jats:sec|jats:title)\b[^>]*>",
                           re.IGNORECASE)

# \s+ = one or more spaces,tabs,line breaks
_SPACES_RE = re.compile(r"\s+")


def clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = _BLOCK_TAG_RE.sub(" ", value) #block tags = one<br>two -> one two
    text = _TAG_RE.sub("", text) #other tags = H<sub>2</sub>O -> H2O
    text = html.unescape(text) # &amp; -> &, &lt; -> <, ...
    text = _SPACES_RE.sub(" ", text).strip()
    return text or None



#abstract rebuild
_ABSTRACT_WORD_RE = re.compile(r"^abstract[\s:.\-–—]+(?=\S)", re.IGNORECASE)

#attention to indexes of words
def rebuild_abstract(inverted_index: Any) -> str | None:
    if not isinstance(inverted_index, dict) or not inverted_index:
        return None
    word_at = {}
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for pos in positions:
                if isinstance(pos, int):
                    word_at[pos] = word
    if not word_at:
        return None
    text = " ".join(word_at[pos] for pos in sorted(word_at))
    text = clean_text(text)
    return _ABSTRACT_WORD_RE.sub("", text) if text else None


#whole paper
@dataclass
class CleanPaper:
    work: dict #1 row `works`
    authors: list = field(default_factory=list) # rows `authors`
    links: list = field(default_factory=list) # rows `work_authors`


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def normalize_work(record: dict) -> CleanPaper | None:
    if not isinstance(record, dict):
        return None
    work_id = short_id(record.get("id"))
    title = clean_text(record.get("title") or record.get("display_name"))
    abstract = rebuild_abstract(record.get("abstract_inverted_index"))
    if not work_id or not work_id.startswith("W") or not title or not abstract:
        return None

    primary = record.get("primary_location") or {}
    best_open = record.get("best_oa_location") or {}
    doi = normalize_doi(record.get("doi"))
    work = {
        "id": work_id,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "publication_year": _int_or_none(record.get("publication_year")),
        "cited_by_count": _int_or_none(record.get("cited_by_count")) or 0,
        "type": record.get("type"),
        #link to original source (publisher's page/DOI)
        "landing_page_url": primary.get("landing_page_url") or
                            ("https://doi.org/" + doi if doi else None),
        "pdf_url": best_open.get("pdf_url") or primary.get("pdf_url"),
        "raw_json": record, #raw file
    }

    authors, links, seen = [], [], set()
    for position, authorship in enumerate(record.get("authorships") or [], start=1):
        author = (authorship or {}).get("author") or {}
        author_id = short_id(author.get("id"))
        name = clean_text(author.get("display_name"))
        if not author_id or not author_id.startswith("A") or not name or author_id in seen:
            continue   # no usable id/name, or the same person listed twice on this paper
        seen.add(author_id)
        institutions = (authorship or {}).get("institutions") or [{}]
        authors.append({"id": author_id, "name": name,
                        "affiliation": clean_text((institutions[0] or {}).get("display_name"))})
        #position = order in the author list
        links.append({"work_id": work_id, "author_id": author_id, "author_position": position})
    return CleanPaper(work=work, authors=authors, links=links)
