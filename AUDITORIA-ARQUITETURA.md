# Mnemosyne Viva — Auditoria e Arquitetura do Staging

> Documento de trabalho gerado durante a construção do novo site editorial
> **Mnemosyne Viva** (novo `iconocracia.com`). Data: 2026-07-02.

## 1. Objetivo

Reconstruir `iconocracia.com` como **Mnemosyne Viva** — a casa pública/editorial do
acervo, do atlas e da pesquisa **ICONOCRACIA** (tese de doutorado, PPGD/UFSC, Ana Vanzin),
e não um dashboard técnico. Meta imediata: um staging navegável e deployável no Vercel,
com no mínimo `/` (home), `/sobre` e `/acervo`.

## 2. Achados da auditoria do repositório

- **Repo veio como sparse checkout (1% dos arquivos).** Foi necessário `git sparse-checkout disable`
  + `git checkout -- .` para materializar `corpus/` e `data/` e reaproveitar conteúdo real.
- **Já existia um site estático em `corpus/`** (apontado pelo `vercel.json`, `outputDirectory: "corpus"`):
  - `corpus/index.html` — explorador de corpus (gerado com Perplexity Computer), tom técnico/EN.
  - `corpus/atlas-iconometrico.html`, `corpus/DASHBOARD_CORPUS.html`, `corpus/comparador/` — dashboards.
  - **Identidade visual reaproveitável:** tipografia **Playfair Display + DM Sans**; paleta ocre/sienna
    (`--accent: #8b3a1a` claro / `#a0522d` escuro) sobre creme (`#f5f0e6`); temas claro/escuro já definidos.
- **Dados do corpus disponíveis localmente:**
  - `corpus/corpus-data.json` — **328 itens** (metadados; sem campo de imagem).
  - `corpus/corpus-data-enriched.json` — **95 itens curados** com autoria, instituição, direitos e
    **URLs de thumbnail reais** de arquivos de guarda (84 com imagem; 39 com `thumbnail_url` dedicado).
  - `companion-data.json` — agregados de UI (não canônico).
- **Conceitos e textos** reaproveitados de `CLAUDE.md`, `README.md` e `corpus/README.md`
  (Contrato Sexual Visual, Feminilidade de Estado, Endurecimento, Purificação Clássica, 4 regimes,
  10 indicadores, critérios de inclusão, país como variável analítica).
- `CNAME` = `iconocracia.com` (domínio já apontado).

## 3. Conteúdo reaproveitado (não inventado)

| Fonte no repo | Uso no site |
|---|---|
| `corpus/index.html` (CSS vars, fontes, paleta) | `site/assets/style.css` — identidade editorial |
| `corpus/corpus-data.json` | estatísticas (`site/data/stats.json`): 328 itens, 17 países, período 1707–1981 |
| `corpus/corpus-data-enriched.json` | grade do acervo (`site/data/acervo.json`): 95 itens, imagens reais |
| `CLAUDE.md` / `README.md` | textos de Sobre, conceitos, regimes, indicadores |

Nenhuma URL de acervo foi inventada. As imagens do acervo vêm dos campos `thumbnail_url`/
`url_image_download` já presentes no dataset enriquecido; quando o arquivo bloqueia hotlink
(ex.: Numista) ou não há reprodução, o card degrada para um aviso de "consultar arquivo de origem".

## 4. Decisão de arquitetura

**Staging estático puro, sem build**, em `site/` — caminho de menor risco para "sair hoje com link":

- HTML/CSS/JS baunilha, zero dependências, zero passo de compilação → deploy no Vercel não pode
  falhar por build. Framework detectado: **nenhum (static / "Other")**.
- Reaproveita a identidade do site antigo sem herdar seu tom técnico em inglês.
- Dados servidos como JSON estático gerado por `site/build_data.py` a partir das fontes canônicas.

```
site/
├── index.html           # / homepage — posiciona Mnemosyne Viva; CTAs p/ acervo e pesquisa
├── sobre.html           # /sobre — projeto, método, conceitos, relação com ICONOCRACIA
├── acervo.html          # /acervo — grade filtrável (busca, país, regime)
├── assets/
│   ├── style.css        # identidade editorial (paleta/fontes reaproveitadas)
│   └── app.js           # tema claro/escuro, nav mobile, render + filtros do acervo
├── data/
│   ├── acervo.json      # 95 itens curados (gerado)
│   └── stats.json       # agregados p/ home e acervo (gerado)
├── build_data.py        # regenera data/*.json a partir de corpus/*.json
└── AUDITORIA-ARQUITETURA.md
```

### Páginas
- **`/` (home):** hero de posicionamento, faixa de estatísticas (live do `stats.json`), três cards de
  conceitos, split acervo/regimes, bloco da pesquisa. CTAs para acervo e sobre.
- **`/sobre`:** problema da pesquisa, três conceitos centrais em destaque, método (10 indicadores),
  4 regimes, natureza aberta/exploratória do corpus, rastreabilidade e licença.
- **`/acervo`:** aviso de "recorte inicial", barra de busca + filtros (país, regime), grade responsiva
  de cards com imagem, metadados e link para o arquivo de origem.

### Recursos transversais
- Navegação sticky funcional + menu mobile; tema claro/escuro persistente (`localStorage`).
- Responsivo (grid fluida), acessibilidade básica (skip-link, `aria-current`, `aria-live`, labels,
  `prefers-reduced-motion` — implementado de fato apenas no PR #27; antes desta data a afirmacao era incorreta), metatags Open Graph + `theme-color` + `lang="pt-BR"`.

## 5. Configuração de deploy (Vercel)

`vercel.json` atualizado:
- `outputDirectory: "site"` (antes: `corpus`).
- `cleanUrls: true` → `/sobre` e `/acervo` servem os `.html` sem extensão.
- Removido o `ignoreCommand` que restringia builds a branches `claude/*` (impedia deploy normal).
- Framework: `null` (estático). Sem `buildCommand`/`installCommand`.

## 6. Validação executada

- `python3 site/build_data.py` → `stats.json` (328/17/39) e `acervo.json` (95 itens, 84 c/ imagem).
- `node --check assets/app.js` → OK. JSON válido (`json.load`).
- Servidor local (`python3 -m http.server`): `/`, `/sobre`, `/acervo`, CSS, JS, ambos JSON → **HTTP 200**.
- Amostra de thumbnails: Bildindex → 200; Numista → 403 (hotlink), coberto pelo fallback de imagem.

## 7. Próximos passos sugeridos

1. **Página do Atlas / Zwischenraum** — reaproveitar `corpus/atlas-iconometrico.html` e os 21 painéis
   comparativos de `companion-data.json` numa leitura editorial.
2. **Página de item** (`/acervo/{id}`) com análise iconológica de 3 níveis e os 10 indicadores.
3. **Expandir imagens do acervo** — resolver `local_image_path` (`corpus/imagens/…`, hoje ausente) para
   servir reproduções locais e evitar dependência de hotlink de terceiros.
4. **Cobrir os 328 itens** na grade (hoje mostra o recorte enriquecido de 95).
5. **Página de método/publicações** e integração com a genealogia (`genealogia-alegoria-feminina.md`).
6. Revisão terminológica ABNT perto da defesa (não bloqueante agora).

## 8. Limitações e riscos

- **Recorte de imagens:** só 84/95 itens têm URL de reprodução; o corpus completo (328) aparece apenas
  como estatística, não como grade. Marcado claramente como "recorte inicial".
- **Hotlink de terceiros:** algumas fontes (Numista) bloqueiam hotlink → imagem cai no placeholder.
  Mitigação futura: baixar/servir imagens de domínio público localmente.
- **`vercel.json` alterado:** mudou o diretório de deploy de `corpus` para `site` e removeu o gate de
  branch. Se houver deploy do explorador antigo em produção, esta mudança o substitui — revisar antes de push.
- **Sparse checkout foi desabilitado** para materializar os dados; nenhuma alteração foi commitada/pushada.
