"""scholar-cards cited, with a made-up Semantic Scholar (no network)."""

from __future__ import annotations

import json

import pytest

from scholar_cards import cited
from scholar_cards.cli import main

ROWS = [
    {"citingPaper": {"paperId": "a" * 40, "title": "Faster Readers", "year": 2025, "venue": "ACL", "publicationDate": "2025-05-01",
                     "externalIds": {"ArXiv": "2505.00001"}, "url": "https://www.semanticscholar.org/paper/a"},
     "contexts": ["Our reader outperforms BERT (Devlin et al., 2019) on all four tasks.", "We initialize from BERT-base."]},
    {"citingPaper": {"paperId": "b" * 40, "title": "On the Limits of Masked Models", "year": 2024, "venue": "",
                     "publicationDate": "2024-02-03", "externalIds": {}, "url": "https://www.semanticscholar.org/paper/b"},
     "contexts": ["However, BERT fails to model long documents [4]."]},
    {"citingPaper": {"paperId": "c" * 40, "title": "A Survey", "year": 2023, "venue": "", "publicationDate": None,
                     "externalIds": {}, "url": ""}, "contexts": []},
    {"citingPaper": {"paperId": None, "title": None}},
]  # fmt: skip


class Fake:
    def __init__(self, fail: int = 0):
        self.urls: list[str] = []
        self.fail = fail

    def __call__(self, url: str, headers: dict[str, str]):
        self.urls.append(url)
        assert "x-api-key" not in headers or headers["x-api-key"]
        if self.fail:
            self.fail -= 1
            return 429, {}, b"{}"
        if "/citations" in url:
            return 200, {}, json.dumps({"offset": 0, "data": ROWS}).encode()
        return 200, {}, json.dumps({"title": "BERT", "citationCount": 120000}).encode()


@pytest.fixture
def fake(monkeypatch):
    f = Fake()
    monkeypatch.setattr(cited, "_urlopen", f)
    monkeypatch.setattr(cited.time, "sleep", lambda s: None)
    return f


def test_labels_and_who_claims_to_beat_it(fake, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert main(["cited", "1810.04805"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("BERT: 3 citing paper(s) of 120,000 counted by Semantic Scholar")
    assert "with the sentences that cite it: 2; contrasts with 1, compares with 1, builds on 0, mentions 0; claims to beat it: 1" in out
    assert "Claims to beat it:\n  2025-05-01  Faster Readers" in out
    assert "(compares with: outperforms)" in out and "[no context]" in out
    assert "arXiv:1810.04805" in fake.urls[0] and not list(tmp_path.iterdir())  # no state file unless asked


def test_new_only_with_a_state_file(fake, capsys, tmp_path):
    state = tmp_path / "s.json"
    assert main(["cited", "arXiv:1810.04805", "--new", "--state", str(state)]) == 0
    assert "3 new citing paper(s)" in capsys.readouterr().out  # first run: everything, then remembered
    assert len(json.loads(state.read_text(encoding="utf-8"))["seen"]) == 3
    assert main(["cited", "arXiv:1810.04805", "--new", "--state", str(state), "--fail-on-new"]) == 0
    assert "0 new citing paper(s)" in capsys.readouterr().out
    ROWS.append({"citingPaper": {"paperId": "d" * 40, "title": "Newer", "year": 2026, "publicationDate": "2026-11-01", "externalIds": {}},
                 "contexts": ["We use BERT."]})  # fmt: skip
    try:
        assert main(["cited", "arXiv:1810.04805", "--new", "--state", str(state), "--fail-on-new", "--format", "markdown"]) == 1
        md = capsys.readouterr().out
        assert "### New citations of BERT (1)" in md and "| builds on | We use BERT. |" in md
    finally:
        ROWS.pop()


def test_json_and_retries(monkeypatch, capsys):
    f = Fake(fail=2)
    monkeypatch.setattr(cited, "_urlopen", f)
    waits: list[float] = []
    monkeypatch.setattr(cited.time, "sleep", waits.append)
    assert main(["cited", "https://doi.org/10.18653/v1/N19-1423", "--format", "json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["paper"] == "DOI:10.18653/v1/N19-1423" and doc["summary"]["claims to beat it"] == 1
    assert [c["main"] for c in doc["citing"]] == ["compares with", "contrasts with", ""]
    assert waits == [5.0, 20.0]


def test_errors(monkeypatch, capsys):
    monkeypatch.setattr(cited, "_urlopen", lambda url, h: (429, {}, b""))
    monkeypatch.setattr(cited.time, "sleep", lambda s: None)
    assert main(["cited", "1810.04805"]) == 2
    assert "S2_API_KEY" in capsys.readouterr().err
    assert main(["cited", "not a paper"]) == 2
