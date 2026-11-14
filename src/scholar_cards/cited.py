r"""Who cites a paper, and what they say about it.

    scholar-cards cited arXiv:1810.04805           the citing papers, newest first, with the sentences that cite it
    scholar-cards cited 10.18653/v1/N19-1423 --new   only those not seen at the last run (kept in a state file)

The citing papers and the sentences that cite (their "contexts") come from Semantic Scholar's public API: only the
paper's id is sent. Semantic Scholar has contexts for part of the citing papers (those whose full text it could
read). Each context is labelled by rules on its words, not by a model, and the label says which words decided it:

- contrasts with: "however", "unlike", "although", "fails to", "lacks", "limitation" ...
- compares with: "baseline", "outperforms", "we compare", "compared with", "better than", a result with ± ...
- builds on: "we use", "based on", "follows", "as in", "backbone", "fine-tune" ...
- mentions: none of these (background).

A citing paper that says it outperforms or surpasses the cited one in a context is listed as "claims to beat it".
"""

from __future__ import annotations

import http.client
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import __version__

API = "https://api.semanticscholar.org/graph/v1"
USER_AGENT = f"scholar-cards/{__version__} (+https://github.com/zch6a/scholar-cards)"
FIELDS = "title,year,venue,publicationDate,externalIds,url,contexts"
PAGE = 1000
WAITS = (5.0, 20.0, 60.0, 120.0)  # Semantic Scholar answers 429 often without a key: wait and ask again

LABELS = ["contrasts with", "compares with", "builds on", "mentions"]
RULES = [
    # in this order: the first that matches decides
    ("contrasts with", re.compile(
        r"\b(?:however|unlike|in\s+contrast|contrary\s+to|although|whereas|fails?\s+to|failed\s+to|suffers?\s+from|limitations?|"
        r"drawbacks?|shortcomings?|lacks?|lacking|struggles?\s+(?:to|with)|unable\s+to|cannot|can\s*not|less\s+effective(?:ly)?|"
        r"is\s+limited|are\s+limited|problematic)\b", re.I)),
    ("compares with", re.compile(
        r"\b(?:baselines?|outperform(?:s|ed|ing)?|surpass(?:es|ed|ing)?|we\s+compare|compare[sd]?\s+(?:\w+\s+){0,4}(?:with|to|against)|"
        r"(?:our|we)\s+\w*\s*compare|versus|vs\.?|(?:better|worse|faster|slower|higher|lower|stronger|weaker)\s+than|"
        r"superior\s+to|state[\s-]of[\s-]the[\s-]art)\b|\d\s*±\s*\d", re.I)),
    ("builds on", re.compile(
        r"\b(?:we\s+(?:use|used|adopt|adopted|employ|employed|follow|followed|build|built|extend|extended|leverage|apply|applied|"
        r"utilize|initialize|fine-?tune|introduce|adapt|incorporate|integrate)|(?:this|our)\s+(?:paper|work|model|method)\s+(?:uses|adapts|adopts|builds)|"
        r"using|uses|based\s+on|built\s+(?:up)?on|builds?\s+(?:up)?on|on\s+top\s+of|follows?|following|as\s+in|pre-?trained|"
        r"fine-?tuned?|initiali[sz]ed\s+(?:with|from)|backbone|implementation\s+of|adapted\s+from|variant\s+of|composed\s+of)\b", re.I)),
]  # fmt: skip
BEATS = re.compile(r"\b(?:outperform(?:s|ed|ing)?|surpass(?:es|ed|ing)?|beats?|better\s+than|superior\s+to|improves?\s+(?:up)?on)\b", re.I)
OURS = re.compile(r"\b(?:our|ours|we|this\s+(?:work|paper|method|model))\b", re.I)


class S2Error(Exception):
    pass


Getter = Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]


def label(context: str) -> tuple[str, str]:
    """(label, the words that decided it) for one citing sentence.

    >>> label("Unlike BERT, our model reads the text left to right.")
    ('contrasts with', 'Unlike')
    >>> label("We fine-tune a pre-trained BERT-base encoder.")
    ('builds on', 'We fine-tune')
    >>> label("Our method outperforms BERT on all tasks.")
    ('compares with', 'outperforms')
    >>> label("A compact Mamba backbone is used rather than a U-Net [3].")
    ('builds on', 'backbone')
    >>> label("Transformers have been applied widely [3].")
    ('mentions', '')
    """
    for name, rx in RULES:
        m = rx.search(context)
        if m:
            return name, m.group(0)
    return "mentions", ""


def beats(context: str) -> bool:
    """Whether the citing paper says, in this sentence, that its own work does better.

    >>> beats("Our model outperforms BERT by 2 points."), beats("BERT outperforms earlier models."), beats("We use BERT.")
    (True, False, False)
    """
    m = BEATS.search(context)
    if m is None:
        return False
    return bool(OURS.search(context[: m.start()] + " " + context[m.end() : m.end() + 40]))


@dataclass
class Citing:
    id: str  # Semantic Scholar paper id
    title: str
    year: int | None
    venue: str
    date: str
    url: str
    doi: str = ""
    arxiv: str = ""
    contexts: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)  # one per context
    why: list[str] = field(default_factory=list)  # the words that decided each label
    claims_to_beat: bool = False

    @property
    def main(self) -> str:
        """The strongest label (contrasts > compares > builds on > mentions), or "" without contexts."""
        return min(self.labels, key=LABELS.index) if self.labels else ""


def _urlopen(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as r:  # noqa: S310 - the URL is the API's, built here
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b""
    except (OSError, http.client.HTTPException) as e:
        return 0, {}, str(e).encode()


def paper_id(who: str) -> str:
    """Semantic Scholar's form of a paper id: arXiv:…, DOI:…, or its own id.

    >>> paper_id("1810.04805"), paper_id("https://arxiv.org/abs/2106.09685v2"), paper_id("https://doi.org/10.18653/v1/N19-1423")
    ('arXiv:1810.04805', 'arXiv:2106.09685', 'DOI:10.18653/v1/N19-1423')
    """
    w = who.strip()
    if m := re.search(r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:)?(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?$", w, re.I):
        return f"arXiv:{m.group(1)}"
    if m := re.search(r"(?:doi\.org/|doi:)?(10\.\d{4,9}/\S+)$", w, re.I):
        return f"DOI:{m.group(1)}"
    if re.fullmatch(r"[0-9a-f]{40}", w):
        return w
    if re.fullmatch(r"(?:arXiv|DOI|CorpusId|ACL|PMID):\S+", w):
        return w
    raise S2Error(f"{who!r} is not an arXiv id, a DOI or a Semantic Scholar paper id")


class Client:
    def __init__(self, key: str | None = None, get: Getter | None = None, sleep: Callable[[float], None] | None = None) -> None:
        self.key = key if key is not None else os.environ.get("S2_API_KEY", "")
        self._get = get or (lambda url, headers: _urlopen(url, headers))  # looked up when called (the tests replace it)
        self._sleep = sleep or (lambda seconds: time.sleep(seconds))

    def get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = API + path + "?" + urllib.parse.urlencode(params)
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.key:
            headers["x-api-key"] = self.key
        for wait in (*WAITS, None):
            status, _, body = self._get(url, headers)
            if status in (0, 429) or status >= 500:
                if wait is None:
                    break
                self._sleep(wait)
                continue
            if status == 404:
                raise S2Error(f"Semantic Scholar has no paper {path.split('/')[2]}")
            if status != 200:
                raise S2Error(f"Semantic Scholar answered {status}: {body[:200].decode('utf-8', 'replace')}")
            data = json.loads(body)
            if not isinstance(data, dict):
                raise S2Error("Semantic Scholar's answer is not a record")
            return data
        raise S2Error("Semantic Scholar kept answering 429 or could not be reached: try later, or set S2_API_KEY (free)")

    def paper(self, pid: str) -> dict[str, Any]:
        return self.get(f"/paper/{urllib.parse.quote(pid, safe=':/')}", {"fields": "title,year,citationCount,url"})

    def citations(self, pid: str, limit: int = 5000) -> list[Citing]:
        out: list[Citing] = []
        offset = 0
        while offset < limit:
            data = self.get(f"/paper/{urllib.parse.quote(pid, safe=':/')}/citations",
                            {"fields": FIELDS, "limit": str(min(PAGE, limit - offset)), "offset": str(offset)})  # fmt: skip
            rows = data.get("data") or []
            out += [c for c in (citing(r) for r in rows) if c]
            if "next" not in data or not rows:
                break
            offset = int(data["next"])
        return out


def citing(row: dict[str, Any]) -> Citing | None:
    p = row.get("citingPaper") or {}
    if not p.get("paperId") or not p.get("title"):
        return None
    ids = p.get("externalIds") or {}
    contexts = [re.sub(r"\s+", " ", c).strip() for c in (row.get("contexts") or []) if c and c.strip()]
    labelled = [label(c) for c in contexts]
    return Citing(
        id=p["paperId"], title=re.sub(r"\s+", " ", p["title"]).strip(), year=p.get("year"), venue=p.get("venue") or "",
        date=p.get("publicationDate") or (str(p["year"]) if p.get("year") else ""), url=p.get("url") or "",
        doi=ids.get("DOI") or "", arxiv=ids.get("ArXiv") or "", contexts=contexts,
        labels=[x[0] for x in labelled], why=[x[1] for x in labelled], claims_to_beat=any(beats(c) for c in contexts),
    )  # fmt: skip


def load_state(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except (OSError, ValueError) as e:
        raise S2Error(f"{path}: not a state file ({e.__class__.__name__})") from e
    if not isinstance(data, dict) or not isinstance(data.get("seen"), list):
        raise S2Error(f'{path}: not a state file (no "seen" list)')
    return set(map(str, data["seen"]))


def save_state(path: Path, pid: str, seen: set[str], checked: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tool": "scholar-cards cited", "paper": pid, "checked": checked, "seen": sorted(seen)}, indent=1) + "\n",
                    encoding="utf-8")  # fmt: skip


def summary(items: list[Citing]) -> dict[str, int]:
    with_contexts = [c for c in items if c.contexts]
    out = {"citing papers": len(items), "with contexts": len(with_contexts)}
    for name in LABELS:
        out[name] = sum(c.main == name for c in with_contexts)
    out["claims to beat it"] = sum(c.claims_to_beat for c in items)
    return out


def _order(items: list[Citing]) -> list[Citing]:
    return sorted(items, key=lambda c: (c.date or "", c.title), reverse=True)


def text(title: str, items: list[Citing], total: int, new_only: bool, contexts: int = 2) -> str:
    s = summary(items)
    head = f"{title}: {s['citing papers']} {'new ' if new_only else ''}citing paper(s)"
    if not new_only and total and total != len(items):
        head += f" of {total:,} counted by Semantic Scholar"
    out = [head, f"  with the sentences that cite it: {s['with contexts']}; " + ", ".join(f"{k} {s[k]}" for k in LABELS) +
           f"; claims to beat it: {s['claims to beat it']}", ""]  # fmt: skip
    beaters = [c for c in items if c.claims_to_beat]
    if beaters:
        out.append("Claims to beat it:")
        out += [f"  {c.date[:10]}  {c.title[:100]}" for c in _order(beaters)[:15]]
        out.append("")
    for c in _order(items):
        tag = f"[{c.main}]" if c.main else "[no context]"
        where = f" · {c.venue}" if c.venue else ""
        out.append(f"{c.date[:10]:10}  {tag:17} {c.title[:110]}{where}")
        for ctx, lab, why in list(zip(c.contexts, c.labels, c.why, strict=True))[:contexts]:
            shown = ctx if len(ctx) <= 220 else ctx[:217] + "..."
            out.append(f"            “{shown}”" + (f"  ({lab}: {why})" if why else ""))
        if c.url:
            out.append(f"            {c.url}")
    return "\n".join(out) + "\n"


def markdown(title: str, items: list[Citing], new_only: bool) -> str:
    if not items:
        return f"No {'new ' if new_only else ''}citations of {title}.\n"
    out = [
        f"### {'New citations' if new_only else 'Citations'} of {title} ({len(items)})",
        "",
        "| Date | Paper | How | What it says |",
        "|---|---|---|---|",
    ]
    for c in _order(items):
        say = (c.contexts[0] if c.contexts else "").replace("|", "\\|")
        say = say if len(say) <= 200 else say[:197] + "..."
        how = (c.main or "—") + (" · claims to beat it" if c.claims_to_beat else "")
        name = c.title.replace("|", "\\|")[:100]
        out.append(f"| {c.date[:10]} | [{name}]({c.url}) | {how} | {say} |")
    return "\n".join(out) + "\n"


def to_json(pid: str, title: str, items: list[Citing], total: int) -> str:
    payload = {"tool": "scholar-cards cited", "version": __version__, "paper": pid, "title": title, "cited_by_count": total,
               "summary": summary(items), "citing": [asdict(c) | {"main": c.main} for c in _order(items)],
               "source": "Semantic Scholar Academic Graph API (https://api.semanticscholar.org)"}  # fmt: skip
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
