#!/usr/bin/env python3
"""Compatibilidade para o gerador editorial canônico.

O site não mantém uma segunda cópia editável do corpus. Este comando delega a
``corpus_sync.py`` e exige o corpus do SHA declarado em ``publication.json``.
"""
from __future__ import annotations

import argparse
import pathlib

from corpus_sync import (
    DEFAULT_LEGACY,
    DEFAULT_OUT,
    DEFAULT_PUBLICATION,
    DEFAULT_SCHEMA,
    generate,
    load_corpus,
    load_json,
    validate_records,
    write_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=pathlib.Path)
    parser.add_argument("--publication", type=pathlib.Path, default=DEFAULT_PUBLICATION)
    parser.add_argument("--legacy", type=pathlib.Path, default=DEFAULT_LEGACY)
    parser.add_argument("--schema", type=pathlib.Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--include-review", action="store_true")
    args = parser.parse_args()
    publication = load_json(args.publication)
    records = load_corpus(args.corpus, publication)
    legacy = load_json(args.legacy)
    validate_records(records, args.schema)
    items, stats, constellations = generate(
        records, publication, legacy, include_review=args.include_review,
    )
    write_outputs(args.out, items, stats, constellations)
    print(f"Sincronizados {len(items)} itens e {len(constellations)} constelações.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
