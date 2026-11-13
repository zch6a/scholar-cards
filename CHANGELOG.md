# Changelog

## 0.1.0

The first release: a researcher's numbers from OpenAlex as SVG cards.

- **Fetches** an author by OpenAlex ID or ORCID (and lists candidates by name, never picking one), with their most
  cited works; keyless, or with `OPENALEX_API_KEY` as a header; waits and retries when told to.
- **Three cards**: the numbers (citations, h-index, i10-index, works, two-year mean citedness), the most cited
  papers, citations per year (the current year marked partial); light, dark or auto theme; English or Chinese.
- **A snapshot** (`scholar.json`) with the date and the API URLs, to render again offline.
- **A GitHub Action** and a two-job workflow recipe (read-only render, git-only commit).
- No dependencies.
