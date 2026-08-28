#!/usr/bin/env python3
"""Validate and transform the canonical ICONOCRACIA corpus for the static site."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "site/data/corpus-data-enriched.json"
DEFAULT_SCHEMA = ROOT / "schemas/corpus-input.schema.json"
DEFAULT_OUT = ROOT / "site/data"

COUNTRY_PT = {
    "france": "França", "brazil": "Brasil", "united states": "Estados Unidos",
    "germany": "Alemanha", "united kingdom": "Reino Unido", "italy": "Itália",
    "portugal": "Portugal", "belgium": "Bélgica", "netherlands": "Países Baixos",
    "spain": "Espanha", "austria": "Áustria", "denmark": "Dinamarca",
    "mexico": "México", "argentina": "Argentina", "switzerland": "Suíça",
    "uruguay": "Uruguai", "chile": "Chile", "eua": "Estados Unidos",
    "usa": "Estados Unidos",
}
REGIME_PT = {
    "fundacional": "Fundacional", "normativo": "Normativo",
    "militar": "Militar", "contra-alegoria": "Contra-alegoria",
}
MOTIF_NOISE = {"alegoria feminina", "female allegory", "fundacional",
               "normativo", "militar", "contra-alegoria", "contra-allegoria"}


def norm_country(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Outros"
    key = raw.lower()
    for source, target in COUNTRY_PT.items():
        if key == source or key.startswith(source + " ("):
            return target
    return raw


def image_for(item: dict[str, Any]) -> str:
    local = item.get("local_image_path")
    if local:
        return str(local)
    for file in item.get("files") or []:
        if (file.get("role") in (None, "primary", "thumbnail")
                and file.get("type") == "image" and file.get("path")):
            return str(file["path"])
    for key in ("thumbnail_url", "url_iiif", "url_image_download"):
        if item.get(key):
            return str(item[key])
    return ""


def validate_records(records: Any, schema_path: pathlib.Path) -> None:
    if not isinstance(records, list):
        raise ValueError("O corpus deve ser um array JSON.")
    try:
        import jsonschema  # type: ignore
    except ModuleNotFoundError:
        jsonschema = None
    if jsonschema and schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(records),
                        key=lambda error: list(error.absolute_path))
        if errors:
            details = "; ".join(
                f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
                for error in errors[:10]
            )
            raise ValueError(f"Corpus inválido segundo o schema: {details}")
    seen: set[str] = set()
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} não é um objeto.")
        item_id = str(item.get("id") or "")
        if not item_id:
            raise ValueError(f"Item {index} não possui id.")
        if item_id in seen:
            raise ValueError(f"ID duplicado no corpus: {item_id}")
        seen.add(item_id)


def transform_item(item: dict[str, Any]) -> dict[str, Any]:
    regime = str(item.get("regime") or "").lower()
    motifs = [
        str(m).strip() for m in (item.get("motif") or item.get("tags") or [])
        if str(m).strip() and str(m).strip().lower() not in MOTIF_NOISE
    ]
    image = image_for(item)
    output = {
        "id": str(item["id"]),
        "titulo": item.get("title") or item.get("titulo") or "(sem título)",
        "pais": norm_country(item.get("country_pt") or item.get("country")),
        "autoria": item.get("creator") or item.get("author") or "",
        "instituicao": item.get("institution") or item.get("sourceInstitution") or "",
        "data": str(item.get("date") or item.get("dateText") or item.get("year") or ""),
        "suporte": item.get("medium") or item.get("support") or "",
        "regime": REGIME_PT.get(regime, regime.capitalize()),
        "motivos": motifs,
        "descricao": (item.get("description") or item.get("shortDescription") or "")[:600],
        "descricao_longa": item.get("longDescription") or item.get("description") or "",
        "notas_curatoriais": item.get("curatorialNotes") or "",
        "direitos": item.get("rights") or "",
        "fonte_url": item.get("url") or "",
        "imagem": image,
        "tem_imagem": bool(image),
        "citacao": item.get("citation_abnt") or "",
    }
    for key in ("iconographic_metadata", "endurecimento_score", "indicadores"):
        if item.get(key) is not None:
            output[key] = item[key]
    return output


def build_stats(items: list[dict[str, Any]], source_count: int, version: str) -> dict[str, Any]:
    countries = Counter(item["pais"] for item in items)
    regimes = Counter(item["regime"] or "Não classificado" for item in items)
    years = []
    for item in items:
        for token in item["data"].replace("-", " ").replace("/", " ").split():
            if token.isdigit() and 1000 <= int(token) <= 2100:
                years.append(int(token))
                break
    return {
        "total": len(items), "paises": len(countries - Counter({"Outros": countries["Outros"]})),
        "com_imagem": sum(item["tem_imagem"] for item in items),
        "periodo": {"min": min(years) if years else None, "max": max(years) if years else None},
        "por_pais": [{"pais": key, "n": value} for key, value in countries.most_common()],
        "por_regime": [{"regime": key, "chave": key.lower(), "n": value}
                       for key, value in regimes.most_common()],
        "motivos": [{"motivo": key, "n": value}
                    for key, value in Counter(m for item in items for m in item["motivos"]).most_common(10)],
        "meta": {"source_count": source_count, "published_count": len(items),
                 "generated_at": datetime.now(timezone.utc).isoformat(),
                 "corpus_version": version},
    }


def load_source(path: pathlib.Path | None, url: str | None) -> tuple[list[dict[str, Any]], str]:
    if url:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response), url
    source = path or DEFAULT_SOURCE
    return json.loads(source.read_text(encoding="utf-8")), str(source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=pathlib.Path)
    parser.add_argument("--source-url", help="Export versionado do corpus canônico.")
    parser.add_argument("--schema", type=pathlib.Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--status", default="published",
                        help="Status editorial a publicar; ausente no corpus upstream = publicado.")
    parser.add_argument("--version", default="working")
    args = parser.parse_args()
    try:
        records, source = load_source(args.corpus, args.source_url)
        validate_records(records, args.schema)
        selected = [item for item in records
                    if item.get("editorialStatus", args.status) == args.status]
        items = sorted((transform_item(item) for item in selected),
                       key=lambda item: (not item["tem_imagem"], item["pais"], item["titulo"]))
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "acervo.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        stats = build_stats(items, len(records), args.version)
        stats["meta"]["source"] = source
        (args.out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Sincronizados {len(items)} de {len(records)} itens.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"[corpus_sync] erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
