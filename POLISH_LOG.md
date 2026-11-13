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

### 2026-11-13 — the partial year

- The snapshot's own year is not over, so its bar read as a drop: it is faded, its label starred, its tooltip and the
  footer say "so far".

Tests: 30.

Next: the GitHub Action; README (English, Chinese) with demo images from a synthetic
profile; Skill; CI; the public repository.

### 2026-11-13 — the Action, CI, release

- `action.yml` (composite): an author or a snapshot in, the cards and scholar.json written to a folder; the key, if any,
  from an input meant for a secret, into the environment (a header, never a URL); the tool runs at the action's own
  ref. It commits nothing: the README's recipe will do that in a second job that runs no project code. Tried locally
  through Git Bash: with the example's snapshot it writes the six cards (light, dark); with neither input it stops
  with exit 2 and says why.
- `examples/scholar.json`: a made-up researcher (`scripts/make_example.py`, seeded), for CI, the README's images and
  tries without the network.
- CI: three systems × Python 3.10/3.13, and the action on the example. Release workflow as exp-tables' (the fixed one).

Tests: 31.

Next: README (English, Chinese) with the workflow recipe and demo images; Skill; SECURITY, CONTRIBUTING, CHANGELOG;
social card; the public repository.

### 2026-11-13 — the docs

- README (English, Chinese): what it is for, the example's cards (auto theme, so they follow GitHub's), `search` first
  (OpenAlex splits some people; the tool never picks), the options, the two-job workflow recipe (read-only render,
  git-only commit), what each number is and how it differs from Google Scholar's, limits.
- Skill (find the record with the user, never silently), SECURITY (only api.openalex.org; the key only in a header;
  inert SVG), CONTRIBUTING (module map), CHANGELOG; the social card from the example's dark cards.
- Found while writing them: rendering one theme writes plain names (`stats.svg`), so a dark run over the docs folder
  replaced the auto cards; the dark ones now go to `docs/dark/`. The sdist leaves out `docs/`.

Next: the public repository and CI; then the five rounds (reviews, real profiles, the workflow recipe run for real
in a test repository).

### 2026-11-13 — public

- Checked first: commits by zch6a with the noreply address, no attribution lines, no personal paths or names.
- https://github.com/zch6a/scholar-cards (public, main), description and topics. The first CI run is green: three
  systems × Python 3.10/3.13, and the action job on the example's snapshot.

Next: polishing round 1.
