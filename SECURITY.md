# Security

## What it does

- **Talks only to OpenAlex** (`api.openalex.org`), over HTTPS, with a User-Agent naming the tool, not the user.
- **The API key**, if any, comes from `OPENALEX_API_KEY` and goes in the `Authorization` header: never in a URL, a
  card, the snapshot or a log line.
- **Cards are inert**: SVG with no scripts, no external fonts, images or links; every text from OpenAlex (names,
  titles, venues) is XML-escaped; each card's CSS is scoped to its own id.
- **The GitHub Action** runs the tool at the action's own ref and needs no write access; the recommended workflow
  commits the cards in a separate job that runs nothing but git.

## What it does not protect against

- **Wrong data at OpenAlex** (a paper attributed to the wrong person): the cards show what OpenAlex has.

## Reporting a vulnerability

Please open a private security advisory on GitHub (Security → Report a vulnerability) rather than a public issue.
