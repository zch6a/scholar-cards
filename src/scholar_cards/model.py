"""A researcher as the cards show them: the numbers, each traceable to the OpenAlex record it came from, and a
snapshot format (JSON) so that cards can be rendered again without the network."""

from __future__ import annotations

import json
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
        stats = author.get("summary_stats") or {}
        institutions = author.get("last_known_institutions") or []
        if not institutions and author.get("last_known_institution"):
            institutions = [author["last_known_institution"]]
        years = sorted(
            (int(c["year"]), int(c.get("works_count") or 0), int(c.get("cited_by_count") or 0))
            for c in author.get("counts_by_year") or []
            if isinstance(c, dict) and isinstance(c.get("year"), int)
        )
        return cls(
            id=str(author.get("id") or ""),
            name=str(author.get("display_name") or ""),
            works_count=int(author.get("works_count") or 0),
            cited_by_count=int(author.get("cited_by_count") or 0),
            h_index=_int(stats.get("h_index")),
            i10_index=_int(stats.get("i10_index")),
            mean_citedness_2yr=_float(stats.get("2yr_mean_citedness")),
            orcid=str(author.get("orcid") or ""),
            institution=str((institutions[0] or {}).get("display_name") or "") if institutions else "",
            counts_by_year=years,
            top_works=[_work(w) for w in works or []],
            retrieved=retrieved,
            sources=list(sources or []),
        )

    def to_json(self) -> str:
        data = {"tool": "scholar-cards", "snapshot": SNAPSHOT_VERSION, **asdict(self)}
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Scholar:
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("tool") != "scholar-cards":
            raise ValueError("not a scholar-cards snapshot")
        version = data.get("snapshot", 0)
        if not isinstance(version, int) or version > SNAPSHOT_VERSION:
            raise ValueError(f"a snapshot from a newer scholar-cards, or not one (format {version!r}); update scholar-cards")
        try:
            data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            data["counts_by_year"] = [(int(y), int(w), int(c)) for y, w, c in data.get("counts_by_year") or []]
            data["top_works"] = [Work(**{k: v for k, v in w.items() if k in Work.__dataclass_fields__}) for w in data.get("top_works") or []]
            return cls(**data)
        except (TypeError, ValueError, AttributeError) as e:
            raise ValueError(f"not a valid scholar-cards snapshot ({e})") from e

    @classmethod
    def load(cls, path: Path) -> Scholar:
        return cls.from_json(path.read_text(encoding="utf-8"))


def _int(v: object) -> int | None:
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _float(v: object) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _work(w: dict[str, Any]) -> Work:
    location = w.get("primary_location") or {}
    source = location.get("source") or {}
    return Work(
        title=str(w.get("title") or w.get("display_name") or ""),
        year=_int(w.get("publication_year")),
        venue=str(source.get("display_name") or ""),
        cited_by_count=int(w.get("cited_by_count") or 0),
        id=str(w.get("id") or ""),
        doi=str(w.get("doi") or ""),
    )
