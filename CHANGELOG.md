# Changelog

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
