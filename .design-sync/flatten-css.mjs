// Pre-build step for /design-sync (cfg.buildCmd). The site stylesheet is two
// layers joined by a relative @import (site/assets/style.css pulls in
// site/assets/design-system/styles.css) and it points at two PNG ornaments by
// relative url(). The converter copies cfg.cssEntry verbatim, so it needs one
// self-contained file: this script inlines the design-system token layers in
// their manifest order, appends style.css without its @import, and swaps the
// ornament PNGs for the WebP copies in .design-sync/assets/ as data URIs.
// Fonts are not inlined here; cfg.extraFonts ships them from fonts.css.
//
// Output (gitignored): .design-sync/.cache/src/mnemosyne-viva.css and an
// empty entry module the converter bundles into the tokens-only _ds_bundle.js.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dsDir = join(root, 'site/assets/design-system');
const out = join(root, '.design-sync/.cache/src');
const read = (p) => readFileSync(p, 'utf8');

const manifest = read(join(dsDir, 'styles.css'));
const layers = [...manifest.matchAll(/@import\s+url\(\s*["']?\.\/([^"')]+)["']?\s*\)/g)]
  .map((m) => m[1])
  .filter((p) => !p.startsWith('fonts/'));
if (!layers.length) throw new Error('no token layers found in design-system/styles.css');

const siteCss = read(join(root, 'site/assets/style.css'));
const importLine = /@import\s+url\(\s*["']?\.\/design-system\/styles\.css["']?\s*\)\s*;\s*\n?/;
if (!importLine.test(siteCss)) throw new Error('style.css no longer imports ./design-system/styles.css; update this script');

// Each data URI is declared once as a custom property (style.css repeats the
// .brand-ornament rule, and a 160 KB URI per occurrence adds up).
const ornaments = [
  ['edelweiss-ornaments.png', 'edelweiss-ornaments.webp', '--edelweiss-sprite'],
  ['edelweiss-flower.png', 'edelweiss-flower.webp', '--edelweiss-flower'],
];
let body = siteCss.replace(importLine, '');
const ornamentVars = [];
for (const [png, webp, prop] of ornaments) {
  if (!body.includes(`url("${png}")`)) throw new Error(`style.css no longer references ${png}; update this script`);
  const uri = `data:image/webp;base64,${readFileSync(join(root, '.design-sync/assets', webp)).toString('base64')}`;
  ornamentVars.push(`  ${prop}: url("${uri}");`);
  body = body.split(`url("${png}")`).join(`var(${prop})`);
}

const parts = [
  '/* Mnemosyne Viva, flattened for Claude Design by .design-sync/flatten-css.mjs.',
  '   Layer 1: site/assets/design-system/tokens/* (Iuris Memoria base tokens).',
  '   Layer 2: site/assets/style.css (site components + the Exposicao --ex-* palette, which wins). */',
  ...layers.map((p) => `\n/* ---- design-system/${p} ---- */\n${read(join(dsDir, p))}`),
  `\n/* ---- Edelweiss ornaments (WebP copies of site/assets/*.png) ---- */\n:root {\n${ornamentVars.join('\n')}\n}`,
  `\n/* ---- style.css ---- */\n${body}`,
];
const css = parts.join('\n');

const leftovers = [...css.matchAll(/url\(\s*["']?(?!data:|https?:|#|%23)([^"')]+)["']?\s*\)/g)].map((m) => m[1]);
if (leftovers.length) throw new Error(`unresolved relative url() in flattened CSS: ${leftovers.join(', ')}`);
if (/@import/.test(css.replace(/\/\*[\s\S]*?\*\//g, ''))) throw new Error('flattened CSS still contains an @import');

mkdirSync(out, { recursive: true });
writeFileSync(join(out, 'mnemosyne-viva.css'), css);
writeFileSync(join(out, 'entry.mjs'), 'export {};\n');
console.log(`flatten-css: ${layers.length} token layers + style.css -> ${(css.length / 1024).toFixed(0)} KB`);
