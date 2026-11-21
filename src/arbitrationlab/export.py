"""Exportacao das revisoes humanas para JSONL compativel com os datasets golden.

As revisoes sao gravadas com `source: human_review` e so incluem campos confirmados ou
corrigidos (os `unreadable` nao sao etiquetas). O resultado NAO entra automaticamente no
dataset: e preciso uma revisao do dataset antes de o usar como golden.

Uso: python -m arbitrationlab.export --database-url sqlite:///./data/arbitrationlab.db --out x.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from arbitrationlab.config import Settings
from arbitrationlab.store.repository import ArbitrationStore, human_reviews

SOURCE = "human_review"
LABEL_ACTIONS = frozenset({"confirm", "correct"})


def export_reviews_jsonl(store: ArbitrationStore) -> str:
    lines: list[str] = []
    for review in human_reviews(store):
        if review["action"] not in LABEL_ACTIONS:
            continue
        record = {
            "id": f"{review['arbitration_id']}:{review['field']}",
            "source": SOURCE,
            "difficulty": "human_review",
            "text": review["text"],
            "gold": {review["field"]: review["new_value"]},
            "reviewed_by": review["actor"],
            "reviewed_at": review["created_at"],
        }
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return "".join(line + "\n" for line in lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta revisoes humanas para JSONL.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings.from_env()
    url = args.database_url or settings.database_url
    text = export_reviews_jsonl(ArbitrationStore(url))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{text.count(chr(10))} revisoes exportadas para {args.out}")


if __name__ == "__main__":
    main()
