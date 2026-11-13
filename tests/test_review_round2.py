"""Regression tests for what the round-2 review found (snapshot types, negatives, widths, contrast, accessibility,
numbers, bidi, clusters, crowded years)."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from test_cards import scholar

from scholar_cards.cli import main
from scholar_cards.model import Scholar
from scholar_cards.svg import THEMES, citations_card, clip, stats_card, text_width, works_card


@pytest.mark.parametrize(
    "field,value",
    [("cited_by_count", "6088"), ("h_index", "27"), ("name", 123), ("retrieved", 20261113), ("works_count", -1), ("mean_citedness_2yr", "6")],
)
def test_wrong_types_in_a_snapshot_are_exit_2(field: str, value: object, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = json.loads(scholar().to_json())
    data[field] = value
    snap = tmp_path / "s.json"
    snap.write_text(json.dumps(data), encoding="utf-8")
    assert main(["--snapshot", str(snap), "-o", str(tmp_path)]) == 2
    assert "not a valid scholar-cards snapshot" in capsys.readouterr().err


def test_bad_works_and_years_in_a_snapshot(tmp_path: Path) -> None:
    for change in ({"top_works": [{"title": None, "cited_by_count": 1}]}, {"top_works": [{"title": "t", "cited_by_count": "12"}]},
                   {"counts_by_year": [[2025.9, 1, 3.9]]}, {"counts_by_year": [[2025, 1, -5]]}):  # fmt: skip
        data = json.loads(scholar().to_json()) | change
        with pytest.raises(ValueError, match="not a valid"):
            Scholar.from_json(json.dumps(data))


def test_a_snapshot_with_a_bom_loads(tmp_path: Path) -> None:
    snap = tmp_path / "s.json"
    snap.write_text(scholar().to_json(), encoding="utf-8-sig")
    assert Scholar.load(snap).name == scholar().name


def test_negative_counts_from_the_api_are_zero() -> None:
    s = Scholar.from_openalex({"id": "A1", "display_name": "X", "works_count": -3, "cited_by_count": -9,
                               "counts_by_year": [{"year": 2025, "works_count": 1, "cited_by_count": -5}]})  # fmt: skip
    assert s.cited_by_count == 0 and s.counts_by_year == [(2025, 1, 0)]
    assert 'y="-' not in citations_card(s)  # no bar above the chart


def test_wide_letters_are_cut_before_they_overflow() -> None:
    s = scholar()
    s.name = "W" * 46
    title = re.search(r'class="title"[^>]*>([^<]*)<', stats_card(s)).group(1)  # type: ignore[union-attr]
    assert title.endswith("…⁩") and text_width(title.strip("⁨⁩"), 18, bold=True) <= 445
    assert text_width("M" * 10, 14) > text_width("i" * 10, 14)


def _contrast(a: str, b: str) -> float:
    def lum(h: str) -> float:
        rgb = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_meets_wcag_aa(theme: str) -> None:
    t = THEMES[theme]
    assert all(_contrast(t[k], t["bg"]) >= 4.5 for k in ("title", "text", "muted"))
    assert _contrast(t["bar"], t["bg"]) >= 3.0  # the partial bar's outline is the bar colour


def test_screen_readers_get_the_numbers_and_the_language() -> None:
    svg = stats_card(scholar(), lang="zh")
    root = ET.fromstring(svg)
    sid = root.get("id")
    assert root.get("aria-labelledby") == f"{sid}-t {sid}-d" and root.get("{http://www.w3.org/XML/1998/namespace}lang") == "zh"
    desc = root.find("{http://www.w3.org/2000/svg}desc").text  # type: ignore[union-attr]
    assert "总被引 12.3k" in desc and "h 指数 17" in desc
    assert "Notes on the analytical engine (Taylor's Scientific Memoirs, 1843): 5000 cited" in works_card(scholar())
    assert "2024: 1000; 2025: 1100; 2026: 0 (so far)" in citations_card(scholar())


def test_means_have_two_decimals_counts_none() -> None:
    s = scholar()
    s.mean_citedness_2yr = 3.0
    assert ">3.00<" in stats_card(s)


def test_names_are_isolated_for_bidi_and_clusters_are_kept() -> None:
    s = scholar()
    s.name = "דוד בן-גוריון (2020) Lab"
    assert "⁨דוד בן-גוריון (2020) Lab⁩" in stats_card(s)
    assert clip("ab👨‍👩‍👧xxxxxxxxxxxxxxxxxxxx", 10, 40).count("‍") in (0, 2)  # the family emoji whole, or not at all


def test_many_years_get_thinned_labels() -> None:
    s = scholar()
    s.counts_by_year = [(y, 1, y - 1980) for y in range(1981, 2027)]
    svg = citations_card(s, years=40)
    labels = re.findall(r'y="188" text-anchor="middle">(\d\d\*?)</text>', svg)  # the year labels under the bars
    assert len(labels) == 20 and labels[-1] == "26*" and labels[-2] == "24"  # every other year, counted from the last
