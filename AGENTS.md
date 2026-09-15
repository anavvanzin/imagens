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
  - **Auth:** `POST /api/exec` requires `Authorization: Bearer <EXEC_API_KEY>`. Set the
    secret locally via `.dev.vars` (see `.dev.vars.example`) and in production with
    `npx wrangler secret put EXEC_API_KEY`. If the secret is unset, the route returns
    `503` (fail closed). Static assets stay public.

### Data generation

- `site/data/publication.json` is the editorial source of truth. It pins one public
  commit of `anavvanzin/iconocracy-corpus` and stores publication decisions, aliases,
  image rights, public analysis, and constellations.
- `site/data/acervo.json`, `stats.json`, and `constellations.json` are reproducible
  deployment artifacts and are committed. Regenerate with
  `conda run -n iconocracy python scripts/build_data.py --corpus /path/to/pinned/corpus/corpus-data.json`.
- CI checks out the exact corpus commit and fails when regenerated JSON differs.

### Validation

- `python3 scripts/validate_acervo.py --json site/data/corpus-data-enriched.json --schema schemas/corpus-data-enriched.schema.json --report /tmp/report.md`
  validates JSON + JSON Schema, then checks every external image URL over the network.
  Schema validation uses `jsonschema` when installed (stdlib fallback otherwise). Some
  image URLs return 403/timeout from restricted networks — those are network/WAF issues,
  **not** code failures. Use `--retries 0 --timeout 5` for a fast run.
- Run `conda run -n iconocracy python -m unittest discover -s tests -v` for the
  publication pipeline. External URL checks are diagnostic; local image presence and
  deterministic generation are release gates.
