/* ICONOCRACIA — exposição, filtros e fichas do recorte publicado. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const normalize = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const safeURL = (value) => /^https?:\/\//i.test(value || '');
  const shortTitle = (item) => item.titulo.replace(/\s*\([^)]*\)\s*$/, '');
  const yearOf = (item) => Number(String(item.data).match(/\b\d{4}\b/)?.[0]) || null;
  const centuryOf = (item) => { const year = yearOf(item); return year ? String(Math.floor((year - 1) / 100) + 1) : 'sem-ano'; };
  // Agrupamento de navegação derivado do suporte; o valor original permanece na ficha.
  function typeOf(item) {
    const support = normalize(item.suporte);
    if (/photograph|photogra|albumen|salted paper/.test(support)) return 'Fotografia';
    if (/sculpture|relief|bust/.test(support)) return 'Escultura';
    if (/poster|affiche|cartaz/.test(support)) return 'Cartaz';
    if (/oil|painting|pintura|decorative panel/.test(support)) return 'Pintura';
    if (/coin|money/.test(support)) return 'Moeda e cédula';
    if (/print|engraving|etching|lithogra|gravura|estampe|woodcut|drawing|desenho/.test(support)) return 'Gravura e desenho';
    if (/manuscript|periodical/.test(support)) return 'Documento';
    return 'Outros suportes';
  }
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function reproduce(item, container, lazy = false) {
    if (!item.tem_imagem || !item.imagem) {
      container.append(node('span', 'ex-missing', 'Sem reprodução disponível — consulte o arquivo de origem.'));
      return;
    }
    const img = node('img');
    img.alt = item.texto_alternativo || item.titulo;
    img.decoding = 'async';
    img.loading = lazy ? 'lazy' : 'eager';
    img.src = item.imagem;
    let fallback = false;
    img.addEventListener('error', () => {
      if (!fallback && safeURL(item.imagem)) { fallback = true; img.src = item.imagem; }
      else container.replaceChildren(node('span', 'ex-missing', 'Reprodução indisponível — consulte o arquivo de origem.'));
    });
    container.append(img);
  }
  const searchShortcut = $('.ex-search-shortcut');
  searchShortcut?.addEventListener('click', () => {
    if ($('#q')) $('#q').focus(); else location.href = 'acervo.html?buscar=1';
  });
  if ($('[data-stat]') || $('[data-collection-cta]')) {
    fetch('data/stats.json').then((response) => response.json()).then((stats) => {
      document.querySelectorAll('[data-stat]').forEach((el) => {
        el.textContent = el.dataset.stat === 'periodo' ? stats.periodo.min + '–' + stats.periodo.max : stats[el.dataset.stat];
      });
      document.querySelectorAll('[data-collection-cta]').forEach((el) => {
        el.textContent = 'Ver os ' + stats.total + ' itens catalogados';
      });
    }).catch(() => {});
  }
  fetch('data/constellations.json').then((response) => response.json()).then((constellations) => {
    if (!Array.isArray(constellations) || !constellations.length) return;
    document.querySelectorAll('.ex-header nav').forEach((nav) => {
      if (!nav.querySelector('[data-constellations-link]')) {
        const link = node('a', '', 'Constelações'); link.href = 'constelacoes.html';
        link.dataset.constellationsLink = ''; nav.insertBefore(link, nav.lastElementChild);
      }
    });
    document.querySelectorAll('[data-constellation-cta]').forEach((el) => { el.hidden = false; });
  }).catch(() => {});
  if (!$('.exhibition')) {
    // Preserve collection links shared before the homepage became an introduction.
    if ($('.ex-home') && new URLSearchParams(location.search).has('item')) {
      location.replace('acervo.html' + location.search + location.hash);
    }
    return;
  }

  let items = [], filtered = [], selected = null, activeConstellation = null;
  const fields = { q: $('#q'), pais: $('#f-pais'), regime: $('#f-regime'), periodo: $('#f-periodo'), tipo: $('#f-tipo') };
  const params = new URLSearchParams(location.search);
  const stage = $('.ex-stage'), strip = $('#ex-filmstrip');
  const dialog = node('dialog', 'ex-dialog');
  dialog.setAttribute('aria-labelledby', 'dialog-title');
  document.body.append(dialog);
  dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => { document.body.style.overflow = ''; });

  function fillOptions(element, values, label = (value) => value) {
    [...new Set(values)].filter(Boolean).sort((a, b) => a.localeCompare(b, 'pt', { numeric: true })).forEach((value) => {
      const option = node('option', '', label(value)); option.value = value; element.append(option);
    });
  }
  function syncURL() {
    const url = new URL(location.href);
    for (const [key, el] of Object.entries(fields)) {
      if (el.value) url.searchParams.set(key, el.value); else url.searchParams.delete(key);
    }
    if (selected) url.searchParams.set('item', selected.id); else url.searchParams.delete('item');
    url.searchParams.delete('buscar');
    history.replaceState(null, '', url);
  }
  function filterItems() {
    const scoped = activeConstellation
      ? activeConstellation.item_ids.map((id) => items.find((item) => item.id === id)).filter(Boolean)
      : items;
    filtered = scoped.filter((item) => {
      if (fields.pais.value && fields.pais.value !== item.pais) return false;
      if (fields.regime.value && fields.regime.value !== item.regime) return false;
      if (fields.periodo.value && fields.periodo.value !== centuryOf(item)) return false;
      if (fields.tipo.value && fields.tipo.value !== typeOf(item)) return false;
      const haystack = normalize([item.id, item.titulo, item.autoria, item.pais, item.data, item.instituicao, item.suporte, ...(item.motivos || [])].join(' '));
      return !fields.q.value || haystack.includes(normalize(fields.q.value));
    });
    selected = filtered.find((item) => item.id === selected?.id) || filtered[0] || null;
    $('#result-count').textContent = activeConstellation
      ? filtered.length + ' obras · ' + activeConstellation.title
      : filtered.length + ' de ' + items.length + ' registros · recorte do acervo';
    $('#clear-filters').hidden = !Object.values(fields).some((el) => el.value);
    renderStrip();
    renderSelected();
  }
  function renderStrip() {
    strip.replaceChildren();
    filtered.forEach((item) => {
      const button = node('button', 'ex-thumb');
      button.type = 'button'; button.dataset.id = item.id;
      button.setAttribute('aria-label', 'Selecionar ' + item.titulo);
      const frame = node('span', 'ex-thumb-image'); reproduce(item, frame, true);
      button.append(frame, node('span', 'ex-thumb-title', shortTitle(item)), node('span', 'ex-thumb-meta', item.pais + ', ' + item.data));
      button.addEventListener('click', () => select(item));
      strip.append(button);
    });
  }
  function select(item) { selected = item; renderSelected(); }
  function navigate(step) {
    const index = filtered.indexOf(selected);
    if (filtered[index + step]) select(filtered[index + step]);
  }
  function renderSelected() {
    const index = filtered.indexOf(selected);
    $('.ex-prev').disabled = index <= 0;
    $('.ex-next').disabled = index < 0 || index >= filtered.length - 1;
    $('#ex-open').disabled = !selected;
    $('#ex-more').disabled = !selected;
    $('.ex-expand').disabled = !selected?.tem_imagem;
    $('#ex-image').replaceChildren();
    $('#ex-metadata').replaceChildren();
    $('#ex-source').hidden = !selected || !safeURL(selected.fonte_url);
    if (!selected) {
      $('#ex-image').append(node('p', 'ex-empty', 'Nenhuma obra encontrada. Experimente outro termo ou limpe os filtros.'));
      $('#ex-title').textContent = 'Nenhuma obra encontrada';
      $('#ex-author').textContent = $('#ex-date').textContent = $('#ex-description').textContent = '';
      $('#ex-position').textContent = '0 / 0';
      syncURL(); return;
    }
    reproduce(selected, $('#ex-image'));
    $('#ex-title').textContent = shortTitle(selected);
    $('#ex-author').textContent = selected.autoria || 'Autoria não informada';
    $('#ex-date').textContent = selected.pais + ', ' + selected.data;
    // A descrição extensa e a citação são preservadas integralmente na ficha.
    $('#ex-description').textContent = selected.instituicao || 'Instituição não informada';
    $('#ex-source').href = selected.fonte_url || '';
    const metadata = [['País', selected.pais], ['Regime', selected.regime], ['Data', selected.data], ['Tipo de obra', typeOf(selected)], ['Suporte', selected.suporte]];
    metadata.forEach(([label, value]) => { if (value) $('#ex-metadata').append(node('dt', '', label), node('dd', '', value)); });
    $('#ex-position').textContent = (index + 1) + ' / ' + filtered.length;
    strip.querySelectorAll('.ex-thumb').forEach((button) => {
      const active = button.dataset.id === selected.id;
      button.setAttribute('aria-pressed', String(active));
      if (active) {
        // Rolagem limitada à faixa, sem deslocar a página ao mudar a obra.
        const left = button.offsetLeft - strip.offsetLeft;
        if (left < strip.scrollLeft || left + button.offsetWidth > strip.scrollLeft + strip.clientWidth) strip.scrollLeft = left;
      }
    });
    syncURL();
  }
  function openRecord(imageOnly = false) {
    if (!selected) return;
    dialog.replaceChildren();
    dialog.classList.toggle('ex-dialog-image-only', imageOnly);
    const close = node('button', 'ex-dialog-close', 'Fechar'); close.type = 'button'; close.addEventListener('click', () => dialog.close());
    const title = node('h2', '', selected.titulo); title.id = 'dialog-title';
    const layout = node('div', 'ex-dialog-layout');
    const picture = node('div', 'ex-dialog-image'); reproduce(selected, picture);
    const details = node('div', 'ex-dialog-details'); details.append(title);
    if (!imageOnly) {
      const list = node('dl', 'ex-record');
      for (const [label, value] of [['Registro', selected.id], ['Autoria', selected.autoria], ['País', selected.pais], ['Data', selected.data], ['Instituição', selected.instituicao], ['Regime', selected.regime], ['Suporte', selected.suporte], ['Motivos', (selected.motivos || []).join(', ')], ['Descrição', selected.descricao], ['Direitos', selected.direitos], ['Crédito da reprodução', selected.credito], ['Citação', selected.citacao]]) {
        if (value) list.append(node('dt', '', label), node('dd', '', value));
      }
      details.append(list);
      const analysis = selected.analise_publica;
      if (analysis) {
        const section = node('details', 'ex-analysis');
        const heading = node('summary', '', 'Análise iconográfica');
        section.append(heading, node('p', 'ex-analysis-summary', analysis.summary || ''));
        const levels = analysis.panofsky || {};
        for (const [label, key] of [['Nível 1 · pré-iconográfico', 'level_1'], ['Nível 2 · iconográfico', 'level_2'], ['Nível 3 · iconológico', 'level_3']]) {
          if (levels[key]) { section.append(node('h3', '', label), node('p', '', levels[key])); }
        }
        if (analysis.indicators) {
          const grid = node('dl', 'ex-indicator-grid');
          Object.entries(analysis.indicators).forEach(([key, value]) => grid.append(node('dt', '', key.replaceAll('_', ' ')), node('dd', '', String(value) + ' / 3')));
          section.append(node('h3', '', 'Indicadores de purificação'), node('p', 'ex-scale', analysis.scale || 'Escala ordinal de 0 a 3.'), grid);
        } else {
          section.append(node('p', 'ex-scale', 'Indicadores não aplicáveis: não há figura feminina identificável nesta obra.'));
        }
        if (analysis.limitation) section.append(node('p', 'ex-analysis-limitation', analysis.limitation));
        if (analysis.method_note) section.append(node('p', 'ex-method-note', analysis.method_note));
        details.append(section);
      }
    }
    if (safeURL(selected.fonte_url)) {
      const source = node('a', 'ex-action', 'Arquivo de origem'); source.href = selected.fonte_url; source.target = '_blank'; source.rel = 'noopener'; details.append(source);
    }
    layout.append(picture, details); dialog.append(close, layout); dialog.showModal(); document.body.style.overflow = 'hidden'; close.focus();
  }
  $('.ex-prev').addEventListener('click', () => navigate(-1));
  $('.ex-next').addEventListener('click', () => navigate(1));
  stage.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); navigate(event.key === 'ArrowLeft' ? -1 : 1); }
  });
  $('#ex-open').addEventListener('click', () => openRecord());
  $('#ex-more').addEventListener('click', () => openRecord());
  $('.ex-expand').addEventListener('click', () => openRecord(true));
  $('.ex-filters').addEventListener('submit', (event) => { event.preventDefault(); filterItems(); });
  Object.values(fields).forEach((field) => field.addEventListener('input', filterItems));
  $('#clear-filters').addEventListener('click', () => { Object.values(fields).forEach((field) => { field.value = ''; }); filterItems(); });
  Promise.all([
    fetch('data/acervo.json').then((response) => { if (!response.ok) throw new Error('Acervo indisponível'); return response.json(); }),
    fetch('data/constellations.json').then((response) => response.ok ? response.json() : []),
  ]).then(([data, constellations]) => {
    if (!Array.isArray(data)) throw new Error('Formato inválido');
    const featured = ['BR-009', 'US-008', 'FR-005', 'BR-005', 'FR-008'];
    const rank = (item) => { const index = featured.indexOf(item.id); return index < 0 ? featured.length : index; };
    items = data.slice().sort((a, b) => rank(a) - rank(b));
    activeConstellation = (constellations || []).find((entry) => entry.slug === params.get('constelacao')) || null;
    const constellationLabel = $('#ex-constellation');
    if (activeConstellation && constellationLabel) {
      constellationLabel.hidden = false;
      constellationLabel.replaceChildren(document.createTextNode('Percurso: '), node('strong', '', activeConstellation.title));
    }
    fillOptions(fields.pais, items.map((item) => item.pais));
    fillOptions(fields.regime, items.map((item) => item.regime));
    fillOptions(fields.periodo, items.map(centuryOf), (value) => value === 'sem-ano' ? 'Sem ano numérico' : 'Século ' + value);
    fillOptions(fields.tipo, items.map(typeOf));
    Object.entries(fields).forEach(([key, field]) => { field.value = params.get(key) || ''; });
    const requested = params.get('item');
    selected = items.find((item) => item.id === requested || (item.legacy_ids || []).includes(requested)) || items[0];
    filterItems();
    if (params.has('buscar')) fields.q.focus();
  }).catch(() => {
    filtered = []; selected = null; renderSelected();
    $('#ex-title').textContent = 'Acervo indisponível';
    $('#ex-image').textContent = 'Não foi possível carregar os registros. Recarregue a página para tentar novamente.';
    $('#result-count').textContent = 'Falha ao carregar o acervo';
  });
})();
