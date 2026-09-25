# Mnemosyne Viva · Exposição: how to build with it

**There are no components.** This design system is the stylesheet of iconocracia.com, a static HTML/CSS site. `window.MnemosyneViva` is empty: nothing to import or mount, so skip the React loading notes further down. Build with plain HTML elements (or JSX that renders plain elements) carrying the class names and tokens below. Link `styles.css` once; it brings the fonts, every token and every class. Content language is Brazilian Portuguese.

## Wrapper
Put `class="ex-page"` on `<body>` (or the outermost wrapper). Without it the page falls back to Arial 16px; with it, text is Crimson Pro 18px/1.6. Editorial pages made of `section.block` bands also take `ex-home` (`class="ex-page ex-home"`), which turns `.block` lilac and `.block.alt` blush. Light theme only: the site never sets `data-theme`.

## Tokens (use `var(--…)`)
The Exposição palette overrides the older Iuris Memoria vellum tokens that are still in the file. Don't bring back cream or red.
- `--ex-ground` #b99aee page lavender · `--ex-reading` #ede4ff reading panels · `--palette-paper` #f7f1ff cards and image mats · `--palette-blush` #f4ddeb alternate bands
- `--ex-ink` #25103f text · `--ex-muted` #49335f secondary text · `--palette-violet` #3b175d labels, tags, footer · `--ex-selection` #6524bd focus and accent · `--ex-line` #aa89c9 rules
- `--ex-action` #e4ff38 the one acid-yellow action colour (hover #d3ee20)
- Type scale (base 18, ratio 4/3): `--atlas-caption` 13.5 · `--atlas-body` 18 · `--atlas-subtitle` 24 · `--atlas-heading` 32 · `--atlas-section` 42.65 · `--atlas-display` 56.86 · `--atlas-title` 75.81
- Fonts: "Instrument Serif" for display (weight 400 only; italic for artwork titles), "Crimson Pro" for reading, "JetBrains Mono" for captions, controls and labels. `--font-display` and `--font-mono` resolve to these. `--font-body` resolves to Arial in this layer, so name Crimson Pro directly or rely on `.ex-page`.

## Classes
| Need | Markup |
|---|---|
| Site header | `header.ex-header` > `a.ex-brand` (`span.brand-flower.brand-ornament` + wordmark "ICONOCRACIA") + `nav` of links; mark the current one with `aria-current="page"` |
| Section band | `section.block` (+ `.alt`, `.closing`) > `div.wrap` (max 1160px) |
| Kickers | `.label` (violet block, mono caps), `.eyebrow` (inline mono caps), `.tag` (small violet chip) |
| Regime pill | `span.pill.regime` |
| Buttons | `a.btn` + `.btn-primary` (acid yellow) / `.btn-dark` (violet) / `.btn-ghost` (outline); row wrappers `.home-actions` (left) or `.cta-row` (centred) |
| Callout | `div.notice` with a leading `<strong>` |
| Figures | `section.stat-band` > `.stat` > `.num` + `.lbl` |
| Collection viewer | `.exhibition`; filters `.ex-filters` (`.ex-search` with input, selects, `.ex-filter-button`); image `.ex-stage`; `.ex-filmstrip` > `button.ex-thumb` (`.ex-thumb-image`, `.ex-thumb-title`, `.ex-thumb-meta`); text `.ex-caption` (`.ex-overline`, `h1`, `.ex-author`, `.ex-description`, `dl.ex-metadata`); actions `a.ex-action` (+ `.ex-primary` for the yellow one) |
| Ornaments | `span.brand-ornament` + `.brand-scroll` (scroll), `.brand-seal` (round seal) or `.brand-flower` (46px mark); divider `div.ornamental-divider` > `span.brand-scroll.brand-ornament` |
| Footer | `footer.site-footer` (violet ground, acid headings) |
| Utilities | `.sr-only`, `.mono`, `.rubric` |

Artwork images are never cropped: `object-fit: contain` inside a `.ex-stage`-style box. Icons are inline line SVGs, `stroke="currentColor"`, `stroke-width="1.7"`, 24px.

## Where the truth lives
`_ds_bundle.css` is the flattened site stylesheet. It has the base token layers first, then the site rules; when rules conflict, the later one wins, and the Exposição blocks near the end decide the look. Fonts are in `fonts/fonts.css`.

## Example
```html
<body class="ex-page ex-home">
  <header class="ex-header">
    <a class="ex-brand" href="#"><span class="brand-flower brand-ornament" aria-hidden="true"></span><span>ICONOCRACIA</span></a>
    <nav aria-label="Navegação principal"><a href="#" aria-current="page">Início</a><a href="#">Acervo</a></nav>
  </header>
  <section class="block alt"><div class="wrap">
    <span class="label">A pesquisa</span>
    <h2>Iconocracia</h2>
    <p><span class="pill regime">Normativo</span> <span class="tag">Conceito autoral</span></p>
    <div class="home-actions"><a class="btn btn-primary" href="#">Explorar o acervo <span aria-hidden="true">↗</span></a><a class="btn btn-dark" href="#">Método</a></div>
  </div></section>
  <div class="ornamental-divider" aria-hidden="true"><span class="brand-scroll brand-ornament"></span></div>
</body>
```
