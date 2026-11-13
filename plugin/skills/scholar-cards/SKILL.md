---
name: scholar-cards
description: Make a researcher's citation cards with scholar-cards: citations, h-index, i10-index, most cited papers and citations per year from OpenAlex, as self-contained SVG for an academic homepage (al-folio, academicpages, Hugo) or a GitHub profile, and a GitHub workflow that refreshes them weekly. Use when the user wants their citation numbers on their homepage or profile, a badge or card of their scholarly impact, or their OpenAlex author ID.
license: MIT
compatibility: Needs Python 3.10+ and uv. Runs scholar-cards with uvx from GitHub (git+https://github.com/zch6a/scholar-cards) unless installed. Reaches only the OpenAlex API; no key needed.
metadata:
  homepage: https://github.com/zch6a/scholar-cards
---

# Citation cards with scholar-cards

```bash
uvx --from git+https://github.com/zch6a/scholar-cards scholar-cards search "Full Name"   # find the author record
uvx --from git+https://github.com/zch6a/scholar-cards scholar-cards A5023888391 -o cards/  # or an ORCID
```

- **Find the right record first.** `search` lists OpenAlex author records (ID, works, citations, institution).
  Several records can be the same person, and namesakes are common: show the user the candidates and let them
  choose (their ORCID settles it). Never pick one silently.
- The second command writes `stats.svg`, `works.svg`, `citations.svg` and `scholar.json` (numbers, date, the API
  URLs). Options: `--cards`, `--theme auto|light|dark` (or `light,dark`), `--lang en|zh`, `--top N`,
  `--snapshot scholar.json` to render again offline.
- For a homepage that stays current, give the user the two-job workflow from the README (a read-only job runs the
  action, a second job only commits); point `out` at a folder the site serves.
- The numbers are OpenAlex's, not Google Scholar's: say so if the user compares them; wrong attributions are fixed
  at OpenAlex, not here. An API key (`OPENALEX_API_KEY`) is optional; never put one in a file or a URL.
