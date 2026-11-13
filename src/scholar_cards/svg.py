"""The cards, as self-contained SVG (no fonts, scripts or images fetched): the numbers, the most cited papers, and
citations per year. Themes: light, dark, or auto (follows the reader's colour scheme). Labels in English or Chinese."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from xml.sax.saxutils import escape as _escape

from .model import Scholar

WIDTH = 495
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
THEMES = {
    "light": {"bg": "#ffffff", "border": "#d0d7de", "title": "#0969da", "text": "#424a53", "muted": "#57606a", "bar": "#0969da"},
    "dark": {"bg": "#0d1117", "border": "#30363d", "title": "#58a6ff", "text": "#c9d1d9", "muted": "#8b949e", "bar": "#58a6ff"},
}
LABELS = {
    "en": {"citations": "Citations", "h_index": "h-index", "i10_index": "i10-index", "works": "Works", "mean2": "2-year mean citedness",
           "top": "Most cited papers", "per_year": "Citations per year", "source": "OpenAlex", "as_of": "as of",
           "cited": "cited", "so_far": "so far", "none_yet": "No citations counted yet",
           "none_recent": "No citations counted in these years"},
    "zh": {"citations": "总被引", "h_index": "h 指数", "i10_index": "i10 指数", "works": "论文数", "mean2": "近两年篇均被引",
           "top": "高被引论文", "per_year": "逐年被引", "source": "OpenAlex", "as_of": "数据日期", "cited": "被引", "so_far": "截至目前",
           "none_yet": "尚无被引记录", "none_recent": "这些年份没有被引记录"},
}  # fmt: skip


# characters XML 1.0 does not allow (controls, lone surrogates, U+FFFE/U+FFFF): titles taken from PDFs carry some
_NOT_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def clean(s: str) -> str:
    r"""Text with the characters XML cannot hold removed (a control character makes the whole card unreadable).

    >>> clean("Title\x0bwith\x00controls\ud800")
    'Titlewithcontrols'
    """
    return _NOT_XML.sub("", s)


def escape(s: str, entities: dict[str, str] | None = None) -> str:
    return _escape(clean(s), entities or {})


def number(n: float | None) -> str:
    """A count as cards print it.

    >>> number(987), number(12345), number(1_234_567), number(None), number(999_950)
    ('987', '12.3k', '1.2M', '–', '1.0M')
    """
    if n is None:
        return "–"
    if abs(n) >= 999_950:  # 999,950 would round to "1000.0k"
        return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 10_000:
        return f"{n / 1000:.1f}k"
    return f"{n:,.0f}"


def mean(v: float | None) -> str:
    """A mean, always with two decimals.

    >>> mean(6.4), mean(3), mean(None)
    ('6.40', '3.00', '–')
    """
    return "–" if v is None else f"{v:.2f}"


def _em(c: str) -> float:
    if unicodedata.combining(c) or c in "\u200d\ufe0f\u2068\u2069":
        return 0.0
    if unicodedata.east_asian_width(c) in "WF":
        return 1.0
    if c in "WMmw@%":
        return 0.95
    if c.isupper():
        return 0.72
    return 0.6 if c.isdigit() else 0.56


def text_width(s: str, size: float, bold: bool = False) -> float:
    """About how wide a line of text is, erring wide (a title cut a little early beats one running into the number
    beside it, in whatever font the reader has): wide (CJK) characters one em, W and M 0.95, capitals 0.72, digits
    0.6, the rest 0.56; bold 8% wider."""
    return sum(_em(c) for c in s) * size * (1.08 if bold else 1.0)


def clip(s: str, size: float, width: float, bold: bool = False) -> str:
    """The text, cut with an ellipsis to fit `width`, never inside a character cluster (a letter and its accent, an
    emoji joined by ZWJ).

    >>> clip("A very long title about attention", 10, 80)  # 5.6 px a character, a capital 7.2
    'A very long t…'
    >>> clip("xxxxxxxxe" + chr(0x301) + "tude", 10, 60) == "xxxxxxxxe" + chr(0x301) + "…"  # the accent stays with its letter
    True
    """
    if text_width(s, size, bold) <= width:
        return s
    n = 0
    while n < len(s) and text_width(s[: n + 1] + "…", size, bold) <= width:
        n += 1
    while 0 < n < len(s) and (unicodedata.combining(s[n]) or s[n] in "\u200d\ufe0f" or s[n - 1] == "\u200d"):
        n -= 1  # back out of a cluster
    return s[:n].rstrip() + "…"


def iso(s: str) -> str:
    """Text isolated for bidi (U+2068 … U+2069): a Hebrew or Arabic name lays out right to left, and its parentheses and
    ellipsis stay where they belong, inside a left-to-right card."""
    return f"\u2068{s}\u2069"


def _style(theme: str, scope: str) -> str:
    """The card's CSS, every rule under the card's own id: several cards inlined in one page must not restyle each
    other (a dark card next to a light one)."""
    s = f"#{scope}"

    def rules(t: dict[str, str]) -> str:
        return (f"{s} .bg{{fill:{t['bg']};stroke:{t['border']}}}{s} .title{{fill:{t['title']}}}{s} .text{{fill:{t['text']}}}"
                f"{s} .muted{{fill:{t['muted']}}}{s} .bar{{fill:{t['bar']}}}"
                f"{s} .partial{{fill:{t['bar']};fill-opacity:0.35;stroke:{t['bar']};stroke-width:1.5}}")  # fmt: skip

    base = f"{s} text{{font-family:{FONT}}}{s} .title{{font-size:18px;font-weight:600}}{s} .text{{font-size:14px}}{s} .muted{{font-size:11px}}"
    if theme == "auto":
        return base + rules(THEMES["light"]) + "@media (prefers-color-scheme: dark){" + rules(THEMES["dark"]) + "}"
    return base + rules(THEMES[theme])


def _frame(height: int, theme: str, title: str, body: list[str], footer: str, desc: str = "", lang: str = "en") -> str:
    """The card around its body: the title shown and read out, a description with every number (screen readers get
    the values, not only the title), the language, the CSS under the card's own id."""
    scope = "sc-" + hashlib.sha1("\n".join([theme, title, footer, *body]).encode()).hexdigest()[:10]
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" '
        f'role="img" id="{scope}" xml:lang="{lang}" aria-labelledby="{scope}-t {scope}-d">',
        f'<title id="{scope}-t">{escape(title)}</title>',
        f'<desc id="{scope}-d">{escape(desc + (". " if desc else "") + footer)}</desc>',
        f"<style>{_style(theme, scope)}</style>",
        f'<rect class="bg" x="0.5" y="0.5" rx="4.5" width="{WIDTH - 1}" height="{height - 1}"/>',
        f'<text class="title" x="25" y="35">{escape(iso(clip(title, 18, WIDTH - 50, bold=True)))}</text>',
        *body,
        f'<text class="muted" x="25" y="{height - 14}">{escape(footer)}</text>',
        "</svg>",
    ]) + "\n"  # fmt: skip


def _footer(s: Scholar, lang: str) -> str:
    words = LABELS[lang]
    return f"{words['source']} · {words['as_of']} {s.retrieved}" if s.retrieved else words["source"]


def stats_card(s: Scholar, theme: str = "auto", lang: str = "en") -> str:
    """The numbers: citations, h-index, i10-index, works, two-year mean citedness; the institution under the name."""
    words = LABELS[lang]
    rows = [(words["citations"], number(s.cited_by_count)), (words["h_index"], number(s.h_index)), (words["i10_index"], number(s.i10_index)),
            (words["works"], number(s.works_count)), (words["mean2"], mean(s.mean_citedness_2yr))]  # fmt: skip
    body = []
    y = 62
    if s.institution:
        body.append(f'<text class="muted" x="25" y="54">{escape(iso(clip(s.institution, 11, WIDTH - 50)))}</text>')
        y = 74
    for label, value in rows:
        body.append(f'<text class="text" x="25" y="{y + 14}">{escape(label)}</text>')
        body.append(f'<text class="text" x="{WIDTH - 25}" y="{y + 14}" text-anchor="end" font-weight="600">{escape(value)}</text>')
        y += 26
    desc = "; ".join(f"{label} {value}" for label, value in rows) + (f"; {s.institution}" if s.institution else "")
    return _frame(y + 34, theme, s.name, body, _footer(s, lang), desc, lang)


def works_card(s: Scholar, theme: str = "auto", lang: str = "en", n: int = 5) -> str:
    """The most cited papers: title, venue and year, citations."""
    words = LABELS[lang]
    body = []
    y = 62
    for w in s.top_works[:n]:
        cited = number(w.cited_by_count)
        room = WIDTH - 50 - text_width(cited, 14, bold=True) - 16
        body.append(f'<text class="text" x="25" y="{y + 14}">{escape(iso(clip(w.title, 14, room)))}</text>')
        body.append(f'<text class="text" x="{WIDTH - 25}" y="{y + 14}" text-anchor="end" font-weight="600">{escape(cited)}</text>')
        meta = " · ".join(x for x in (w.venue, str(w.year) if w.year else "") if x)
        body.append(f'<text class="muted" x="25" y="{y + 30}">{escape(iso(clip(meta, 11, WIDTH - 50)))}</text>')
        y += 42
    if not s.top_works:
        body.append(f'<text class="muted" x="25" y="{y + 14}">–</text>')
        y += 26
    desc = "; ".join(
        f"{w.title} ({', '.join(x for x in (w.venue, str(w.year or '')) if x)}): {w.cited_by_count} {words['cited']}" for w in s.top_works[:n]
    )
    return _frame(y + 34, theme, f"{words['top']} · {s.name}", body, _footer(s, lang), desc, lang)


def citations_card(s: Scholar, theme: str = "auto", lang: str = "en", years: int = 10) -> str:
    """Citations per year as bars: the last `years` years up to the snapshot's (OpenAlex leaves out years with nothing
    counted; they are zeros here, so that the years are evenly spaced), the largest labelled."""
    words = LABELS[lang]
    current = int(s.retrieved[:4]) if s.retrieved[:4].isdigit() else None  # its bar is faded: the year is not over
    data = _year_range(s.counts_by_year, current, years)
    top, height_bars, left, right = 62, 110, 25, WIDTH - 25
    body = []
    if data and not any(c for _, _, c in data):
        message = words["none_yet"] if not s.cited_by_count else words["none_recent"]
        body.append(f'<text class="muted" x="{WIDTH / 2:.0f}" y="{top + height_bars / 2:.0f}" text-anchor="middle">{escape(message)}</text>')
    if data:
        peak = max(0, *(c for _, _, c in data)) or 1
        step = (right - left) / len(data)
        bar = max(4.0, step * 0.62)
        every = max(1, math.ceil(22 / step))  # a label every few years when the bars are narrow, counted from the last
        for i, (year, _, cites) in enumerate(data):
            h = 0 if cites == 0 else max(1.5, height_bars * cites / peak)
            x = left + i * step + (step - bar) / 2
            body.append(
                "<rect"
                + ("" if year == current else ' class="bar"')
                + f' x="{x:.1f}" y="{top + height_bars - h:.1f}" width="{bar:.1f}" height="{h:.1f}" rx="2"'
                + (' class="bar partial"' if year == current else "")
                + f"><title>{year}: {cites}{' (' + words['so_far'] + ')' if year == current else ''}</title></rect>"
            )
            label = f"{year % 100:02d}" + ("*" if year == current else "")
            if (len(data) - 1 - i) % every == 0:
                body.append(f'<text class="muted" x="{x + bar / 2:.1f}" y="{top + height_bars + 16}" text-anchor="middle">{label}</text>')
            if cites == peak and cites:
                body.append(
                    f'<text class="muted" x="{x + bar / 2:.1f}" y="{top + height_bars - h - 5:.1f}" text-anchor="middle">'
                    f"{escape(number(cites))}</text>"
                )
    else:
        body.append(f'<text class="muted" x="25" y="{top + 14}">–</text>')
    footer = _footer(s, lang) + (f" · *{words['so_far']}" if data and current == data[-1][0] else "")
    desc = "; ".join(f"{y}: {c}" + (f" ({words['so_far']})" if y == current else "") for y, _, c in data)
    return _frame(math.ceil(top + height_bars + 58), theme, f"{words['per_year']} · {s.name}", body, footer, desc, lang)


def _year_range(counts: list[tuple[int, int, int]], current: int | None, years: int) -> list[tuple[int, int, int]]:
    """The last `years` years of counts, missing years as zeros, ending at the snapshot's year (or the last counted).

    >>> _year_range([(2019, 1, 5), (2022, 2, 7)], 2023, 4)
    [(2020, 0, 0), (2021, 0, 0), (2022, 2, 7), (2023, 0, 0)]
    >>> _year_range([(2019, 1, 5)], None, 10)
    [(2019, 1, 5)]
    """
    if not counts:
        return []
    by_year = {y: (y, w, c) for y, w, c in counts}
    end = max(current or 0, max(by_year))
    start = max(min(by_year), end - years + 1)
    return [by_year.get(y, (y, 0, 0)) for y in range(start, end + 1)]


CARDS = {"stats": stats_card, "works": works_card, "citations": citations_card}


def render(card: str, s: Scholar, theme: str = "auto", lang: str = "en", top: int = 5) -> str:
    """One card by name; `top` papers on the works card."""
    return works_card(s, theme, lang, top) if card == "works" else CARDS[card](s, theme, lang)
