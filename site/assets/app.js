/* Mnemosyne Viva — comportamento do site (tema, nav mobile, acervo) */
(function () {
  "use strict";

  /* ---------- tema claro/escuro (persistente) ---------- */
  const root = document.documentElement;
  const saved = localStorage.getItem("mv-theme");
  if (saved) root.setAttribute("data-theme", saved);
  else if (window.matchMedia("(prefers-color-scheme: dark)").matches)
    root.setAttribute("data-theme", "dark");

  function syncToggle(btn) {
    if (!btn) return;
    const dark = root.getAttribute("data-theme") === "dark";
    btn.textContent = dark ? "☀" : "☾";
    btn.setAttribute("aria-label", dark ? "Ativar tema claro" : "Ativar tema escuro");
  }

  document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.querySelector(".theme-toggle");
    syncToggle(toggle);
    if (toggle) {
      toggle.addEventListener("click", function () {
        const dark = root.getAttribute("data-theme") === "dark";
        const next = dark ? "light" : "dark";
        root.setAttribute("data-theme", next);
        localStorage.setItem("mv-theme", next);
        syncToggle(toggle);
      });
    }

    const navToggle = document.querySelector(".nav-toggle");
    const navLinks = document.querySelector(".nav-links");
    if (navToggle && navLinks) {
      navToggle.addEventListener("click", function () {
        const open = navLinks.classList.toggle("open");
        navToggle.setAttribute("aria-expanded", String(open));
      });
    }

    if (document.getElementById("gallery")) initAcervo();
    hydrateStats();
  });

  /* ---------- estatísticas na home ---------- */
  function hydrateStats() {
    const nodes = document.querySelectorAll("[data-stat]");
    if (!nodes.length) return;
    fetch("data/stats.json")
      .then((r) => r.json())
      .then((s) => {
        nodes.forEach((n) => {
          const key = n.getAttribute("data-stat");
          if (key === "total") n.textContent = s.total;
          else if (key === "paises") n.textContent = s.paises;
          else if (key === "com_imagem") n.textContent = s.com_imagem;
          else if (key === "periodo") n.textContent = s.periodo.min + "–" + s.periodo.max;
        });
      })
      .catch(() => {});
  }

  /* ---------- acervo ---------- */
  function initAcervo() {
    const gallery = document.getElementById("gallery");
    const countEl = document.getElementById("result-count");
    const search = document.getElementById("q");
    const fPais = document.getElementById("f-pais");
    const fRegime = document.getElementById("f-regime");
    let itens = [];

    fetch("data/acervo.json")
      .then((r) => r.json())
      .then((data) => {
        itens = data;
        populate(fPais, unique(itens.map((i) => i.pais)));
        populate(fRegime, unique(itens.map((i) => i.regime).filter(Boolean)));
        render();
      })
      .catch((err) => {
        gallery.innerHTML =
          '<p class="notice">Não foi possível carregar o acervo (' +
          String(err) +
          "). Verifique se o site está sendo servido por HTTP.</p>";
      });

    [search, fPais, fRegime].forEach((el) => el && el.addEventListener("input", render));

    function render() {
      const q = (search.value || "").trim().toLowerCase();
      const p = fPais.value;
      const r = fRegime.value;
      const filtered = itens.filter((i) => {
        if (p && i.pais !== p) return false;
        if (r && i.regime !== r) return false;
        if (q) {
          const hay = (i.titulo + " " + i.autoria + " " + i.instituicao + " " + (i.motivos || []).join(" ")).toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
      countEl.textContent =
        filtered.length + " de " + itens.length + " itens do recorte inicial";
      gallery.innerHTML = "";
      const frag = document.createDocumentFragment();
      filtered.forEach((i) => frag.appendChild(cardFor(i)));
      gallery.appendChild(frag);
    }

    function cardFor(i) {
      const el = document.createElement("article");
      el.className = "item";

      const thumb = document.createElement("div");
      if (i.tem_imagem && i.imagem) {
        thumb.className = "thumb";
        const img = document.createElement("img");
        img.loading = "lazy";
        img.alt = i.titulo;
        img.src = i.imagem;
        img.addEventListener("error", function () {
          thumb.className = "thumb noimg";
          thumb.textContent = "Imagem no arquivo de origem";
        });
        thumb.appendChild(img);
      } else {
        thumb.className = "thumb noimg";
        thumb.textContent = "Sem reprodução local — consultar arquivo";
      }
      el.appendChild(thumb);

      const body = document.createElement("div");
      body.className = "body";

      const h = document.createElement("h3");
      h.textContent = i.titulo;
      body.appendChild(h);

      const meta = document.createElement("div");
      meta.className = "meta";
      const bits = [i.pais, i.data, i.instituicao].filter(Boolean);
      meta.textContent = bits.join(" · ");
      body.appendChild(meta);

      if (i.autoria) {
        const au = document.createElement("div");
        au.className = "meta";
        au.textContent = i.autoria;
        body.appendChild(au);
      }

      const pills = document.createElement("div");
      pills.className = "pills";
      if (i.regime) {
        const rp = document.createElement("span");
        rp.className = "pill regime";
        rp.textContent = i.regime;
        pills.appendChild(rp);
      }
      (i.motivos || []).slice(0, 2).forEach((m) => {
        if (!m) return;
        const mp = document.createElement("span");
        mp.className = "pill";
        mp.textContent = m;
        pills.appendChild(mp);
      });
      body.appendChild(pills);

      if (i.fonte_url) {
        const a = document.createElement("a");
        a.href = i.fonte_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Ver no arquivo de origem →";
        a.style.fontSize = ".82rem";
        a.style.marginTop = ".4rem";
        body.appendChild(a);
      }

      el.appendChild(body);
      return el;
    }
  }

  function unique(arr) {
    return Array.from(new Set(arr.filter(Boolean))).sort((a, b) => a.localeCompare(b, "pt"));
  }
  function populate(sel, vals) {
    if (!sel) return;
    vals.forEach((v) => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      sel.appendChild(o);
    });
  }
})();
