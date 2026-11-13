"""OpenAlex, as far as the cards need it: an author (by OpenAlex ID or ORCID), their most cited works, and a search
to find the right author record. No key is needed for this; one, in ``OPENALEX_API_KEY``, raises the daily budget
and is sent as a header, never in a URL. The User-Agent names the tool, not the user."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from . import __version__

API = "https://api.openalex.org"
USER_AGENT = f"scholar-cards/{__version__} (+https://github.com/zch6a/scholar-cards)"
ORCID = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$", re.I)
OPENALEX_ID = re.compile(r"(?:https?://(?:api\.)?openalex\.org/(?:authors/)?)?(A\d+)$", re.I)

Getter = Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]  # url, headers -> status, headers, body


class OpenAlexError(Exception):
    pass


def author_path(who: str) -> str:
    """The API path of an author given as an OpenAlex ID (or its URL) or an ORCID (or its URL).

    >>> author_path("A5023888391"), author_path("https://openalex.org/A5023888391"), author_path("https://orcid.org/0000-0002-1825-009X")
    ('/authors/A5023888391', '/authors/A5023888391', '/authors/orcid:0000-0002-1825-009X')
    """
    who = who.strip().rstrip("/")
    if m := OPENALEX_ID.search(who):
        return f"/authors/{m.group(1).upper()}"
    if m := ORCID.search(who):
        return f"/authors/orcid:{m.group(1).upper()}"
    raise OpenAlexError(f"{who!r} is neither an OpenAlex author ID (A followed by digits) nor an ORCID; find the ID with: scholar-cards search NAME")


def _urlopen(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as r:  # noqa: S310 - the URL is the API's, built here
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read() or b""


class Client:
    """A small OpenAlex client: JSON GETs with the key as a header, retrying (up to three times) when told to wait."""

    def __init__(self, key: str | None = None, get: Getter | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self.key = key if key is not None else os.environ.get("OPENALEX_API_KEY", "")
        self._get = get or _urlopen
        self._sleep = sleep
        self.requested: list[str] = []  # the URLs asked for, for the snapshot's sources (the key is never in them)

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        for attempt in range(4):
            status, response_headers, body = self._get(url, headers)
            if status == 429 or status >= 500:
                if attempt == 3:
                    break
                wait = response_headers.get("Retry-After", "")
                self._sleep(min(60.0, float(wait)) if wait.replace(".", "", 1).isdigit() else 2.0**attempt)
                continue
            if status == 404:
                raise OpenAlexError(f"OpenAlex has no record at {url}")
            if status != 200:
                raise OpenAlexError(f"OpenAlex answered {status} for {url}: {body[:200].decode('utf-8', 'replace')}")
            self.requested.append(url)
            return json.loads(body)
        raise OpenAlexError(f"OpenAlex kept answering {status} for {url} (rate limit or outage); try later, or set OPENALEX_API_KEY")

    def author(self, who: str) -> dict[str, Any]:
        return self.get(author_path(who))  # type: ignore[no-any-return]

    def top_works(self, author_id: str, n: int = 5) -> list[dict[str, Any]]:
        short = author_id.rstrip("/").rsplit("/", 1)[-1]
        data = self.get("/works", {"filter": f"author.id:{short}", "sort": "cited_by_count:desc", "per_page": str(max(1, min(n, 50))),
                                   "select": "id,title,publication_year,primary_location,cited_by_count,doi"})  # fmt: skip
        return list(data.get("results") or [])

    def search(self, name: str, n: int = 10) -> list[dict[str, Any]]:
        data = self.get("/authors", {"search": name, "per_page": str(n),
                                     "select": "id,display_name,orcid,works_count,cited_by_count,last_known_institutions"})  # fmt: skip
        return list(data.get("results") or [])
