# Mnemosyne Viva

Site editorial estático para o novo `iconocracia.com`, concebido como casa pública do acervo, do atlas e da pesquisa ICONOCRACIA.

## Estrutura

- `site/index.html` — homepage.
- `site/sobre.html` — apresentação do projeto, método e conceitos.
- `site/acervo.html` — recorte inicial do acervo, com busca e filtros.
- `site/assets/` — CSS e JavaScript.
- `site/data/` — JSONs estáticos usados pela homepage e pelo acervo.
- `scripts/build_data.py` — regenera `site/data/*.json` a partir dos dados do corpus original.
- `scripts/validate_acervo.py` — valida o JSON enriquecido e verifica URLs de imagem.
- `.github/workflows/validate-acervo.yml` — validação automática semanal do acervo, com resumo via issue quando houver item quebrado.
- `AUDITORIA-ARQUITETURA.md` — auditoria do repositório de origem e arquitetura proposta.

## Deploy

O site é HTML/CSS/JS puro, sem etapa de build. No Vercel, usar framework `Other` ou `null`, sem `buildCommand` e com `outputDirectory` configurado como `site`.
