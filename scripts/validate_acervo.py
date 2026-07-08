#!/usr/bin/env python3
"""Validate the Mnemosyne Viva corpus JSON and image URLs.

The script is designed for GitHub Actions and uses only the Python standard
library. It writes a Markdown report and, when running in Actions, exposes
summary values via GITHUB_OUTPUT.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IMAGE_KEY_HINTS = (
    "image",
    "imagem",
    "thumbnail",
    "thumb",
    "media",
    "picture",
    "iiif_image",
)

IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".avif",
    ".tif",
    ".tiff",
    ".jp2",
)

HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


@dataclass(frozen=True)
class ImageUrl:
    item_id: str
    title: str
    field: str
    url: str


@dataclass(frozen=True)
class UrlCheck:
    item_id: str
    title: str
    field: str
    url: str
    ok: bool
    status: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate corpus JSON and check image URLs."
    )
    parser.add_argument(
        "--json",
        default="site/data/corpus-data-enriched.json",
        help="Path to the enriched corpus JSON file.",
    )
    parser.add_argument(
        "--report",
        default="acervo-validation-report.md",
        help="Path for the Markdown report.",
    )
    parser.add_argument(
        "--schema",
        default="schemas/corpus-data-enriched.schema.json",
        help="Path to the JSON Schema used to validate the corpus structure.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout per request, in seconds.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Maximum number of concurrent URL checks.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry attempts per URL after the first failure.",
    )
    return parser.parse_args()


def write_outputs(**values: Any) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def load_json(path: Path) -> tuple[bool, Any, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return True, json.load(handle), ""
    except FileNotFoundError:
        return False, None, f"Arquivo não encontrado: `{path}`"
    except json.JSONDecodeError as exc:
        return (
            False,
            None,
            f"JSON inválido em linha {exc.lineno}, coluna {exc.colno}: {exc.msg}",
        )


def validate_schema(data: Any, schema_path: Path) -> tuple[bool, list[str], str]:
    """Valida ``data`` contra o JSON Schema.

    Usa ``jsonschema`` quando disponível; caso contrário aplica um validador
    mínimo (campos obrigatórios + padrões de id/url) derivado do próprio schema,
    para não depender de bibliotecas externas em ambientes restritos.

    Retorna (ok, lista_de_erros, modo).
    """
    if not schema_path.exists():
        return True, [], "ausente"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"Falha ao ler schema: {exc}"], "erro"

    try:
        import jsonschema  # type: ignore

        validator = jsonschema.Draft7Validator(schema)
        errors = []
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
            loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"{loc}: {err.message}")
        return (not errors), errors, "jsonschema"
    except ModuleNotFoundError:
        ok, errors = _validate_minimal(data, schema)
        return ok, errors, "stdlib"


def _validate_minimal(data: Any, schema: dict[str, Any]) -> tuple[bool, list[str]]:
    item_def = schema.get("definitions", {}).get("corpusItem", {})
    required = item_def.get("required", [])
    props = item_def.get("properties", {})
    pattern_fields = {
        field: re.compile(spec["pattern"])
        for field, spec in props.items()
        if isinstance(spec, dict) and "pattern" in spec
    }
    errors: list[str] = []
    if not isinstance(data, list):
        return False, ["<root>: esperado um array de itens"]
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"[{index}]: item não é um objeto")
            continue
        for field in required:
            if field not in item:
                errors.append(f"[{index}].{field}: campo obrigatório ausente")
        for field, pattern in pattern_fields.items():
            value = item.get(field)
            if isinstance(value, str) and not pattern.search(value):
                errors.append(
                    f"[{index}].{field}: '{value}' não corresponde ao padrão {pattern.pattern}"
                )
    return (not errors), errors


def records_from_data(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "records", "data", "corpus"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def looks_like_image_field(field_path: str, value: str) -> bool:
    lower_field = field_path.lower()
    lower_value = value.lower().split("?", 1)[0].split("#", 1)[0]
    return any(hint in lower_field for hint in IMAGE_KEY_HINTS) or lower_value.endswith(
        IMAGE_EXTENSIONS
    )


def walk_urls(value: Any, field_path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            next_path = f"{field_path}.{key}" if field_path else str(key)
            found.extend(walk_urls(child, next_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            next_path = f"{field_path}[{index}]"
            found.extend(walk_urls(child, next_path))
    elif isinstance(value, str) and HTTP_URL_RE.match(value.strip()):
        url = value.strip()
        if looks_like_image_field(field_path, url):
            found.append((field_path or "value", url))
    return found


def item_label(item: dict[str, Any], index: int) -> tuple[str, str]:
    item_id = str(
        item.get("id")
        or item.get("item_id")
        or item.get("slug")
        or item.get("identifier")
        or f"item-{index + 1}"
    )
    title = str(item.get("title") or item.get("titulo") or item.get("name") or item_id)
    return item_id, title


def collect_image_urls(records: list[dict[str, Any]]) -> list[ImageUrl]:
    urls: list[ImageUrl] = []
    seen: set[tuple[str, str, str]] = set()
    for index, item in enumerate(records):
        item_id, title = item_label(item, index)
        for field, url in walk_urls(item):
            key = (item_id, field, url)
            if key in seen:
                continue
            seen.add(key)
            urls.append(ImageUrl(item_id=item_id, title=title, field=field, url=url))
    return urls


def request_status(url: str, method: str, timeout: float) -> tuple[int | None, str]:
    request = urllib.request.Request(
        url,
        method=method,
        headers={
            # Browser-like User-Agent. Several digital archives (notably
            # gallica.bnf.fr) run a WAF that returns 403 to any non-browser
            # User-Agent — a self-identifying bot string was blocked outright,
            # which produced ~30 false "broken" 403s in the acervo report. A
            # standard browser UA restores 200 for those IIIF endpoints.
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,pt;q=0.7",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if method == "GET":
            response.read(1024)
        return response.status, response.reason


def check_one(image_url: ImageUrl, timeout: float, retries: int) -> UrlCheck:
    last_detail = ""
    last_status = "erro"
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(2 * attempt, 6))
        try:
            status, reason = request_status(image_url.url, "HEAD", timeout)
            if status == 200:
                return UrlCheck(
                    **image_url.__dict__,
                    ok=True,
                    status="200",
                    detail="OK via HEAD",
                )
            last_status = str(status or "sem status")
            last_detail = f"HEAD retornou {status} {reason}".strip()
        except urllib.error.HTTPError as exc:
            last_status = str(exc.code)
            last_detail = f"HEAD retornou HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            last_status = "erro"
            last_detail = f"HEAD falhou: {type(exc).__name__}: {exc}"

        try:
            status, reason = request_status(image_url.url, "GET", timeout)
            if status == 200:
                return UrlCheck(
                    **image_url.__dict__,
                    ok=True,
                    status="200",
                    detail="OK via GET",
                )
            last_status = str(status or "sem status")
            last_detail = f"GET retornou {status} {reason}".strip()
        except urllib.error.HTTPError as exc:
            last_status = str(exc.code)
            last_detail = f"GET retornou HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            last_status = "erro"
            last_detail = f"GET falhou: {type(exc).__name__}: {exc}"

    return UrlCheck(
        **image_url.__dict__,
        ok=False,
        status=last_status,
        detail=last_detail,
    )


def check_urls(
    image_urls: list[ImageUrl], timeout: float, workers: int, retries: int
) -> list[UrlCheck]:
    if not image_urls:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(check_one, image_url, timeout, retries)
            for image_url in image_urls
        ]
        return [future.result() for future in concurrent.futures.as_completed(futures)]


def action_run_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return ""


def write_report(
    report_path: Path,
    json_path: Path,
    json_valid: bool,
    json_error: str,
    record_count: int,
    checks: list[UrlCheck],
    schema_valid: bool = True,
    schema_errors: list[str] | None = None,
    schema_mode: str = "ausente",
) -> None:
    schema_errors = schema_errors or []
    broken = sorted(
        [check for check in checks if not check.ok],
        key=lambda item: (item.item_id, item.field, item.url),
    )
    checked_count = len(checks)
    ok_count = checked_count - len(broken)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    run_url = action_run_url()

    lines = [
        "# Relatório de validação do acervo",
        "",
        f"Gerado em: {timestamp}",
        f"Arquivo validado: `{json_path}`",
    ]
    if run_url:
        lines.append(f"Execução: {run_url}")
    lines.extend(
        [
            "",
            "## Resumo",
            "",
            f"- JSON válido: {'sim' if json_valid else 'não'}",
            f"- Schema válido: {'sim' if schema_valid else 'não'} (validador: {schema_mode})",
            f"- Itens no acervo: {record_count}",
            f"- URLs de imagem verificadas: {checked_count}",
            f"- URLs acessíveis com status 200: {ok_count}",
            f"- Problemas encontrados: "
            f"{len(broken) + (0 if json_valid else 1) + (0 if schema_valid else len(schema_errors))}",
            "",
        ]
    )

    if not json_valid:
        lines.extend(["## Erro de JSON", "", json_error, ""])

    if not schema_valid:
        lines.extend(["## Erros de schema", ""])
        for err in schema_errors[:50]:
            safe_err = err.replace("|", "\\|")
            lines.append(f"- {safe_err}")
        if len(schema_errors) > 50:
            lines.append(f"- … e mais {len(schema_errors) - 50} erro(s).")
        lines.append("")

    if broken:
        lines.extend(
            [
                "## Itens quebrados ou inacessíveis",
                "",
                "| Item | Campo | Status | Detalhe | URL |",
                "|---|---|---:|---|---|",
            ]
        )
        for check in broken:
            safe_title = check.title.replace("|", "\\|")
            safe_detail = check.detail.replace("|", "\\|")
            lines.append(
                f"| `{check.item_id}` {safe_title} | `{check.field}` | "
                f"{check.status} | {safe_detail} | {check.url} |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "## Resultado",
                "",
                "Nenhum item quebrado ou inacessível foi detectado nesta execução.",
                "",
            ]
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    json_path = Path(args.json)
    report_path = Path(args.report)
    schema_path = Path(args.schema)

    json_valid, data, json_error = load_json(json_path)
    if not json_valid:
        write_report(
            report_path=report_path,
            json_path=json_path,
            json_valid=False,
            json_error=json_error,
            record_count=0,
            checks=[],
            schema_valid=False,
            schema_errors=["JSON inválido: schema não avaliado."],
            schema_mode="ausente",
        )
        write_outputs(
            json_valid="false",
            schema_valid="false",
            checked_count=0,
            broken_count=1,
            schema_error_count=1,
        )
        print(json_error, file=sys.stderr)
        return 0

    schema_valid, schema_errors, schema_mode = validate_schema(data, schema_path)

    records = records_from_data(data)
    image_urls = collect_image_urls(records)
    checks = check_urls(
        image_urls=image_urls,
        timeout=args.timeout,
        workers=args.workers,
        retries=args.retries,
    )
    broken_count = sum(1 for check in checks if not check.ok)
    write_report(
        report_path=report_path,
        json_path=json_path,
        json_valid=True,
        json_error="",
        record_count=len(records),
        checks=checks,
        schema_valid=schema_valid,
        schema_errors=schema_errors,
        schema_mode=schema_mode,
    )
    write_outputs(
        json_valid="true",
        schema_valid="true" if schema_valid else "false",
        checked_count=len(checks),
        broken_count=broken_count,
        schema_error_count=len(schema_errors),
    )
    print(
        f"JSON válido. Schema: {'ok' if schema_valid else 'FALHOU'} ({schema_mode}). "
        f"Itens: {len(records)}. URLs verificadas: {len(checks)}. "
        f"Problemas de URL: {broken_count}. Erros de schema: {len(schema_errors)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
