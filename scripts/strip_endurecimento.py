"""Migração única: remove o escore composto aposentado dos dados do acervo.

O índice de endurecimento foi aposentado da metodologia ICONOCRACIA (a codificação
vigente é o inventário verbal de atributos — indícios lidos caso a caso, nunca
somados). Este script limpa os artefatos numéricos dos dois JSONs públicos:

1. ``iconographic_metadata.endurecimento_score`` (335 itens);
2. ``endurecimento_score`` e ``indicadores`` de nível superior (enriched);
3. o parêntese mecânico ``(endurecimento N.N)`` embutido em
   ``panofsky.interpretation[].claim_text``.

O que NÃO é tocado: as ocorrências da palavra "endurecimento" como conceito na
prosa interpretativa (ex.: "Justiça antes do endurecimento alegórico"). Essas são
editoriais — rever caso a caso, não por script.

Uso:
    python scripts/strip_endurecimento.py
    git add site/data && git commit -m "data: strip retired endurecimento score"
"""
import json
import re
from pathlib import Path

DATA = [
    Path("site/data/corpus-data-enriched.json"),
    Path("site/data/acervo.json"),
]
PAREN_SCORE = re.compile(r"\s*\(endurecimento\s+\d+(?:\.\d+)?\)")


def strip(path: Path) -> None:
    items = json.loads(path.read_text(encoding="utf-8"))
    removed = 0
    for item in items:
        meta = item.get("iconographic_metadata")
        if isinstance(meta, dict) and "endurecimento_score" in meta:
            del meta["endurecimento_score"]
            removed += 1
        for key in ("endurecimento_score", "indicadores"):
            if key in item:
                del item[key]
                removed += 1
        panofsky = (meta or {}).get("panofsky") or {}
        for interp in panofsky.get("interpretation") or []:
            text = interp.get("claim_text", "")
            text, n = PAREN_SCORE.subn("", text)
            if n:
                interp["claim_text"] = text
                removed += n
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path}: {removed} artefatos de escore removidos")


if __name__ == "__main__":
    for p in DATA:
        strip(p)
