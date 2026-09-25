/**
 * Mnemosyne Viva — editorial site worker (iconocracia.com)
 *
 * Serves the static `site/` assets via the ASSETS binding, plus:
 *   - GET /robots.txt        crawl policy, points at the sitemap
 *   - GET /sitemap.xml       generated at request time from site/data/stats.json
 *   - GET /pesquisa-e-metodo 301 → /sobre (the nav label's promised URL)
 *   - unknown paths          clean 404 with the site's own 404.html
 *
 * Responses to HTML routes are cached at the edge (short TTL, long SWR)
 * so the editorial pages are not re-rendered by the Worker on every hit.
 */

const BASE_URL = 'https://iconocracia.com';

/** Routes that own a real static page in site/. */
const KNOWN_ROUTES = new Set(['/', '/index', '/acervo', '/sobre']);

/** Legacy or promised URLs that permanently move elsewhere. */
const REDIRECTS = new Map([
  ['/pesquisa-e-metodo', '/sobre'],
  ['/home', '/'],
]);

const XML_HEADERS = { 'Content-Type': 'application/xml; charset=utf-8' };
const TEXT_HEADERS = { 'Content-Type': 'text/plain; charset=utf-8' };

/** Edge cache profile for editorial HTML: 5 min fresh, 1 day stale-while-revalidate. */
const HTML_CACHE = 'public, max-age=300, stale-while-revalidate=86400';

function normalizePath(pathname) {
  let path = pathname.replace(/\/+$/, '') || '/';
  if (path.endsWith('.html')) path = path.slice(0, -'.html'.length);
  return path;
}

function buildRobots() {
  return ['User-agent: *', 'Allow: /', '', `Sitemap: ${BASE_URL}/sitemap.xml`, ''].join('\n');
}

function buildSitemap(stats) {
  const total = stats && Number.isFinite(stats.total) ? stats.total : null;
  const urls = [
    { loc: `${BASE_URL}/`, priority: '1.0' },
    { loc: `${BASE_URL}/sobre`, priority: '0.9' },
    { loc: `${BASE_URL}/acervo`, priority: '0.9' },
  ];
  const body = urls
    .map(
      (u) =>
        `  <url><loc>${u.loc}</loc><changefreq>weekly</changefreq><priority>${u.priority}</priority></url>`,
    )
    .join('\n');
  const comment = total
    ? `  <!-- acervo: ${total} itens; fichas individuais entram no sitemap quando as páginas estáticas forem geradas -->\n`
    : '';
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${comment}${body}\n</urlset>\n`;
}

async function fetchSiteStats(env) {
  try {
    const res = await env.ASSETS.fetch(new Request(`${BASE_URL}/data/stats.json`));
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null; // sitemap must never fail because of stats
  }
}

/** Serve a static page from site/, honoring the editorial cache profile. */
async function servePage(env, assetPath, status = 200) {
  const res = await env.ASSETS.fetch(new Request(new URL(assetPath, BASE_URL)));
  if (!res.ok) {
    return new Response('Not found', { status: 404, headers: TEXT_HEADERS });
  }
  const headers = new Headers(res.headers);
  headers.set('Cache-Control', HTML_CACHE);
  return new Response(res.body, { status, headers });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = normalizePath(url.pathname);

    if (url.pathname === '/robots.txt') {
      return new Response(buildRobots(), { headers: TEXT_HEADERS });
    }

    if (url.pathname === '/sitemap.xml') {
      const stats = await fetchSiteStats(env);
      return new Response(buildSitemap(stats), { headers: XML_HEADERS });
    }

    if (REDIRECTS.has(path)) {
      return Response.redirect(`${BASE_URL}${REDIRECTS.get(path)}`, 301);
    }

    if (KNOWN_ROUTES.has(path)) {
      const asset = path === '/' || path === '/index' ? '/index.html' : `${path}.html`;
      return servePage(env, asset);
    }

    // Anything else: only assets (css/js/images/data) fall through.
    const isAsset = /\.[a-z0-9]+$/i.test(url.pathname);
    if (isAsset) {
      return env.ASSETS.fetch(request);
    }

    return servePage(env, '/404.html', 404);
  },
};
