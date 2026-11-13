"""The cards, as self-contained SVG (no fonts, scripts or images fetched): the numbers, the most cited papers, and
citations per year. Themes: light, dark, or auto (follows the reader's colour scheme). Labels in English or Chinese."""

from __future__ import annotations

import hashlib
import math
import unicodedata
from xml.sax.saxutils import escape

from .model import Scholar

WIDTH = 495
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
THEMES = {
    "light": {"bg": "#ffffff", "border": "#e4e2e2", "title": "#2f80ed", "text": "#434d58", "muted": "#6a737d", "bar": "#2f80ed"},
    "dark": {"bg": "#0d1117", "border": "#30363d", "title": "#58a6ff", "text": "#c9d1d9", "muted": "#8b949e", "bar": "#58a6ff"},
}
LABELS = {
    "en": {"citations": "Citations", "h_index": "h-index", "i10_index": "i10-index", "works": "Works", "mean2": "2-year mean citedness",
           "top": "Most cited papers", "per_year": "Citations per year", "source": "OpenAlex", "as_of": "as of", "cited": "cited"},
    "zh": {"citations": "总被引", "h_index": "h 指数", "i10_index": "i10 指数", "works": "论文数", "mean2": "近两年篇均被引",
           "top": "高被引论文", "per_year": "逐年被引", "source": "OpenAlex", "as_of": "数据日期", "cited": "被引"},
}  # fmt: skip


def number(n: float | None) -> str:
    """A count as cards print it.

    >>> number(987), number(12345), number(1_234_567), number(None)
    ('987', '12.3k', '1.2M', '–')
    """
    if n is None:
        return "–"
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 10_000:
        return f"{n / 1000:.1f}k"
    return f"{n:,.0f}" if float(n).is_integer() else f"{n:.2f}"


def text_width(s: str, size: float) -> float:
    """About how wide a line of text is: wide (CJK) characters count as one em, the others as 0.55."""
    return sum(size if unicodedata.east_asian_width(c) in "WF" else 0.55 * size for c in s)


def clip(s: str, size: float, width: float) -> str:
    """The text, cut with an ellipsis to fit `width`.

    >>> clip("A very long title about attention", 10, 80)  # 5.5 px a character: 13 and the ellipsis
    'A very long t…'
    """
    if text_width(s, size) <= width:
        return s
    out = ""
    for c in s:
        if text_width(out + c + "…", size) > width:
            break
        out += c
    return out.rstrip() + "…"


def _style(theme: str, scope: str) -> str:
    """The card's CSS, every rule under the card's own id: several cards inlined in one page must not restyle each
    other (a dark card next to a light one)."""
    s = f"#{scope}"

    def rules(t: dict[str, str]) -> str:
        return (f"{s} .bg{{fill:{t['bg']};stroke:{t['border']}}}{s} .title{{fill:{t['title']}}}{s} .text{{fill:{t['text']}}}"
                f"{s} .muted{{fill:{t['muted']}}}{s} .bar{{fill:{t['bar']}}}")  # fmt: skip

    base = f"{s} text{{font-family:{FONT}}}{s} .title{{font-size:18px;font-weight:600}}{s} .text{{font-size:14px}}{s} .muted{{font-size:11px}}"
    if theme == "auto":
        return base + rules(THEMES["light"]) + "@media (prefers-color-scheme: dark){" + rules(THEMES["dark"]) + "}"
    return base + rules(THEMES[theme])


def _frame(height: int, theme: str, title: str, body: list[str], footer: str) -> str:
    scope = "sc-" + hashlib.sha1("\n".join([theme, title, footer, *body]).encode()).hexdigest()[:10]
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" '
        f'role="img" id="{scope}" aria-label="{escape(title, {chr(34): "&quot;"})}">',
        f"<title>{escape(title)}</title>",
        f"<style>{_style(theme, scope)}</style>",
        f'<rect class="bg" x="0.5" y="0.5" rx="4.5" width="{WIDTH - 1}" height="{height - 1}"/>',
        f'<text class="title" x="25" y="35">{escape(clip(title, 18, WIDTH - 50))}</text>',
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
            (words["works"], number(s.works_count)), (words["mean2"], number(s.mean_citedness_2yr))]  # fmt: skip
    body = []
    y = 62
    if s.institution:
        body.append(f'<text class="muted" x="25" y="54">{escape(clip(s.institution, 11, WIDTH - 50))}</text>')
        y = 74
    for label, value in rows:
        body.append(f'<text class="text" x="25" y="{y + 14}">{escape(label)}</text>')
        body.append(f'<text class="text" x="{WIDTH - 25}" y="{y + 14}" text-anchor="end" font-weight="600">{escape(value)}</text>')
        y += 26
    return _frame(y + 34, theme, s.name, body, _footer(s, lang))


def works_card(s: Scholar, theme: str = "auto", lang: str = "en", n: int = 5) -> str:
    """The most cited papers: title, venue and year, citations."""
    words = LABELS[lang]
    body = []
    y = 62
    for w in s.top_works[:n]:
        cited = f"{number(w.cited_by_count)}"
        body.append(f'<text class="text" x="25" y="{y + 14}">{escape(clip(w.title, 14, WIDTH - 50 - text_width(cited, 14) - 12))}</text>')
        body.append(f'<text class="text" x="{WIDTH - 25}" y="{y + 14}" text-anchor="end" font-weight="600">{escape(cited)}</text>')
        meta = " · ".join(x for x in (w.venue, str(w.year) if w.year else "") if x)
        body.append(f'<text class="muted" x="25" y="{y + 30}">{escape(clip(meta, 11, WIDTH - 50))}</text>')
        y += 42
    if not s.top_works:
        body.append(f'<text class="muted" x="25" y="{y + 14}">–</text>')
        y += 26
    return _frame(y + 34, theme, f"{words['top']} · {s.name}", body, _footer(s, lang))


def citations_card(s: Scholar, theme: str = "auto", lang: str = "en", years: int = 10) -> str:
    """Citations per year as bars (the last `years` years OpenAlex counts), the largest labelled."""
    words = LABELS[lang]
    data = s.counts_by_year[-years:]
    top, height_bars, left, right = 62, 110, 25, WIDTH - 25
    body = []
    if data:
        peak = max(c for _, _, c in data) or 1
        step = (right - left) / len(data)
        bar = max(4.0, step * 0.62)
        for i, (year, _, cites) in enumerate(data):
            h = 0 if cites == 0 else max(1.5, height_bars * cites / peak)
            x = left + i * step + (step - bar) / 2
            body.append(
                f'<rect class="bar" x="{x:.1f}" y="{top + height_bars - h:.1f}" width="{bar:.1f}" height="{h:.1f}" rx="2">'
                f"<title>{year}: {cites}</title></rect>"
            )
            body.append(f'<text class="muted" x="{x + bar / 2:.1f}" y="{top + height_bars + 16}" text-anchor="middle">{year % 100:02d}</text>')
            if cites == peak:
                body.append(
                    f'<text class="muted" x="{x + bar / 2:.1f}" y="{top + height_bars - h - 5:.1f}" text-anchor="middle">'
                    f"{escape(number(cites))}</text>"
                )
    else:
        body.append(f'<text class="muted" x="25" y="{top + 14}">–</text>')
    return _frame(math.ceil(top + height_bars + 58), theme, f"{words['per_year']} · {s.name}", body, _footer(s, lang))


CARDS = {"stats": stats_card, "works": works_card, "citations": citations_card}
