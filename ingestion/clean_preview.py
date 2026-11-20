"""
check the cleaning

"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root

from ingestion import config, corpus  # noqa: E402
from ingestion.normalize import (clean_text, normalize_doi, normalize_work,  # noqa: E402
                                 rebuild_abstract, short_id)
from ingestion.openalex_client import OpenAlexClient, OpenAlexError  # noqa: E402



#description, function, input, expected output
EXAMPLES = [
    ("id: URL -> short id", short_id, "https://openalex.org/W3096831136", "W3096831136"),
    ("id: not a work/author id", short_id, "https://openalex.org/S123", None),
    ("DOI: URL removed, lowercase", normalize_doi, "https://doi.org/10.1038/S41586-025-09422-Z",
     "10.1038/s41586-025-09422-z"),
    ("DOI: 'doi:' prefix", normalize_doi, "doi:10.1145/3422622", "10.1145/3422622"),
    ("DOI: garbage -> None", normalize_doi, "not a doi", None),
    ("text: HTML tags removed", clean_text, "Deep <i>learning</i> for graphs", "Deep learning for graphs"),
    ("text: &amp; decoded", clean_text, "Graphs &amp; networks", "Graphs & networks"),
    ("text: maths 'a < b' kept", clean_text, "if a < b and c > d", "if a < b and c > d"),
    ("text: H<sub>2</sub>O", clean_text, "H<sub>2</sub>O", "H2O"),
    ("text: <br> becomes a space", clean_text, "one<br>two", "one two"),
    ("text: extra spaces", clean_text, "  too   many \n spaces ", "too many spaces"),
    ("text: empty -> None", clean_text, "   ", None),
    ("abstract: rebuilt in order", rebuild_abstract,
     {"graphs": [2, 4], "We": [0], "study": [1], "and": [3]}, "We study graphs and graphs"),
    ("abstract: leading 'Abstract' removed", rebuild_abstract,
     {"Abstract": [0], "General": [1], "reasoning": [2]}, "General reasoning"),
    ("abstract: missing -> None", rebuild_abstract, None, None),
]




def part_a():
    print("CLEANING RULES")
    failures = 0
    for description, function, given, expected in EXAMPLES:
        result = function(given)
        ok = result == expected
        failures += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {description:38} -> {result!r}"
              + ("" if ok else f"   (expected {expected!r})"))
    print(f"  {len(EXAMPLES) - failures}/{len(EXAMPLES)} OK\n")


part_a()
