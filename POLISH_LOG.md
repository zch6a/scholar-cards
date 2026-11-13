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

### 2026-11-13 — polishing round 1

**Real records** (keyless, a handful of requests; cards to a temporary folder, deleted after): a name in Chinese
characters, ORCID's own example ID, a very large record, a five-paper record with no citations. Found:

- OpenAlex's data is wrong in ways the tool should show, not hide: the Chinese-name search returned a record whose
  "name" is seven people's names, and ORCID's example ID led to someone else's record. `fetch` now prints whom it
  got (name, ID, works, citations, the record's ORCID), and warns when the record's ORCID is not the one asked.
- OpenAlex leaves out years with nothing counted, so the bars skipped them and the years were unevenly spaced; an
  all-zero chart was empty. Missing years are zeros now, up to the snapshot's year, and an empty chart says "No
  citations counted yet" (or "in these years", when the author has citations before them).

**Independent review** (11 confirmed, all fixed, tests in `tests/test_review_round1.py`):

1. A control character (or a lone surrogate) in a name, title or venue, as PDF-extracted titles carry, made every card
   unparseable (or the write fail): characters XML cannot hold are removed.
2. `--top N` never drew more than five papers: the works card is drawn with N.
3. A malformed snapshot crashed with a traceback (extra keys, missing fields, a string format number, nulls): exit 2
   with "not a valid scholar-cards snapshot"; unknown keys are ignored.
4. `search` did not show the ORCID it tells you to pick by: it does.
5. `--top 0`, negative or over 50 were taken silently: 1 to 50.
6. A `null` or list body, or a connection cut mid-answer, escaped as tracebacks; a non-JSON body gave a bare message.
   Now OpenAlex errors naming the URL; network failures are retried like a 5xx.
7. 999,950 printed as "1000.0k": "1.0M".
8. "No citations counted yet" beside a stats card with citations (all before the last ten years): the other message.
9. `--cards ","` wrote nothing and exited 0: an error.
10. IDs matched anywhere in the text (`MA123`, `https://example.com/A5`, `foo0000-…`): whole matches only, with the
    OpenAlex and ORCID URL forms and `orcid:`.
11. An extra argument was ignored (`scholar-cards A1 junk`): an error.

From its "plausible" list: `Retry-After` is read case-insensitively (real answers use lower-case header names);
capitals and digits count wider when cutting titles; the README says `auto` follows the reader's system setting and
shows the `<picture>` form for GitHub's own theme, says the commit job's paths follow `out`, and that a commit comes
each run (the date changes).

Tests: 48 (were 31), Python 3.10 and 3.13; ruff, mypy clean.

Next: round 2.

### 2026-11-13 — polishing round 2

Round 1's CI was green on every job. `--help` brought up to date (search shows ORCIDs; `auto` follows the reader's
system setting); the wheel holds only the package, the sdist no images.

**Second independent review** (accessibility, contrast, embedding, rendering edges; 10 confirmed, all fixed, tests in
`tests/test_review_round2.py`):

1. Round 1's snapshot fix was partial: a field of the wrong type (`"cited_by_count": "6088"`, `"name": 123`, a null
   title) still crashed, with exit 1. Every field is now checked (text, whole numbers of 0 or more, a mean of 0 or
   more), exit 2 with what is wrong; a snapshot saved with a BOM loads.
2. All-negative counts drew a bar over the title: counts from the API are at least 0, a snapshot's must be.
3. Wide letters (W, M) overflowed the card and ran into the citation count: wider estimates (W and M 0.95 em,
   capitals 0.72, bold 8% more) and more room beside the number.
4. Contrast: the light title was 3.9:1, the faded current-year bar 1.8:1. Now a darker blue (5.2:1), muted text
   6.2:1, and the partial bar outlined in the bar colour (its outline 5.2:1) as well as faded. A test checks WCAG AA.
5. Screen readers got only the card's title: each card has a `<desc>` with every number (or each paper, or each
   year), `aria-labelledby` the title and the description.
6. The two-year mean printed "3" or "6.40": always two decimals; counts are whole.
7. Bidi: a Hebrew name's parentheses and an Arabic title's ellipsis landed on the wrong side: names, titles, venues
   and institutions are isolated (U+2068 … U+2069).
8. Cutting split an emoji joined by ZWJ, or a letter from its accent: never inside a cluster.
9. Forty years of bars ran their labels together: a label every few years, counted from the last.
10. The cards had no language: `xml:lang` (en, zh).

Also from its list: the README's recipe has a concurrency group (a manual run cannot race the weekly one), clears the
old cards before the new ones (a theme dropped leaves no stale files) and commits deletions; for al-folio, whose
dark switch does not change the reader's system setting, it suggests a fixed theme.

Tests: 65 (were 48), Python 3.10 and 3.13; ruff, mypy clean.

Next: round 3.
