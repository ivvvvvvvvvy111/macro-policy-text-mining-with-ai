#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import read_jsonl, write_json


def main() -> int:
    output = ROOT / "output"
    relations_csv = output / "scores_relations.csv"
    rows = []
    if relations_csv.exists() and relations_csv.stat().st_size > 0:
        with relations_csv.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

    measures = read_jsonl(output / "measures.jsonl")
    routes = read_jsonl(output / "routing_results.jsonl")
    errors = read_jsonl(output / "errors.jsonl")

    def _num(v):
        try:
            return float(v) if v not in (None, "", "None") else None
        except Exception:
            return None

    state_scores = [_num(r.get("state_score")) for r in rows if r.get("track") == "industry"]
    a_units = [_num(r.get("a_unit")) for r in rows if r.get("track") == "style"]
    report = {
        "measures_news": len(measures),
        "routing_rows": len(routes),
        "errors": len(errors),
        "relation_rows": len(rows),
        "track_counts": dict(Counter(r.get("track") for r in rows)),
        "channel_top": Counter(r.get("channel") for r in rows).most_common(15),
        "null_policy_delta": sum(1 for r in rows if not r.get("policy_delta")),
        "null_novelty": sum(1 for r in rows if not r.get("novelty")),
        "industry_state_score_non_null": sum(1 for x in state_scores if x is not None),
        "style_a_unit_non_null": sum(1 for x in a_units if x is not None),
        "sample_titles": sorted({r.get("title", "") for r in rows})[:10],
        "error_samples": [e.get("error", "")[:200] for e in errors[:10]],
    }
    out = output / "qa_summary.json"
    write_json(out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
