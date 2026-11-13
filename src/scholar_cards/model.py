"""A researcher as the cards show them: the numbers, each traceable to the OpenAlex record it came from, and a
snapshot format (JSON) so that cards can be rendered again without the network."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SNAPSHOT_VERSION = 1


@dataclass
class Work:
    title: str
    year: int | None
    venue: str
    cited_by_count: int
    id: str = ""  # the OpenAlex work, https://openalex.org/W...
    doi: str = ""


@dataclass
class Scholar:
    id: str  # https://openalex.org/A...
    name: str
    works_count: int
    cited_by_count: int
    h_index: int | None = None
    i10_index: int | None = None
    mean_citedness_2yr: float | None = None
    orcid: str = ""
    institution: str = ""
    counts_by_year: list[tuple[int, int, int]] = field(default_factory=list)  # (year, works, citations), oldest first
    top_works: list[Work] = field(default_factory=list)
    retrieved: str = ""  # the date the record was fetched, YYYY-MM-DD
    sources: list[str] = field(default_factory=list)  # the API URLs the numbers came from (no key in them)

    @classmethod
    def from_openalex(cls, author: dict[str, Any], works: list[dict[str, Any]] | None = None, retrieved: str = "",
                      sources: list[str] | None = None) -> Scholar:  # fmt: skip
        """From an OpenAlex author record and its most cited works.

        >>> s = Scholar.from_openalex({"id": "https://openalex.org/A1", "display_name": "Ada", "works_count": 3,
        ...     "cited_by_count": 10, "summary_stats": {"h_index": 2, "i10_index": 0, "2yr_mean_citedness": 1.5},
        ...     "counts_by_year": [{"year": 2025, "works_count": 1, "cited_by_count": 6},
        ...                        {"year": 2024, "works_count": 2, "cited_by_count": 4}]})
        >>> s.name, s.h_index, s.counts_by_year
        ('Ada', 2, [(2024, 2, 4), (2025, 1, 6)])
        """
        stats = _dict(author.get("summary_stats"))
        institutions = [i for i in _list(author.get("last_known_institutions")) if isinstance(i, dict)]
        if not institutions and isinstance(author.get("last_known_institution"), dict):
            institutions = [author["last_known_institution"]]
        years = sorted(
            (c["year"], _int(c.get("works_count")) or 0, _int(c.get("cited_by_count")) or 0)
            for c in _list(author.get("counts_by_year"))
            if isinstance(c, dict) and isinstance(c.get("year"), int) and not isinstance(c["year"], bool) and 0 < c["year"] < 10_000
        )
        return cls(
            id=str(author.get("id") or ""),
            name=str(author.get("display_name") or ""),
            works_count=_int(author.get("works_count")) or 0,
            cited_by_count=_int(author.get("cited_by_count")) or 0,
            h_index=_int(stats.get("h_index")),
            i10_index=_int(stats.get("i10_index")),
            mean_citedness_2yr=_float(stats.get("2yr_mean_citedness")),
            orcid=str(author.get("orcid") or ""),
            institution=str(institutions[0].get("display_name") or "") if institutions else "",
            counts_by_year=years,
            top_works=[_work(w) for w in works or [] if isinstance(w, dict)],
            retrieved=retrieved,
            sources=list(sources or []),
        )

    def to_json(self) -> str:
        data = {"tool": "scholar-cards", "snapshot": SNAPSHOT_VERSION, **asdict(self)}
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Scholar:
        try:
            data = json.loads(text)
        except RecursionError as e:
            raise ValueError("not a scholar-cards snapshot (nested too deep)") from e
        if not isinstance(data, dict) or data.get("tool") != "scholar-cards":
            raise ValueError("not a scholar-cards snapshot")
        version = data.get("snapshot", 0)
        if not isinstance(version, int) or version > SNAPSHOT_VERSION:
            raise ValueError(f"a snapshot from a newer scholar-cards, or not one (format {version!r}); update scholar-cards")
        try:
            return cls(
                id=_text(data, "id"),
                name=_text(data, "name"),
                works_count=_count(data, "works_count"),
                cited_by_count=_count(data, "cited_by_count"),
                h_index=_count(data, "h_index", optional=True),
                i10_index=_count(data, "i10_index", optional=True),
                mean_citedness_2yr=_mean(data.get("mean_citedness_2yr")),
                orcid=_text(data, "orcid", ""),
                institution=_text(data, "institution", ""),
                counts_by_year=[_year(x) for x in data.get("counts_by_year") or []],
                top_works=[_snapshot_work(w) for w in data.get("top_works") or []],
                retrieved=_text(data, "retrieved", ""),
                sources=[str(x) for x in _sources(data.get("sources"))],
            )
        except (TypeError, ValueError, AttributeError, KeyError, RecursionError) as e:
            raise ValueError(f"not a valid scholar-cards snapshot ({e})") from e

    @classmethod
    def load(cls, path: Path) -> Scholar:
        return cls.from_json(path.read_text(encoding="utf-8-sig"))  # an editor may have saved it with a BOM


def _text(data: dict[str, Any], key: str, default: str | None = None) -> str:
    v = data.get(key, default)
    if v is None and default is not None:
        v = default  # an optional text left null
    if not isinstance(v, str):
        raise TypeError(f"{key} must be text, not {v!r}")
    return v


def _whole(v: object, what: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= MAX_COUNT:
        raise TypeError(f"{what} must be a whole number from 0 to {MAX_COUNT}, not {v!r}")
    return v


def _count(data: dict[str, Any], key: str, optional: bool = False) -> Any:
    if optional and data.get(key) is None:
        return None
    return _whole(data.get(key), key)


def _mean(v: object) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= MAX_COUNT:
        raise TypeError(f"mean_citedness_2yr must be a number of 0 or more, not {v!r}")
    return float(v)


def _sources(v: object) -> list[Any]:
    if v is None:
        return []
    if not isinstance(v, list):
        raise TypeError(f"sources must be a list, not {v!r}")
    return v


def _year(x: Any) -> tuple[int, int, int]:
    year, works, cites = x
    return _whole(year, "a year"), _whole(works, "a year's works"), _whole(cites, "a year's citations")


def _snapshot_work(w: dict[str, Any]) -> Work:
    year = w.get("year")
    return Work(
        title=_text(w, "title"),
        year=None if year is None else _whole(year, "a work's year"),
        venue=_text(w, "venue", ""),
        cited_by_count=_whole(w.get("cited_by_count"), "a work's cited_by_count"),
        id=_text(w, "id", ""),
        doi=_text(w, "doi", ""),
    )


MAX_COUNT = 10**12  # more than any count could be; bigger is a broken record, not a number to print


def _int(v: object) -> int | None:
    """A count from OpenAlex: a whole number from 0 to MAX_COUNT, else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return min(MAX_COUNT, max(0, int(v)))


def _dict(v: object) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _list(v: object) -> list[Any]:
    return v if isinstance(v, list) else []


def _float(v: object) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return max(0.0, float(v))


def _work(w: dict[str, Any]) -> Work:
    location = _dict(w.get("primary_location"))
    source = _dict(location.get("source"))
    return Work(
        title=str(w.get("title") or w.get("display_name") or ""),
        year=_int(w.get("publication_year")),
        venue=str(source.get("display_name") or ""),
        cited_by_count=_int(w.get("cited_by_count")) or 0,
        id=str(w.get("id") or ""),
        doi=str(w.get("doi") or ""),
    )
