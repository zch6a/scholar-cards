"""Regression tests for what the round-3 review found."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_cards import scholar

from scholar_cards.cli import main
from scholar_cards.model import Scholar
from scholar_cards.svg import clip, stats_card


@pytest.mark.parametrize(
    "text",
    [
        "भाषाओं के लिए बहुभाषी मॉडल का अध्ययन और मूल्यांकन",  # Devanagari vowel signs (Mc, class 0)
        "การศึกษาภาษาไทยด้วยแบบจำลองภาษาขนาดใหญ่",  # Thai vowel marks
        "Hi 👋🏽👋🏽👋🏽👋🏽👋🏽👋🏽👋🏽👋🏽",  # skin tones
        "🇯🇵🇯🇵🇯🇵🇯🇵🇯🇵🇯🇵🇯🇵🇯🇵🇯🇵🇯🇵",  # flags: pairs of regional indicators
        "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣",  # keycaps
    ],
)
def test_clip_never_cuts_inside_a_cluster(text: str) -> None:
    import unicodedata

    for width in range(40, 200, 7):
        cut = clip(text, 14, width)
        if not cut.endswith("…"):
            continue
        kept = cut[:-1].rstrip()
        rest = text[len(kept) :].lstrip()
        assert not rest or (unicodedata.category(rest[0]) not in ("Mn", "Mc", "Me") and rest[0] not in "⃣️‍")
        assert not rest or not ("\U0001f3fb" <= rest[0] <= "\U0001f3ff")
        flags = sum(1 for c in kept if "\U0001f1e6" <= c <= "\U0001f1ff")
        assert flags % 2 == 0


@pytest.mark.parametrize(
    "change",
    [{"cited_by_count": 10**400}, {"mean_citedness_2yr": float("nan")}, {"mean_citedness_2yr": float("inf")}, {"sources": "http://x"}],
)
def test_snapshots_with_impossible_numbers_are_exit_2(change: dict[str, object], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = json.loads(scholar().to_json()) | change
    snap = tmp_path / "s.json"
    snap.write_text(json.dumps(data), encoding="utf-8")
    assert main(["--snapshot", str(snap), "-o", str(tmp_path)]) == 2
    assert "not a valid" in capsys.readouterr().err


def test_a_deeply_nested_snapshot_is_exit_2(tmp_path: Path) -> None:
    snap = tmp_path / "s.json"
    snap.write_text('{"tool": "scholar-cards", "x": ' + "[" * 100_000 + "]" * 100_000 + "}", encoding="utf-8")
    assert main(["--snapshot", str(snap), "-o", str(tmp_path)]) == 2


def test_null_optional_text_loads() -> None:
    data = json.loads(scholar().to_json()) | {"orcid": None, "institution": None, "retrieved": None}
    data["top_works"][0]["venue"] = None
    s = Scholar.from_json(json.dumps(data))
    assert s.orcid == "" and s.institution == "" and s.top_works[0].venue == ""


def test_malformed_api_records_are_read_without_crashing() -> None:
    author = {"id": "A1", "display_name": "X", "works_count": 3, "cited_by_count": 9, "summary_stats": [], "last_known_institutions": ["MIT"],
              "counts_by_year": [{"year": -1, "cited_by_count": 4}, {"year": 2025, "cited_by_count": float("nan")}]}  # fmt: skip
    s = Scholar.from_openalex(author, [1, {"title": "T", "primary_location": "x", "cited_by_count": 2}])  # type: ignore[list-item]
    assert s.h_index is None and s.institution == "" and s.counts_by_year == [(2025, 0, 0)] and [w.title for w in s.top_works] == ["T"]
    assert Scholar.from_json(s.to_json()) == s  # and what it writes loads back
    assert stats_card(s)
