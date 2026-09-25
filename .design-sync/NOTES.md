# design-sync notes: Mnemosyne Viva · Exposição

## Shape
- Tokens-only sync (package shape, 0 components). The repo is a static HTML/CSS site with vanilla `app.js`; there is no React library, dist or Storybook. `_ds_bundle.js` is an empty IIFE on `window.MnemosyneViva`; everything the design agent uses is in `styles.css` -> `fonts/fonts.css` + `_ds_bundle.css`.
- The user chose the live site look (full `site/assets/style.css`: Iuris Memoria base tokens + the lavender Exposição `--ex-*` layer), not the bare `site/assets/design-system/` layer. An older, separate "Iconocracia Design System" project exists in claude.ai/design; this sync targets "Mnemosyne Viva · Exposição".

## Build
- Always run `cfg.buildCmd` (`node .design-sync/flatten-css.mjs`) before the converter. `style.css` pulls the token layers through a relative `@import` and references two PNG ornaments by relative `url()`; the converter copies `cfg.cssEntry` verbatim, so the script writes one self-contained file to `.design-sync/.cache/src/mnemosyne-viva.css` plus the empty `entry.mjs`. It throws if `style.css` stops importing `./design-system/styles.css`, stops referencing either PNG, or if any relative `url()` or `@import` survives.
- The entry lives in `.design-sync/.cache/src/`; the converter walks up to the repo-root `package.json` (name `mnemosyne-viva-sandbox`, version 1.0.0), so PKG_DIR is the repo root. `globalName` is pinned so the namespace does not come from the sandbox package name.
- Ornaments: `.design-sync/assets/edelweiss-ornaments.webp` (1086x362) and `edelweiss-icon.webp` (200x224) are WebP copies of `site/assets/*.png` (Pillow, LANCZOS, quality 86). The originals weigh 1.8 MB and 0.2 MB; inlined they would have made `_ds_bundle.css` ~2.5 MB. Each is declared once as `--edelweiss-sprite` / `--edelweiss-icon` in `:root` and the site rules point at those vars.
- Fonts ship through `cfg.extraFonts` (`site/assets/design-system/fonts/fonts.css`, 46 faces, local woff2).
- `guidelinesGlob: []` because the default `docs/*.md` would upload `docs/corpus-sync-design.md`, which is about corpus data sync, not visual design.
- Converter deps: `cd .ds-sync && npm i esbuild ts-morph @types/react react react-dom playwright@1.56.1`. Pass `--node-modules .ds-sync/node_modules` (the repo's own node_modules has no React). In the claude.ai/code container, playwright 1.56.1 matches the preinstalled `/opt/pw-browsers/chromium-1194`.
- Final build command (first sync, no anchor): `node .design-sync/flatten-css.mjs && node .ds-sync/resync.mjs --config .design-sync/config.json --node-modules .ds-sync/node_modules --entry .design-sync/.cache/src/entry.mjs --out ./ds-bundle`. Re-syncs add `--remote .design-sync/.cache/remote-sync.json`.

## Known build/validate warns
- `[DTS_REACT]`: looks for `@types/react` beside the repo-root package; irrelevant with 0 components.
- `[ZERO_MATCH] no component exports, treating as tokens-only DS`: expected.

## Site issues found during the sync (not fixed by the sync)
- `site/assets/style.css` repeats the `.brand-ornament` rule right after `.brand-flower` (commit 4199cff). The repeat overrides `.brand-flower`'s `background-image`, so `span.brand-flower.brand-ornament` in the header shows the whole three-motif sprite shrunk into 46px instead of `edelweiss-icon.png`. The design system mirrors the site, so it has the same bug. Deleting the second `.brand-ornament` line fixes both after a re-sync.

- AGENTS.md ("Regra de design") describes the site identity as "papel creme #EFE5CF, lacre vermelho". That is the Iuris Memoria base layer; since the Exposição block in `style.css` the live look is lavender / violet / acid yellow, and that is what this design system ships. Both agree that `site/assets/style.css` is the reference.

## Re-sync risks
- The WebP ornament copies go stale if `site/assets/edelweiss-*.png` change; regenerate them (same sizes) before re-syncing.
- `conventions.md` lists class and token names from `style.css`. A site redesign can orphan them; re-validate each name against `ds-bundle/_ds_bundle.css`.
- The generated README body still carries the converter's React boilerplate ("All 0 components are the real upstream code", a React loading snippet). The conventions header says up front that there are no components; keep it that way.
- Verification for a tokens-only sync is `package-validate.mjs` plus a manual render of the conventions example against `ds-bundle/styles.css` (done on the first sync; fonts, palette and ornaments rendered correctly).
