#!/usr/bin/env python3
"""Mede o tempo de resposta das imagens do acervo Mnemosyne Viva.

Percorre ``site/data/corpus-data-enriched.json``, mede o tempo de carregamento
(HTTP GET completo) de cada imagem acessível, calcula a média e mantém um
histórico determinístico em ``site/data/performance.json`` (array ``runs``).

Também escreve um relatório Markdown e, quando executado no GitHub Actions,
expõe valores de resumo via ``GITHUB_OUTPUT`` (média, status, se ultrapassou o
limite). Usa apenas a biblioteca padrão do Python.

Uso: python scripts/measure_performance.py [--threshold-ms 2000]
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
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
# Campos que apontam para a reprodução visual do item, em ordem de preferência.
IMAGE_FIELDS = ("thumbnail_url", "url_image_download", "url_iiif")


@dataclass(frozen=True)
class ImageTarget:
    item_id: str
    title: str
    field: str
    url: str


@dataclass(frozen=True)
class Measurement:
    id: str
    title: str
    field: str
    url: str
    accessible: bool
    response_ms: int | None
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mede tempos de resposta das imagens do acervo.")
    parser.add_argument("--json", default="site/data/corpus-data-enriched.json",
                        help="Caminho do corpus enriquecido.")
    parser.add_argument("--history", default="site/data/performance.json",
                        help="Arquivo histórico de performance (array runs).")
    parser.add_argument("--report", default="acervo-performance-report.md",
                        help="Caminho do relatório Markdown.")
    parser.add_argument("--threshold-ms", type=float, default=2000.0,
                        help="Limite de média (ms) acima do qual dispara alerta.")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="Timeout HTTP por requisição, em segundos.")
    parser.add_argument("--workers", type=int, default=8,
                        help="Número máximo de medições concorrentes.")
    parser.add_argument("--retries", type=int, default=1,
                        help="Tentativas extras por URL após a primeira falha.")
    parser.add_argument("--top", type=int, default=10,
                        help="Quantidade de itens mais lentos no relatório.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limita o nº de itens medidos (0 = todos). Útil para smoke tests.")
    return parser.parse_args()


def write_outputs(**values: Any) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("items", "records", "data", "corpus"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def collect_targets(records: list[dict[str, Any]]) -> list[ImageTarget]:
    """Uma imagem representativa por item (primeiro campo de imagem preenchido)."""
    targets: list[ImageTarget] = []
    for index, item in enumerate(records):
        item_id = str(item.get("id") or item.get("item_id") or f"item-{index + 1}")
        title = str(item.get("title") or item.get("titulo") or item_id)
        for field in IMAGE_FIELDS:
            value = item.get(field)
            if isinstance(value, str) and HTTP_URL_RE.match(value.strip()):
                targets.append(ImageTarget(item_id, title, field, value.strip()))
                break
    return targets


def measure_one(target: ImageTarget, timeout: float, retries: int) -> Measurement:
    request = urllib.request.Request(
        target.url,
        method="GET",
        headers={
            "User-Agent": (
                "MnemosyneVivaPerfMeter/1.0 "
                "(https://github.com/anavvanzin/mnemosyne-viva)"
            ),
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        },
    )
    last_status = "erro"
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(2 * attempt, 5))
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                # Lê o corpo completo para medir o tempo real de carregamento.
                while response.read(65536):
                    pass
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                if response.status == 200:
                    return Measurement(
                        id=target.item_id, title=target.title, field=target.field,
                        url=target.url, accessible=True, response_ms=elapsed_ms,
                        status="200",
                    )
                last_status = str(response.status)
        except urllib.error.HTTPError as exc:
            last_status = str(exc.code)
        except Exception as exc:  # noqa: BLE001
            last_status = f"{type(exc).__name__}"
    return Measurement(
        id=target.item_id, title=target.title, field=target.field,
        url=target.url, accessible=False, response_ms=None, status=last_status,
    )


def measure_all(targets: list[ImageTarget], timeout: float, workers: int,
                retries: int) -> list[Measurement]:
    if not targets:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(measure_one, t, timeout, retries) for t in targets]
        return [f.result() for f in concurrent.futures.as_completed(futures)]


def build_run(measurements: list[Measurement], threshold_ms: float, top: int) -> dict[str, Any]:
    accessible = [m for m in measurements if m.accessible and m.response_ms is not None]
    times = [m.response_ms for m in accessible]
    average = round(sum(times) / len(times)) if times else 0
    slowest = sorted(accessible, key=lambda m: m.response_ms or 0, reverse=True)[:top]
    over = bool(times) and average > threshold_ms
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checked_count": len(measurements),
        "accessible_count": len(accessible),
        "average_response_ms": average,
        "threshold_ms": int(threshold_ms),
        "status": "alert" if over else "ok",
        "top_slowest": [
            {"id": m.id, "title": m.title, "url": m.url, "response_ms": m.response_ms,
             "field": m.field}
            for m in slowest
        ],
    }


def load_history(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("runs"), list):
                return data
        except json.JSONDecodeError:
            pass
    return {"schema": "mnemosyne-viva/performance-history@1", "runs": []}


def write_history(path: Path, history: dict[str, Any], run: dict[str, Any]) -> None:
    history.setdefault("schema", "mnemosyne-viva/performance-history@1")
    history.setdefault("runs", [])
    history["runs"].append(run)
    history["last_run"] = run["timestamp"]
    history["last_average_response_ms"] = run["average_response_ms"]
    history["last_status"] = run["status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(report_path: Path, run: dict[str, Any], json_path: Path) -> None:
    over = run["status"] == "alert"
    lines = [
        "# Relatório de performance do acervo",
        "",
        f"Gerado em: {run['timestamp']}",
        f"Arquivo medido: `{json_path}`",
        "",
        "## Resumo",
        "",
        f"- Imagens verificadas: {run['checked_count']}",
        f"- Imagens acessíveis: {run['accessible_count']}",
        f"- Tempo médio de resposta: **{run['average_response_ms']} ms**",
        f"- Limite configurado: {run['threshold_ms']} ms",
        f"- Status: {'ACIMA DO LIMITE' if over else 'dentro do limite'}",
        "",
    ]
    if run["top_slowest"]:
        lines.extend([
            f"## {len(run['top_slowest'])} itens mais lentos",
            "",
            "| Item | Tempo (ms) | Campo | URL |",
            "|---|---:|---|---|",
        ])
        for entry in run["top_slowest"]:
            safe_title = str(entry["title"]).replace("|", "\\|")
            lines.append(
                f"| `{entry['id']}` {safe_title} | {entry['response_ms']} | "
                f"`{entry['field']}` | {entry['url']} |"
            )
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    json_path = Path(args.json)
    history_path = Path(args.history)
    report_path = Path(args.report)

    records = load_records(json_path)
    targets = collect_targets(records)
    if args.limit and args.limit > 0:
        targets = targets[: args.limit]

    measurements = measure_all(targets, args.timeout, args.workers, args.retries)
    run = build_run(measurements, args.threshold_ms, args.top)

    history = load_history(history_path)
    write_history(history_path, history, run)
    write_report(report_path, run, json_path)

    over = run["status"] == "alert"
    write_outputs(
        average_response_ms=run["average_response_ms"],
        threshold_ms=run["threshold_ms"],
        accessible_count=run["accessible_count"],
        checked_count=run["checked_count"],
        status=run["status"],
        over_threshold="true" if over else "false",
    )
    print(
        f"Imagens: {run['checked_count']} (acessíveis: {run['accessible_count']}). "
        f"Média: {run['average_response_ms']} ms. Limite: {run['threshold_ms']} ms. "
        f"Status: {run['status']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
