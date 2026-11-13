# Polish log

### 2026-11-13 — research and design

- **Others.** GitHub has many profile-stats cards (github-readme-stats and its action forks, user-statistician),
  all GitHub-only. A search found nothing that makes cards from a researcher's citation record; Google Scholar has no
  API (scraping it is against its terms and bot-checked), so the data comes from OpenAlex.
- **OpenAlex today** (its own docs, 2026-11): basic queries need no key (10 requests a second); a free key, sent as
  `Authorization: Bearer`, raises the daily budget and is needed for paging past the first page. One author record
  carries what the stats card needs (works, citations, h-index, i10-index, two-year mean citedness, citations per
  year, the last institution); one list call gives the most cited works. So a profile costs two calls and needs no
  key.
- **Design.**
  - CLI: `scholar-cards AUTHOR -o cards/` (an OpenAlex ID or an ORCID) fetches, saves `scholar.json` (the numbers
    with the date and the API URLs they came from, never a key) and writes the cards; `--snapshot` renders again
    without the network; `search NAME` lists author records, because OpenAlex splits some people into several and
    the tool must never pick one silently.
  - Cards: self-contained SVG (no fonts, scripts or images fetched): the numbers, the most cited papers, citations
    per year; themes light, dark, auto (follows the reader's colour scheme); English or Chinese labels.
  - To come: a GitHub Action for the user's own repository (a read-only job fetches and renders, a job that runs no
    project code commits the cards), the Skill, the README, then the five rounds.

### 2026-11-13 — the core

- `model.py`: `Scholar` and `Work` from OpenAlex records; the snapshot (JSON, versioned, refusing a newer format).
- `openalex.py`: author by OpenAlex ID or ORCID (URLs too), most cited works, search; the User-Agent names the tool,
  the key (from `OPENALEX_API_KEY`) goes in a header; waits and retries on 429 and 5xx (Retry-After honoured, three
  times), says what happened on 404 and the rest.
- `svg.py`: the three cards; numbers as 12.3k / 1.2M; titles cut to fit (wide characters counted wide); every CSS rule
  under the card's own id. Found while looking at them: inlined side by side, a light card restyled a dark one
  (shared class names); now scoped.
- `cli.py`: fetch, snapshot, render, search; exit 0 / 1 (nothing found) / 2 (error).
- Tried once against the live API (keyless): a well-known author's record and top works came back as expected, with
  the two URLs in the snapshot. To handle next: the current year is partial, and its bar looks like a drop.

Tests: 29 (a fake transport; none reaches the network). ruff, mypy clean.

Next: the partial current year; the GitHub Action; README (English, Chinese) with demo images from a synthetic
profile; Skill; CI; the public repository.
