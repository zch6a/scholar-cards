"""Before a release: every card in every theme and language, from a snapshot and from a (fake) fetch, through the
command line; and the README's example numbers are the example's."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from test_cards import AUTHOR, WORKS, FakeAPI

from scholar_cards.cli import main
from scholar_cards.model import Scholar
from scholar_cards.openalex import Client

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_every_card_theme_and_language_from_the_example(lang: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--snapshot", str(ROOT / "examples" / "scholar.json"), "-o", str(tmp_path), "--theme", "auto,light,dark", "--lang", lang]) == 0
    files = sorted(tmp_path.glob("*.svg"))
    assert [p.name for p in files] == sorted(f"{c}-{t}.svg" for c in ("stats", "works", "citations") for t in ("auto", "light", "dark"))
    for p in files:
        root = ET.fromstring(p.read_text(encoding="utf-8"))
        assert root.get("{http://www.w3.org/XML/1998/namespace}lang") == lang
    assert len(capsys.readouterr().out.splitlines()) == 9


def test_a_fetch_writes_the_snapshot_and_the_cards(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import scholar_cards.cli as cli

    monkeypatch.setattr(cli, "Client", lambda: Client(key="", get=FakeAPI([(200, {}, AUTHOR), (200, {}, WORKS)])))
    assert main(["A123", "-o", str(tmp_path / "cards")]) == 0
    s = Scholar.load(tmp_path / "cards" / "scholar.json")
    assert s.h_index == 17 and len(s.sources) == 2 and all("api_key" not in u for u in s.sources)
    assert main(["--snapshot", str(tmp_path / "cards" / "scholar.json"), "-o", str(tmp_path / "again")]) == 0
    assert (tmp_path / "again" / "stats.svg").read_text(encoding="utf-8") == (tmp_path / "cards" / "stats.svg").read_text(encoding="utf-8")


@pytest.mark.parametrize("readme", ["README.md", "README.zh-CN.md"])
def test_the_readme_numbers_are_the_examples(readme: str) -> None:
    s = Scholar.load(ROOT / "examples" / "scholar.json")
    text = (ROOT / readme).read_text(encoding="utf-8")
    alt = re.search(r'alt="[^"]*?(\d[\d,]*)[^"]*?27[^"]*?48[^"]*?(\d+)[^"]*"', text)
    assert alt, "the stats card's alt text names the example's numbers"
    assert alt.group(1).replace(",", "") == str(s.cited_by_count) and alt.group(2) == str(s.works_count)
    assert s.h_index == 27 and s.i10_index == 48
    for card in ("stats", "works", "citations"):  # the README's images are the example's cards as the tool draws them now
        drawn = (ROOT / "docs" / f"{card}.svg").read_text(encoding="utf-8")
        assert s.name in drawn and s.retrieved in drawn
