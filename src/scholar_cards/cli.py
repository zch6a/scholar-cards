"""scholar-cards: a researcher's numbers as SVG cards for a homepage or a GitHub profile.

scholar-cards A5023888391 -o cards/                 fetch from OpenAlex, save scholar.json, write the cards
scholar-cards 0000-0002-1825-009X -o cards/         the same by ORCID
scholar-cards search "Ada Lovelace"                 find the author record (OpenAlex IDs, ORCIDs, institutions, counts)
scholar-cards --snapshot cards/scholar.json -o cards/   render again from a snapshot, without the network

Set OPENALEX_API_KEY for a higher daily budget (it is sent as a header; never needed for one profile).
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from . import __version__
from .model import Scholar
from .openalex import ORCID, Client, OpenAlexError
from .svg import CARDS, THEMES, render


def fetch(who: str, client: Client, top: int = 5, today: str | None = None) -> Scholar:
    """The scholar from OpenAlex: the author record (citations, h-index, per-year counts) and their most cited works."""
    author = client.author(who)
    works = client.top_works(str(author.get("id") or ""), top) if top else []
    return Scholar.from_openalex(author, works, retrieved=today or dt.date.today().isoformat(), sources=list(client.requested))


def write_cards(s: Scholar, out: Path, cards: list[str], themes: list[str], lang: str, top: int = 5) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for card in cards:
        for theme in themes:
            path = out / (f"{card}.svg" if len(themes) == 1 else f"{card}-{theme}.svg")
            path.write_text(render(card, s, theme, lang, top), encoding="utf-8")
            written.append(path)
    return written


def _search(name: str, client: Client) -> int:
    found = client.search(name)
    if not found:
        print(f"scholar-cards: no author found for {name!r}", file=sys.stderr)
        return 1
    for a in found:
        inst = ", ".join(i.get("display_name", "") for i in (a.get("last_known_institutions") or [])[:2])
        short = str(a.get("id", "")).rsplit("/", 1)[-1]
        orcid = "ORCID " + str(a["orcid"]).rsplit("/", 1)[-1] if a.get("orcid") else "no ORCID"
        print(f"{short:14} {a.get('display_name', '')}  ·  {orcid}  ·  {a.get('works_count', 0)} works, "
              f"{a.get('cited_by_count', 0)} citations  ·  {inst}")  # fmt: skip
    print("\nSeveral records can be the same person (OpenAlex splits some profiles): pick the one with your ORCID, or the largest.")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="scholar-cards", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="exit status: 0 done, 1 nothing found, 2 an error (bad ID, OpenAlex unreachable, bad snapshot)")  # fmt: skip
    ap.add_argument("who", nargs="?", metavar="AUTHOR", help="an OpenAlex author ID (A…) or an ORCID; or: search NAME")
    ap.add_argument("name", nargs="?", help=argparse.SUPPRESS)
    ap.add_argument("-o", "--out", type=Path, default=Path("."), help="the folder for the cards and scholar.json (default: here)")
    ap.add_argument("--cards", default="stats,works,citations", help="which cards: stats, works, citations (default: all)")
    ap.add_argument("--theme", default="auto", help="auto (follows the reader's system setting), light, dark, or both: light,dark (default auto)")
    ap.add_argument("--lang", choices=["en", "zh"], default="en", help="the cards' labels (default en)")
    ap.add_argument("--top", type=int, default=5, help="how many papers on the works card (default 5)")
    ap.add_argument("--snapshot", type=Path, help="render from this scholar.json instead of fetching")
    ap.add_argument("--version", action="version", version=f"scholar-cards {__version__}")
    args = ap.parse_args(argv)

    cards = [c.strip() for c in args.cards.split(",") if c.strip()]
    themes = [t.strip() for t in args.theme.split(",") if t.strip()]
    if not cards:
        ap.error(f"--cards names no card; the cards are {', '.join(CARDS)}")
    if not themes:
        ap.error(f"--theme names no theme; the themes are auto, {', '.join(THEMES)}")
    if not 1 <= args.top <= 50:
        ap.error("--top is from 1 to 50")
    if args.name and args.who != "search":
        ap.error(f"one author at a time (got also {args.name!r}); a name to look up goes after search")
    if bad := [c for c in cards if c not in CARDS]:
        ap.error(f"unknown card(s) {', '.join(bad)}; the cards are {', '.join(CARDS)}")
    if bad := [t for t in themes if t not in (*THEMES, "auto")]:
        ap.error(f"unknown theme(s) {', '.join(bad)}; the themes are auto, {', '.join(THEMES)}")
    try:
        if args.who == "search":
            if not args.name:
                ap.error('search needs a name: scholar-cards search "Ada Lovelace"')
            return _search(args.name, Client())
        if args.snapshot:
            scholar = Scholar.load(args.snapshot)
        elif args.who:
            scholar = fetch(args.who, Client(), args.top)
            short = scholar.id.rsplit("/", 1)[-1]
            print(f"scholar-cards: fetched {scholar.name} ({short}): {scholar.works_count} works, {scholar.cited_by_count} citations"
                  + (f", ORCID {scholar.orcid.rsplit('/', 1)[-1]}" if scholar.orcid else ""), file=sys.stderr)  # fmt: skip
            asked = ORCID.search(args.who.strip().rstrip("/"))
            if asked and not scholar.orcid.upper().endswith(asked.group(1).upper()):
                print(f"scholar-cards: warning: OpenAlex gave this record for ORCID {asked.group(1)}, but the record's own ORCID is "
                      f"{scholar.orcid.rsplit('/', 1)[-1] or 'none'}: check it is you (scholar-cards search NAME)", file=sys.stderr)  # fmt: skip
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / "scholar.json").write_text(scholar.to_json(), encoding="utf-8")
        else:
            ap.error("give an author (an OpenAlex ID or an ORCID), search NAME, or --snapshot FILE")
        for path in write_cards(scholar, args.out, cards, themes, args.lang, args.top):
            print(f"scholar-cards: wrote {path.as_posix()}")
    except OpenAlexError as e:
        print(f"scholar-cards: {e}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as e:
        print(f"scholar-cards: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
