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

## Regra de design: quando usar o musepool

Antes de gerar qualquer página, componente ou HTML novo, decidir qual autoridade
de design se aplica. Critério de desempate: **na dúvida, o design system
existente vence.**

**USAR o musepool quando:**
- A superfície **não tem identidade própria**: domínio/microssite novo,
  landing page isolada, dashboard — ou pedido explícito de identidade visual
  nova. Páginas novas **dentro** de um site existente (atlas, método, artigos
  públicos no iconocracia.com; qualquer página no anavanzin.com) NÃO são esse
  caso: herdam o design system do site hospedeiro.
- Fluxo: recall amplo (temperatura 0.6–0.9) → escolher 1–2 dimensões "wow"
  → fetch profundo (seed + referências dimensionais) → sintetizar.
- Queries em inglês, por problema e não por estilo (ex.: "scholarly digital
  archive, dense image grid, Warburg-inspired interface" — nunca
  "minimal/clean/modern").
- Restrição de saída: **HTML/CSS estático, sem build, sem framework** — o
  resultado precisa caber no pipeline existente. Se o musepool não estiver
  disponível, não improvisar identidade nova: herdar o design system e avisar.

**NÃO USAR o musepool quando:**
- O trabalho é dentro de um design system já resolvido. O iconocracia.com
  (Mnemosyne Viva) já tem identidade própria: papel creme #EFE5CF, lacre
  vermelho, Instrument Serif (display) + Crimson Pro (corpo) + JetBrains Mono.
  Nesse caso a referência é o próprio site (site/assets/style.css) — mexer
  no design é dano, não melhoria. Pedido explícito de redesign → confirmar
  escopo antes de tocar nos tokens.
- O trabalho é técnico e não visual (SEO, canonicals, JSON-LD, redirects,
  Worker, fichas estáticas): nenhuma decisão de design deve ser tomada.

**Princípio:** o musepool existe para impedir a "média visual de IA". Onde já
existe identidade construída, ela é a referência — o musepool só entra onde
não há identidade alguma.
