# Mnemosyne Viva

Site editorial estático para o novo `iconocracia.com`, concebido como casa pública do acervo, do atlas e da pesquisa ICONOCRACIA.

## Estrutura

- `site/index.html` — homepage.
- `site/sobre.html` — apresentação do projeto, método e conceitos.
- `site/acervo.html` — recorte inicial do acervo, com busca e filtros.
- `site/assets/` — CSS e JavaScript.
- `site/data/` — JSONs estáticos usados pela homepage e pelo acervo.
- `scripts/build_data.py` — regenera `site/data/*.json` a partir dos dados do corpus original.
- `scripts/validate_acervo.py` — valida o JSON enriquecido (estrutura + JSON Schema) e verifica URLs de imagem.
- `scripts/measure_performance.py` — mede o tempo de resposta das imagens e mantém o histórico em `site/data/performance.json`.
- `schemas/corpus-data-enriched.schema.json` — JSON Schema (draft-07) do corpus enriquecido.
- `.github/workflows/validate-acervo.yml` — validação automática semanal do acervo, com resumo via issue quando houver item quebrado ou fora do schema.
- `.github/workflows/performance-acervo.yml` — medição mensal (dia 1) do tempo de resposta das imagens.
- `AUDITORIA-ARQUITETURA.md` — auditoria do repositório de origem e arquitetura proposta.

## Dados e schema

O arquivo `site/data/corpus-data-enriched.json` é um array de itens do acervo. Sua
estrutura é documentada em [`schemas/corpus-data-enriched.schema.json`](schemas/corpus-data-enriched.schema.json)
(JSON Schema draft-07). Campos centrais consumidos pelo frontend (`id`, `title`,
`country`/`country_pt`, `regime`, `motif`, `url`, `thumbnail_url`, etc.) são
preservados; novos itens devem seguir o padrão do schema.

Metadados iconográficos da metodologia ICONOCRACIA são **opcionais** e ficam num
objeto aninhado `iconographic_metadata` (campos: `allegorical_figure`, `iconclass`,
`attributes`, `pathosformel`, `visual_regime`, `state_function`,
`contract_visual_sexual`, `coloniality_of_seeing`, `purification_indicators`,
`endurecimento_score`, `atlas_panel`). Quando presente, `build_data.py` preserva
esse objeto em `site/data/acervo.json` sem afetar os filtros existentes.

Validação local (o `jsonschema` é opcional; sem ele, um validador stdlib mínimo é usado):

```bash
pip install jsonschema  # opcional
python scripts/validate_acervo.py --json site/data/corpus-data-enriched.json
```

## Monitoramento de performance

`scripts/measure_performance.py` mede o tempo de carregamento (HTTP GET completo)
de cada imagem acessível do corpus, calcula a média e anexa uma execução ao
histórico determinístico `site/data/performance.json` (array `runs` com
`timestamp`, `checked_count`, `accessible_count`, `average_response_ms`,
`threshold_ms`, `status` e `top_slowest`). O workflow `performance-acervo.yml` roda
todo dia 1 (09:00 São Paulo), comita o histórico com `[skip ci]` e abre/atualiza
uma issue com os 10 itens mais lentos quando a média ultrapassa 2000 ms.

```bash
python scripts/measure_performance.py --threshold-ms 2000 --top 10
```

## Deploy

O site é HTML/CSS/JS puro, sem etapa de build. No Vercel, usar framework `Other` ou `null`, sem `buildCommand` e com `outputDirectory` configurado como `site`.
