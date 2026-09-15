(() => {
  'use strict';
  const params = new URLSearchParams(location.search);
  const requested = params.get('slug');
  const node = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const workLink = (item, slug) => `acervo.html?item=${encodeURIComponent(item.id)}&constelacao=${encodeURIComponent(slug)}`;
  Promise.all([
    fetch('data/constellations.json').then((response) => response.json()),
    fetch('data/acervo.json').then((response) => response.json()),
  ]).then(([constellations, items]) => {
    const definition = constellations.find((entry) => entry.slug === requested) || constellations[0];
    const intro = document.querySelector('#constellation-intro');
    const list = document.querySelector('#constellation-items');
    if (!definition) {
      intro.replaceChildren(node('p', 'eyebrow', 'Constelações'), node('h1', '', 'Nenhum percurso publicado'), node('p', '', 'As lentes curatoriais aparecem aqui depois da revisão autoral e documental.'));
      return;
    }
    document.title = `${definition.title} — Iconocracia`;
    intro.replaceChildren(node('p', 'eyebrow', 'Constelação curatorial'), node('h1', '', definition.title), node('p', 'constellation-period', definition.subtitle || ''), node('p', 'constellation-deck', definition.introduction || ''));
    const byId = new Map(items.map((item) => [item.id, item]));
    definition.item_ids.forEach((id, index) => {
      const item = byId.get(id); if (!item) return;
      const li = node('li', 'constellation-work');
      const link = node('a'); link.href = workLink(item, definition.slug);
      const figure = node('figure');
      const image = node('img'); image.src = item.imagem; image.alt = item.texto_alternativo || item.titulo; image.loading = index < 2 ? 'eager' : 'lazy'; image.decoding = 'async';
      const caption = node('figcaption');
      caption.append(node('span', 'constellation-number', String(index + 1).padStart(2, '0')), node('h2', '', item.titulo), node('p', 'constellation-meta', `${item.pais} · ${item.data}`), node('p', '', item.analise_publica?.summary || item.descricao));
      if (item.id === '324a90b6-403b-5b36-9bcf-d4c4db9efdc1') caption.append(node('p', 'constellation-date-note', 'Produzida entre 1835 e 1841 · representa a Constituição de 1791.'));
      caption.append(node('span', 'constellation-open', 'Abrir ficha →'));
      figure.append(image, caption); link.append(figure); li.append(link); list.append(li);
    });
    const switcher = document.querySelector('#constellation-switcher');
    const current = constellations.indexOf(definition);
    const previous = constellations[current - 1]; const next = constellations[current + 1];
    if (previous) { const link = node('a', '', `← ${previous.title}`); link.href = `constelacoes.html?slug=${encodeURIComponent(previous.slug)}`; switcher.append(link); }
    if (next) { const link = node('a', '', `${next.title} →`); link.href = `constelacoes.html?slug=${encodeURIComponent(next.slug)}`; switcher.append(link); }
  }).catch(() => {
    document.querySelector('#constellation-intro').replaceChildren(node('h1', '', 'Percurso indisponível'), node('p', '', 'Não foi possível carregar esta constelação.'));
  });
})();
