"""Regression tests for what the round-1 review found."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from test_cards import AUTHOR, WORKS, FakeAPI, scholar

from scholar_cards.cli import main
from scholar_cards.model import Scholar, Work
from scholar_cards.openalex import Client, OpenAlexError, author_path
from scholar_cards.svg import CARDS, number


def test_control_characters_and_lone_surrogates_do_not_break_the_cards(tmp_path: Path) -> None:
    s = scholar()
    s.name = "Ada\x0b Lovelace\x00"
    s.institution = "Uni\ud800versity"
    s.top_works[0].title = "Notes\x1f on￾ the engine"
    for card in CARDS.values():
        svg = card(s, "auto", "en")
        ET.fromstring(svg)  # parses
        (tmp_path / "c.svg").write_text(svg, encoding="utf-8")  # and can be written
    assert "Ada Lovelace" in CARDS["stats"](s, "auto", "en")


def test_top_n_papers_are_drawn(tmp_path: Path) -> None:
    s = scholar()
    s.top_works = [Work(f"Paper {i}", 2020, "V", 100 - i) for i in range(10)]
    snap = tmp_path / "s.json"
    snap.write_text(s.to_json(), encoding="utf-8")
    assert main(["--snapshot", str(snap), "-o", str(tmp_path), "--cards", "works", "--top", "8"]) == 0
    svg = (tmp_path / "works.svg").read_text(encoding="utf-8")
    assert "Paper 7" in svg and "Paper 8" not in svg


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["top_works"][0].update(extra=1),
        lambda d: d.pop("name"),
        lambda d: d.update(snapshot="2"),
        lambda d: d.update(counts_by_year=None),
        lambda d: d.update(counts_by_year=[["x", 1, 2]]),
    ],
)
def test_bad_snapshots_are_exit_2_not_a_traceback(change, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:  # type: ignore[no-untyped-def]
    data = json.loads(scholar().to_json())
    change(data)
    snap = tmp_path / "s.json"
    snap.write_text(json.dumps(data), encoding="utf-8")
    code = main(["--snapshot", str(snap), "-o", str(tmp_path)])
    err = capsys.readouterr().err
    if "extra" in json.dumps(data["top_works"][0]) or data.get("counts_by_year") is None:
        assert code == 0  # an unknown key is ignored, a null list is empty
    else:
        assert code == 2 and "snapshot" in err


def test_search_shows_the_orcid(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import scholar_cards.cli as cli

    found = {"results": [{"id": "https://openalex.org/A1", "display_name": "Ada", "orcid": "https://orcid.org/0000-0002-1825-009X",
                          "works_count": 3, "cited_by_count": 9, "last_known_institutions": []}]}  # fmt: skip
    monkeypatch.setattr(cli, "Client", lambda: Client(key="", get=FakeAPI([(200, {}, found)])))
    assert main(["search", "Ada"]) == 0
    assert "ORCID 0000-0002-1825-009X" in capsys.readouterr().out


def test_options_are_checked() -> None:
    for bad in (["A1", "--top", "0"], ["A1", "--top", "51"], ["A1", "--cards", ","], ["A1", "junk"]):
        with pytest.raises(SystemExit) as e:
            main(bad)
        assert e.value.code == 2


def test_bad_answers_are_openalex_errors() -> None:
    with pytest.raises(OpenAlexError, match="not a record"):
        Client(key="", get=FakeAPI([(200, {}, None)])).author("A1")
    api = FakeAPI([])
    api.answers = [(200, {}, AUTHOR)]
    bad = Client(key="", get=lambda url, h: (200, {}, b"<html>"))
    with pytest.raises(OpenAlexError, match="not JSON"):
        bad.author("A1")
    waits: list[float] = []
    flaky = FakeAPI([(0, {}, "timeout"), (429, {"retry-after": "3"}, {}), (200, {}, AUTHOR)])
    assert Client(key="", get=flaky, sleep=waits.append).author("A1")["display_name"] == AUTHOR["display_name"]
    assert waits == [1.0, 3.0]  # a network failure retried; a lower-case Retry-After honoured
    assert WORKS


def test_ids_are_matched_whole() -> None:
    for bad in ("MA123", "XYZA123", "https://example.com/A5", "https://api.openalex.org/people/A5", "foo0000-0002-1825-009X"):
        with pytest.raises(OpenAlexError):
            author_path(bad)
    assert author_path("orcid:0000-0002-1825-009x") == "/authors/orcid:0000-0002-1825-009X"
    assert author_path("https://openalex.org/authors/A5/") == "/authors/A5"


def test_numbers_roll_over_to_millions() -> None:
    assert number(999_949) == "999.9k" and number(999_950) == "1.0M"


def test_a_snapshot_is_still_a_scholar() -> None:
    assert isinstance(Scholar.from_json(scholar().to_json()), Scholar)
