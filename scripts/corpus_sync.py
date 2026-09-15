#!/usr/bin/env python3
"""Gera a projeção editorial estática de iconocracia.com.

O corpus fornece os fatos canônicos. ``publication.json`` decide o recorte
publicado, aliases, imagens, direitos, análise pública e constelações.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "corpus-input.schema.json"
DEFAULT_PUBLICATION = ROOT / "site" / "data" / "publication.json"
DEFAULT_LEGACY = ROOT / "site" / "data" / "corpus-data-enriched.json"
DEFAULT_OUT = ROOT / "site" / "data"

COUNTRY_PT = {
    "france": "França", "brazil": "Brasil", "united states": "Estados Unidos",
    "germany": "Alemanha", "united kingdom": "Reino Unido", "italy": "Itália",
    "portugal": "Portugal", "belgium": "Bélgica", "netherlands": "Países Baixos",
    "spain": "Espanha", "austria": "Áustria", "denmark": "Dinamarca",
    "mexico": "México", "argentina": "Argentina", "switzerland": "Suíça",
    "uruguay": "Uruguai", "chile": "Chile", "eua": "Estados Unidos",
    "usa": "Estados Unidos", "us": "Estados Unidos",
}
REGIME_PT = {
    "fundacional": "Fundacional", "normativo": "Normativo",
    "militar": "Militar", "contra-alegoria": "Contra-alegoria",
}
MOTIF_NOISE = {
    "alegoria feminina", "female allegory", "fundacional", "normativo",
    "militar", "contra-alegoria", "contra-allegoria",
}
PUBLISH_REQUIRED_IMAGE_FIELDS = {"path", "source_url", "license", "credit", "alt"}


def norm_country(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Outros"
    key = raw.lower()
    for source, target in COUNTRY_PT.items():
        if key == source or key.startswith(source + " ("):
            return target
    return raw


def normalize_url(value: Any) -> str:
    url = str(value or "").strip().replace("http://", "https://").rstrip("/")
    if url.endswith(".item"):
        url = url[:-5]
    return url


def validate_records(records: Any, schema_path: pathlib.Path) -> None:
    if not isinstance(records, list):
        raise ValueError("O corpus deve ser um array JSON.")
    try:
        import jsonschema  # type: ignore
    except ModuleNotFoundError:
        jsonschema = None
    if jsonschema and schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(
            jsonschema.Draft7Validator(schema).iter_errors(records),
            key=lambda error: list(error.absolute_path),
        )
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


def validate_publication(publication: Any) -> None:
    if not isinstance(publication, dict) or not isinstance(publication.get("items"), list):
        raise ValueError("publication.json deve ser um objeto com array items.")
    if not str(publication.get("corpus_commit") or ""):
        raise ValueError("publication.json não informa corpus_commit.")
    seen: set[str] = set()
    for entry in publication["items"]:
        key = str(entry.get("canonical_id") or entry.get("legacy_record_id") or "")
        if not key:
            raise ValueError("Entrada editorial sem canonical_id ou legacy_record_id.")
        if key in seen:
            raise ValueError(f"Entrada editorial duplicada: {key}")
        seen.add(key)
        if entry.get("editorial_status") not in {"review", "published", "withheld"}:
            raise ValueError(f"Status editorial inválido em {key}.")
        if entry.get("editorial_status") != "published" or entry.get("grandfathered"):
            continue
        image = entry.get("image") or {}
        missing = sorted(field for field in PUBLISH_REQUIRED_IMAGE_FIELDS if not image.get(field))
        for field in ("approved_by", "approved_at"):
            if not entry.get(field):
                missing.append(field)
        if str(image.get("path") or "").startswith(("http://", "https://")):
            missing.append("image.path local")
        if missing:
            raise ValueError(f"Item novo {key} não pode ser publicado; faltam: {', '.join(missing)}")


def index_records(records: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, dict]]:
    return (
        {str(item["id"]): item for item in records},
        {normalize_url(item.get("url")): item for item in records if normalize_url(item.get("url"))},
    )


def resolve_entry(
    entry: dict[str, Any], records: list[dict[str, Any]], legacy: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    by_id, by_url = index_records(records)
    legacy_by_id = {str(item.get("id")): item for item in legacy}
    canonical_id = str(entry.get("canonical_id") or "")
    if canonical_id in by_id:
        return by_id[canonical_id], canonical_id
    source_url = normalize_url(entry.get("source_url"))
    if source_url and source_url in by_url:
        return by_url[source_url], str(by_url[source_url]["id"])
    for alias in entry.get("legacy_ids") or []:
        old = legacy_by_id.get(str(alias))
        if old:
            match = by_url.get(normalize_url(old.get("url")))
            if match:
                return match, str(match["id"])
    legacy_id = str(entry.get("legacy_record_id") or "")
    if entry.get("grandfathered") and legacy_id in legacy_by_id:
        return legacy_by_id[legacy_id], legacy_id
    raise ValueError(f"Entrada editorial sem correspondência canônica explícita: {canonical_id or legacy_id}")


def transform_item(source: dict[str, Any], editorial: dict[str, Any] | None = None) -> dict[str, Any]:
    editorial = editorial or {}
    item = {**source, **(editorial.get("overrides") or {})}
    regime = str(item.get("regime") or "").lower()
    raw_motifs = item.get("motif") or item.get("tags") or []
    motifs = [
        str(value).strip() for value in raw_motifs
        if str(value).strip() and str(value).strip().lower() not in MOTIF_NOISE
    ]
    image_meta = editorial.get("image") or {}
    image = str(image_meta.get("path") or item.get("local_image_path") or
                item.get("thumbnail_url") or item.get("url_image_download") or "")
    canonical_id = str(editorial.get("canonical_id") or item["id"])
    result = {
        "id": canonical_id,
        "slug": editorial.get("slug") or canonical_id.lower(),
        "legacy_ids": editorial.get("legacy_ids") or [],
        "titulo": item.get("title") or item.get("titulo") or "(sem título)",
        "pais": norm_country(item.get("country_pt") or item.get("country")),
        "autoria": item.get("creator") or item.get("author") or "",
        "instituicao": item.get("institution") or item.get("sourceInstitution") or item.get("source_archive") or "",
        "data": str(item.get("date") or item.get("dateText") or item.get("year") or ""),
        "suporte": item.get("medium") or item.get("support") or "",
        "regime": REGIME_PT.get(regime, regime.capitalize()),
        "motivos": motifs,
        "descricao": (item.get("description") or item.get("shortDescription") or "")[:600],
        "descricao_longa": item.get("longDescription") or item.get("description") or "",
        "direitos": image_meta.get("license") or item.get("rights") or "",
        "credito": image_meta.get("credit") or "",
        "texto_alternativo": image_meta.get("alt") or item.get("title") or "",
        "fonte_url": image_meta.get("catalog_url") or item.get("url") or editorial.get("source_url") or "",
        "imagem_fonte": image_meta.get("source_url") or "",
        "imagem": image,
        "tem_imagem": bool(image),
        "citacao": item.get("citation_abnt") or "",
        "analise_publica": editorial.get("public_analysis") or None,
        "constelacoes": editorial.get("constellations") or [],
    }
    if item.get("endurecimento_score") is not None:
        result["endurecimento_score"] = item["endurecimento_score"]
    if item.get("indicadores") is not None:
        result["indicadores"] = item["indicadores"]
    return result


def build_stats(
    items: list[dict[str, Any]], source_count: int, version: str, generated_at: str,
) -> dict[str, Any]:
    countries = Counter(item["pais"] for item in items)
    regimes = Counter(item["regime"] or "Não classificado" for item in items)
    years: list[int] = []
    for item in items:
        for token in item["data"].replace("–", " ").replace("-", " ").replace("/", " ").split():
            if token.isdigit() and 1000 <= int(token) <= 2100:
                years.append(int(token))
                break
    return {
        "total": len(items),
        "paises": len([country for country in countries if country != "Outros"]),
        "com_imagem": sum(item["tem_imagem"] for item in items),
        "periodo": {"min": min(years) if years else None, "max": max(years) if years else None},
        "por_pais": [{"pais": key, "n": value} for key, value in countries.most_common()],
        "por_regime": [{"regime": key, "chave": key.lower(), "n": value} for key, value in regimes.most_common()],
        "motivos": [{"motivo": key, "n": value} for key, value in Counter(m for item in items for m in item["motivos"]).most_common(10)],
        "meta": {
            "source_count": source_count,
            "published_count": len(items),
            "generated_at": generated_at,
            "corpus_version": version,
        },
    }


def build_constellations(
    definitions: list[dict[str, Any]], items: list[dict[str, Any]], include_review: bool = False,
) -> list[dict[str, Any]]:
    visible_ids = {item["id"] for item in items}
    result = []
    for definition in definitions:
        if definition.get("editorial_status") != "published" and not include_review:
            continue
        ordered = [item_id for item_id in definition.get("item_ids", []) if item_id in visible_ids]
        if not ordered:
            continue
        result.append({**definition, "item_ids": ordered})
    return result


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_corpus(path: pathlib.Path | None, publication: dict[str, Any]) -> list[dict[str, Any]]:
    if path:
        return load_json(path)
    commit = publication["corpus_commit"]
    url = f"https://raw.githubusercontent.com/anavvanzin/iconocracy-corpus/{commit}/corpus/corpus-data.json"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def generate(
    records: list[dict[str, Any]], publication: dict[str, Any], legacy: list[dict[str, Any]],
    *, include_review: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    validate_publication(publication)
    statuses = {"published", "review"} if include_review else {"published"}
    items = []
    for entry in publication["items"]:
        if entry["editorial_status"] not in statuses:
            continue
        source, resolved_id = resolve_entry(entry, records, legacy)
        normalized = {**entry, "canonical_id": entry.get("canonical_id") or resolved_id}
        items.append(transform_item(source, normalized))
    stats = build_stats(
        items, len(records), publication["corpus_commit"], publication.get("generated_at", ""),
    )
    constellations = build_constellations(
        publication.get("constellations") or [], items, include_review=include_review,
    )
    return items, stats, constellations


def write_outputs(out: pathlib.Path, items: list[dict], stats: dict, constellations: list[dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, value in (("acervo.json", items), ("stats.json", stats), ("constellations.json", constellations)):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=pathlib.Path)
    parser.add_argument("--publication", type=pathlib.Path, default=DEFAULT_PUBLICATION)
    parser.add_argument("--legacy", type=pathlib.Path, default=DEFAULT_LEGACY)
    parser.add_argument("--schema", type=pathlib.Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--include-review", action="store_true")
    args = parser.parse_args()
    try:
        publication = load_json(args.publication)
        records = load_corpus(args.corpus, publication)
        legacy = load_json(args.legacy)
        validate_records(records, args.schema)
        items, stats, constellations = generate(
            records, publication, legacy, include_review=args.include_review,
        )
        write_outputs(args.out, items, stats, constellations)
        print(f"Sincronizados {len(items)} de {len(records)} itens; {len(constellations)} constelações.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"[corpus_sync] erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
