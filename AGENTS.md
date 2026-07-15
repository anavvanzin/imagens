# AGENTS.md

## Cursor Cloud specific instructions

Mnemosyne Viva is a **static editorial site** (the public site for `iconocracia.com`).
There is no build/bundling step for the HTML/CSS/JS itself. See `README.md` for the
canonical file/directory overview.

### Services

- **Static site (only runnable service).** Served either by Vercel (`outputDirectory: site`)
  or locally by the Cloudflare Worker in `src/index.js`. For local development run the
  Worker with Miniflare:
  - `npx wrangler dev --port 8787` — serves the `site/` assets plus the Worker. Open
    `http://127.0.0.1:8787/` (homepage) and `/acervo` (collection grid).
  - The pinned wrangler is v3; it prints harmless warnings about being out-of-date and
    about the `compatibility_date` (2026-07-03) being newer than the runtime — the site
    serves fine regardless.
  - The Worker's `/api/exec` endpoint uses `@cloudflare/sandbox` (a Cloudflare
    *container* Durable Object built from `Dockerfile`). Containers require Docker, which
    is **not** available in this environment. This does **not** affect the editorial site
    or static asset serving — only that one sandbox API route is unavailable locally.

### Data generation (do this before demoing the acervo grid)

- `site/data/acervo.json` and `site/data/stats.json` are **generated** by
  `python3 scripts/build_data.py` from `site/data/corpus-data-enriched.json`. A fresh
  checkout ships `acervo.json` as an empty `[]` and a minimal `stats.json`, so the grid
  is empty until you run the build script (it regenerates ~95 items). These generated
  files are intentionally left untracked-in-spirit; avoid committing regenerated data.

### Validation (no unit/test suite exists)

- `python3 scripts/validate_acervo.py --json site/data/corpus-data-enriched.json --schema schemas/corpus-data-enriched.schema.json --report /tmp/report.md`
  validates JSON + JSON Schema, then checks every external image URL over the network.
  Schema validation uses `jsonschema` when installed (stdlib fallback otherwise). Some
  image URLs return 403/timeout from restricted networks — those are network/WAF issues,
  **not** code failures. Use `--retries 0 --timeout 5` for a fast run.
- There is no linter configured. CI is the GitHub workflows in `.github/workflows/`
  (`validate-acervo`, `performance-acervo`, `conflict-markers`).
