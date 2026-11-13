"""The model, the OpenAlex client (with a fake transport: no test reaches the network), the cards and the CLI."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scholar_cards.cli import fetch, main, write_cards
from scholar_cards.model import Scholar
from scholar_cards.openalex import Client, OpenAlexError, author_path
from scholar_cards.svg import CARDS, citations_card, stats_card, works_card

AUTHOR = {
    "id": "https://openalex.org/A123",
    "display_name": "Ada <Lovelace> & Co",
    "orcid": "https://orcid.org/0000-0002-1825-009X",
    "works_count": 42,
    "cited_by_count": 12345,
    "summary_stats": {"h_index": 17, "i10_index": 25, "2yr_mean_citedness": 3.25},
    "last_known_institutions": [{"display_name": "University of Somewhere"}],
    "counts_by_year": [{"year": y, "works_count": 3, "cited_by_count": 100 * (y - 2014)} for y in range(2015, 2026)],
}
WORKS = {
    "results": [
        {"id": "https://openalex.org/W1", "title": "Notes on the analytical engine", "publication_year": 1843, "cited_by_count": 5000,
         "primary_location": {"source": {"display_name": "Taylor's Scientific Memoirs"}}, "doi": "https://doi.org/10.1/x"},
        {"id": "https://openalex.org/W2", "title": "A very long title " * 8, "publication_year": 2020, "cited_by_count": 12,
         "primary_location": None},
    ]
}  # fmt: skip


class FakeAPI:
    def __init__(self, answers: list[tuple[int, dict[str, str], object]]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
        self.calls.append((url, headers))
        status, h, body = self.answers.pop(0)
        return status, h, json.dumps(body).encode()


def scholar() -> Scholar:
    return Scholar.from_openalex(AUTHOR, WORKS["results"], retrieved="2026-11-13", sources=["https://api.openalex.org/authors/A123"])


def test_author_ids_and_orcids() -> None:
    assert author_path("a123") == "/authors/A123"
    assert author_path("0000-0002-1825-009x") == "/authors/orcid:0000-0002-1825-009X"
    with pytest.raises(OpenAlexError, match="search NAME"):
        author_path("Ada Lovelace")


def test_fetch_with_a_fake_api_key_as_header_and_a_retry() -> None:
    api = FakeAPI([(429, {"Retry-After": "1"}, {}), (200, {}, AUTHOR), (200, {}, WORKS)])
    waits: list[float] = []
    s = fetch("A123", Client(key="secret", get=api, sleep=waits.append), today="2026-11-13")
    assert waits == [1.0] and len(api.calls) == 3
    assert all(h["Authorization"] == "Bearer secret" and "secret" not in url for url, h in api.calls)
    assert api.calls[0][1]["User-Agent"].startswith("scholar-cards/")
    assert s.h_index == 17 and s.cited_by_count == 12345 and [w.year for w in s.top_works] == [1843, 2020]
    assert s.sources == ["https://api.openalex.org/authors/A123", api.calls[2][0]] and "author.id%3AA123" in api.calls[2][0]


def test_errors_say_what_happened() -> None:
    with pytest.raises(OpenAlexError, match="no record"):
        Client(key="", get=FakeAPI([(404, {}, {})])).author("A9")
    with pytest.raises(OpenAlexError, match="kept answering 503"):
        Client(key="", get=FakeAPI([(503, {}, {})] * 4), sleep=lambda _: None).author("A9")


def test_snapshot_round_trip() -> None:
    s = scholar()
    assert Scholar.from_json(s.to_json()) == s
    with pytest.raises(ValueError, match="not a scholar-cards snapshot"):
        Scholar.from_json("{}")


@pytest.mark.parametrize("card", list(CARDS))
@pytest.mark.parametrize("theme", ["auto", "light", "dark"])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_cards_are_valid_svg(card: str, theme: str, lang: str) -> None:
    svg = CARDS[card](scholar(), theme, lang)
    root = ET.fromstring(svg)  # well-formed XML, the name escaped
    assert root.tag.endswith("svg") and "Ada &lt;Lovelace&gt; &amp; Co" in svg and "2026-11-13" in svg
    assert ("prefers-color-scheme" in svg) == (theme == "auto")


def test_what_the_cards_say() -> None:
    s = scholar()
    stats = stats_card(s)
    assert "12.3k" in stats and ">17<" in stats and ">25<" in stats and ">42<" in stats and "University of Somewhere" in stats
    works = works_card(s)
    assert "Notes on the analytical engine" in works and "Taylor's Scientific Memoirs · 1843" in works and "…" in works
    bars = citations_card(s)
    assert bars.count('class="bar"') == 10 and "2025: 1100" in bars and ">1,100<" in bars  # the last ten years, the peak labelled
    assert "总被引" in stats_card(s, lang="zh")


def test_the_current_year_is_marked_partial() -> None:
    s = scholar()
    s.retrieved = "2025-03-01"  # the snapshot's year is the last bar's
    bars = citations_card(s)
    assert bars.count('opacity="0.45"') == 1 and "2025: 1100 (so far)" in bars and ">25*<" in bars and "*so far" in bars
    assert 'opacity="0.45"' not in citations_card(scholar())  # retrieved 2026: 2025 is a whole year


def test_each_card_scopes_its_css() -> None:
    import re

    light, dark = stats_card(scholar(), "light"), stats_card(scholar(), "dark")
    ids = [re.search(r'id="(sc-[0-9a-f]{10})"', svg).group(1) for svg in (light, dark)]  # type: ignore[union-attr]
    assert ids[0] != ids[1]  # inlined side by side, one does not restyle the other
    style = re.search(r"<style>(.*)</style>", dark).group(1)  # type: ignore[union-attr]
    assert all(rule.startswith(f"#{ids[1]} ") for rule in re.split(r"(?<=\})", style) if rule)


def test_cli_from_a_snapshot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    snap = tmp_path / "scholar.json"
    snap.write_text(scholar().to_json(), encoding="utf-8")
    assert main(["--snapshot", str(snap), "-o", str(tmp_path / "cards"), "--theme", "light,dark", "--cards", "stats"]) == 0
    assert sorted(p.name for p in (tmp_path / "cards").iterdir()) == ["stats-dark.svg", "stats-light.svg"]
    assert main(["--snapshot", str(tmp_path / "missing.json")]) == 2
    with pytest.raises(SystemExit):
        main(["--snapshot", str(snap), "--cards", "badge"])
    assert write_cards(scholar(), tmp_path / "x", ["works"], ["auto"], "en")[0].name == "works.svg"
