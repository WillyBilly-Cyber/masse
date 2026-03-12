"""update_ledger.py

Append a single run's summary to results.tsv (untracked).

Usage:
  python update_ledger.py runs/<run_id> --description "baseline"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HEADER = [
    "run_id",
    "score",
    "accuracy",
    "runtime_s",
    "stability",
    "status",
    "description",
]


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--ledger", type=Path, default=Path(__file__).resolve().parent / "results.tsv")
    ap.add_argument("--description", type=str, default="")
    ap.add_argument("--status", type=str, default="")
    args = ap.parse_args()

    run_id = args.run_dir.name
    score_path = args.run_dir / "score.json"
    if not score_path.exists():
        raise SystemExit(f"Missing score.json, run score_bench.py first: {score_path}")

    score_obj = _load_json(score_path)
    sub = score_obj.get("submetrics", {})

    row = {
        "run_id": run_id,
        "score": score_obj.get("score"),
        "accuracy": sub.get("accuracy"),
        "runtime_s": sub.get("runtime_s"),
        "stability": sub.get("stability"),
        "status": args.status or score_obj.get("status"),
        "description": args.description,
    }

    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    is_new = not args.ledger.exists()
    with args.ledger.open("a", encoding="utf-8") as f:
        if is_new:
            f.write("\t".join(HEADER) + "\n")
        f.write("\t".join("" if row[h] is None else str(row[h]) for h in HEADER) + "\n")

    print(str(args.ledger))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
