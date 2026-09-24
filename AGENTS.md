# AGENTS.md

## Cursor Cloud specific instructions

Mnemosyne Viva is a **static editorial site** (the public site for `iconocracia.com`).
There is no build/bundling step for the HTML/CSS/JS itself. See `README.md` for the
canonical file/directory overview.

### Services

- **Static site (only runnable service).** Production is the Cloudflare Worker in
  `src/index.js` (worker name: `iconocracia`), which serves `site/` via the assets
  binding and owns `/robots.txt`, `/sitemap.xml`, redirects, and the clean 404.
  There is no Vercel deploy. For local development run the Worker with Miniflare:
  - `npx wrangler dev --port 8787` — serves the `site/` assets plus the Worker. Open
    `http://127.0.0.1:8787/` (homepage) and `/acervo` (collection grid).
  - The pinned wrangler is v3; it prints harmless warnings about being out-of-date and
    about the `compatibility_date` being newer than the runtime — the site
    serves fine regardless.
  - The old `/api/exec` sandbox endpoint (Cloudflare container Durable Object) was
    **removed** — the editorial site carries no server-side execution surface.