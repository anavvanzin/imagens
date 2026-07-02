#!/usr/bin/env python3
"""Gera os dados estáticos do site Mnemosyne Viva a partir do corpus do repositório.

Fontes (resolvidas de forma robusta, na ordem indicada):
  - corpus/corpus-data.json           -> corpus operacional completo (contagens/estatísticas)
  - corpus/corpus-data-enriched.json  -> subconjunto curado com thumbnails reais de arquivos

Quando o diretório ``corpus/`` não está presente (por exemplo, neste repositório
público autônomo, que só distribui os dados já publicados), o script recorre a
``site/data/corpus-data-enriched.json`` como fonte tanto do corpus quanto do
subconjunto enriquecido. Assim ``build_data.py`` continua funcionando sem falhas
crípticas e permanece idempotente sobre os dados já publicados.

Saídas:
  - site/data/acervo.json  -> itens para a grade do acervo (com imagem quando disponível)
  - site/data/stats.json   -> agregados para a homepage e o cabeçalho do acervo

Metadados iconográficos (metodologia ICONOCRACIA) são opcionais: quando um item
enriquecido traz o objeto ``iconographic_metadata``, ele é preservado no item
gerado do acervo, sem afetar os campos de filtro já consumidos pelo frontend.

Uso: python scripts/build_data.py  (a partir da raiz do repositório)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "site" / "data"

# Fonte primária (repo de trabalho) e fallback público (este repo autônomo).
CORPUS_CANDIDATES = [
    ROOT / "corpus" / "corpus-data.json",
    ROOT / "site" / "data" / "corpus-data-enriched.json",
]
ENRICHED_CANDIDATES = [
    ROOT / "corpus" / "corpus-data-enriched.json",
    ROOT / "site" / "data" / "corpus-data-enriched.json",
]

# Campo aninhado, opcional, com os metadados iconográficos da metodologia ICONOCRACIA.
ICONOGRAPHIC_KEY = "iconographic_metadata"

COUNTRY_PT = {
    "France": "França", "Brazil": "Brasil", "United States": "Estados Unidos",
    "Germany": "Alemanha", "United Kingdom": "Reino Unido", "Italy": "Itália",
    "Portugal": "Portugal", "Belgium": "Bélgica", "Netherlands": "Países Baixos",
    "Spain": "Espanha", "Austria": "Áustria", "Denmark": "Dinamarca",
    "Mexico": "México", "Argentina": "Argentina", "Switzerland": "Suíça",
    "Uruguay": "Uruguai", "CL": "Chile",
}

REGIME_PT = {
    "fundacional": "Fundacional", "normativo": "Normativo",
    "militar": "Militar", "contra-alegoria": "Contra-alegoria",
}


def norm_country(raw):
    if not raw:
        return "Outros"
    raw = raw.strip()
    for k, v in COUNTRY_PT.items():
        if raw.lower() == k.lower() or raw.lower() == v.lower():
            return v
    # variações "France (held in Austria)" etc.
    for k, v in COUNTRY_PT.items():
        if raw.lower().startswith(k.lower()):
            return v
    return raw


def resolve_source(candidates: list[pathlib.Path], label: str) -> pathlib.Path:
    """Retorna o primeiro caminho existente; erro claro se nenhum existir."""
    for path in candidates:
        if path.exists():
            return path
    tried = "\n  - ".join(str(p) for p in candidates)
    raise SystemExit(
        f"[build_data] Nenhuma fonte de {label} encontrada. Caminhos testados:\n  - {tried}\n"
        "Coloque os dados do corpus em corpus/ ou garanta o JSON público em site/data/."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=pathlib.Path, default=None,
                        help="JSON do corpus operacional completo (opcional).")
    parser.add_argument("--enriched", type=pathlib.Path, default=None,
                        help="JSON do subconjunto curado enriquecido (opcional).")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT,
                        help="Diretório de saída para stats.json e acervo.json.")
    return parser.parse_args()


def build_stats(corpus: list[dict]) -> dict:
    countries = Counter(norm_country(x.get("country")) for x in corpus)
    regimes = Counter((x.get("regime") or "não classificado") for x in corpus)
    motifs: Counter = Counter()
    for x in corpus:
        for m in (x.get("motif") or []):
            m = (m or "").strip()
            # descarta ruído técnico de rótulos pré-iconográficos
            if m and not m.startswith("descricao_") and not m.startswith("figura ") \
               and m.lower() not in {"alegoria feminina", "allégorie féminine"}:
                motifs[m] += 1

    years = []
    for x in corpus:
        d = str(x.get("date") or "")
        for tok in d.replace("-", " ").replace("/", " ").split():
            if tok.isdigit() and 1700 <= int(tok) <= 2000:
                years.append(int(tok))
                break

    return {
        "total": len(corpus),
        "paises": len([c for c in countries if c != "Outros"]),
        "com_imagem": sum(1 for x in corpus if x.get("thumbnail_url")),
        "periodo": {"min": min(years) if years else None, "max": max(years) if years else None},
        "por_pais": [{"pais": p, "n": n} for p, n in countries.most_common()],
        "por_regime": [
            {"regime": REGIME_PT.get(r, r.capitalize()), "chave": r, "n": n}
            for r, n in regimes.most_common()
        ],
        "motivos": [{"motivo": m, "n": n} for m, n in motifs.most_common(10)],
    }


def build_items(enriched: list[dict]) -> list[dict]:
    itens = []
    for x in enriched:
        img = x.get("thumbnail_url") or x.get("url_image_download") or ""
        item = {
            "id": x.get("id"),
            "titulo": x.get("title") or "(sem título)",
            "pais": norm_country(x.get("country_pt") or x.get("country")),
            "autoria": x.get("creator") or "",
            "instituicao": x.get("institution") or x.get("source_archive") or "",
            "data": str(x.get("date") or x.get("year") or ""),
            "suporte": x.get("medium") or "",
            "regime": REGIME_PT.get((x.get("regime") or "").lower(), (x.get("regime") or "").capitalize()),
            "motivos": x.get("motif") or [],
            "descricao": (x.get("description") or "")[:600],
            "direitos": x.get("rights") or "",
            "fonte_url": x.get("url") or "",
            "imagem": img,
            "tem_imagem": bool(img),
            "citacao": x.get("citation_abnt") or "",
        }
        # Preserva metadados iconográficos quando presentes (opcional, não quebra filtros).
        iconografia = x.get(ICONOGRAPHIC_KEY)
        if isinstance(iconografia, dict) and iconografia:
            item[ICONOGRAPHIC_KEY] = iconografia
        itens.append(item)
    # imagens primeiro, depois por país
    itens.sort(key=lambda i: (not i["tem_imagem"], i["pais"], i["titulo"]))
    return itens


def main() -> int:
    args = parse_args()
    corpus_path = args.corpus or resolve_source(CORPUS_CANDIDATES, "corpus")
    enriched_path = args.enriched or resolve_source(ENRICHED_CANDIDATES, "enriched")

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    enriched = json.loads(enriched_path.read_text(encoding="utf-8"))

    stats = build_stats(corpus)
    itens = build_items(enriched)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "acervo.json").write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"fonte corpus:   {corpus_path}")
    print(f"fonte enriched: {enriched_path}")
    print(f"stats.json: total={stats['total']} paises={stats['paises']} com_imagem={stats['com_imagem']}")
    com_icono = sum(1 for i in itens if ICONOGRAPHIC_KEY in i)
    print(f"acervo.json: {len(itens)} itens ({sum(i['tem_imagem'] for i in itens)} com imagem, "
          f"{com_icono} com metadados iconográficos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
