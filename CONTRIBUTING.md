# Contributing

The most useful contributions are **cards that look wrong** somewhere (a site, a theme, a language) and **records
read wrongly** (with the OpenAlex author ID).

## Development

```bash
uv sync
uv run pytest -q          # no test reaches the network: OpenAlex is a fake transport in the tests
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

The example (`examples/scholar.json`, a made-up researcher) is made by `scripts/make_example.py`; the README's cards
by `uv run scholar-cards --snapshot examples/scholar.json -o docs`.

## Where things are

| | |
|---|---|
| `model.py` | `Scholar`, `Work`, from OpenAlex records; the snapshot |
| `openalex.py` | the API: author by ID or ORCID, top works, search; key, retries |
| `svg.py` | the cards, themes, labels |
| `cli.py` | the command line |
| `action.yml` | the GitHub Action |
