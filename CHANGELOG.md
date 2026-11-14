# Changelog

## 0.2.0 — 2026-11-14

- **`scholar-cards cited PAPER`**: who cites a paper and what they say. The citing papers and the sentences that cite
  it come from Semantic Scholar's public API (the paper's id only; `S2_API_KEY` optional; 429 answers retried after
  5, 20, 60 and 120 s). Each sentence is labelled by rules (builds on, compares with, contrasts with, mentions) with
  the deciding word; papers that claim, in their own voice, to beat the cited one are listed. `--new` with a state
  file lists only new citing papers; `--format text|markdown|json`, `--fail-on-new` for a weekly issue.
- Measured on Mamba's first 1,000 citing papers: 759 with citing sentences; the labels matched a hand reading for 27
  of 40 sentences drawn at random.

## 0.1.1 — 2026-11-14

- The agent skill's frontmatter is valid YAML again: its description held a `: `, which YAML reads as a new key, so
  the whole frontmatter failed to parse and the skill loaded without its description (`claude plugin validate`
  reported it). The values are quoted now.

## 0.1.0

The first release: a researcher's numbers from OpenAlex as SVG cards for a homepage or a GitHub profile.

- **Fetches** an author by OpenAlex ID or ORCID (URLs too), with their most cited works; `search NAME` lists the
  candidate records with their ORCIDs and never picks one. It says whom it fetched, and warns when the record's ORCID
  is not the one asked (OpenAlex's data has such errors). Keyless, or with `OPENALEX_API_KEY` sent as a header;
  waits and retries on rate limits, outages and network failures.
- **Three cards**: the numbers (citations, h-index, i10-index, works, two-year mean citedness), the most cited
  papers, citations per year (missing years as zeros, the current year marked "so far"). Light, dark or auto theme;
  English or Chinese. Self-contained SVG: no scripts, fonts or images fetched; text escaped, characters XML cannot
  hold removed, bidi isolated, never cut inside a character cluster; WCAG AA colours; a description with every
  number for screen readers.
- **A snapshot** (`scholar.json`) with the date and the API URLs (never a key), to render again offline; checked
  strictly when read.
- **A GitHub Action** and a two-job workflow recipe (a read-only job renders, a job that runs only git commits),
  exercised in this repository's CI.
- Tested on real OpenAlex records of every shape; three independent reviews (28 defects found and fixed, each with a
  test). No dependencies.
