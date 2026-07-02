#!/usr/bin/env python3
"""Gera os dados estáticos do site Mnemosyne Viva a partir do corpus do repositório.

Fontes (somente conteúdo já presente no repo):
  - corpus/corpus-data.json           -> corpus operacional completo (contagens/estatísticas)
  - corpus/corpus-data-enriched.json  -> subconjunto curado com thumbnails reais de arquivos

Saídas:
  - site/data/acervo.json  -> itens para a grade do acervo (com imagem quando disponível)
  - site/data/stats.json   -> agregados para a homepage e o cabeçalho do acervo

Uso: python site/build_data.py  (a partir da raiz do repositório)
"""
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "corpus-data.json"
ENRICHED = ROOT / "corpus" / "corpus-data-enriched.json"
OUT = ROOT / "site" / "data"

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


def main():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    enriched = json.loads(ENRICHED.read_text(encoding="utf-8"))

    # ---- estatísticas do corpus operacional completo ----
    countries = Counter(norm_country(x.get("country")) for x in corpus)
    regimes = Counter((x.get("regime") or "não classificado") for x in corpus)
    motifs = Counter()
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

    stats = {
        "total": len(corpus),
        "paises": len([c for c in countries if c != "Outros"]),
        "com_imagem": sum(1 for x in enriched if x.get("thumbnail_url")),
        "periodo": {"min": min(years) if years else None, "max": max(years) if years else None},
        "por_pais": [
            {"pais": p, "n": n} for p, n in countries.most_common()
        ],
        "por_regime": [
            {"regime": REGIME_PT.get(r, r.capitalize()), "chave": r, "n": n}
            for r, n in regimes.most_common()
        ],
        "motivos": [{"motivo": m, "n": n} for m, n in motifs.most_common(10)],
    }

    # ---- itens do acervo (subconjunto curado enriquecido) ----
    itens = []
    for x in enriched:
        img = x.get("thumbnail_url") or x.get("url_image_download") or ""
        itens.append({
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
        })
    # imagens primeiro, depois por país
    itens.sort(key=lambda i: (not i["tem_imagem"], i["pais"], i["titulo"]))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "acervo.json").write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"stats.json: total={stats['total']} paises={stats['paises']} com_imagem={stats['com_imagem']}")
    print(f"acervo.json: {len(itens)} itens ({sum(i['tem_imagem'] for i in itens)} com imagem)")


if __name__ == "__main__":
    main()
