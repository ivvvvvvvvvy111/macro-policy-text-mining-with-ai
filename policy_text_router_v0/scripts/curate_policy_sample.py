from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import Settings  # noqa: E402
from src.io_utils import append_jsonl, read_news, write_json  # noqa: E402
from src.llm_client import StructuredLLM  # noqa: E402
from src.measure_extract import MeasureExtractor  # noqa: E402


def read_full_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def quality_score(row: dict[str, str], extraction: object) -> float:
    content = row["content"]
    measures = extraction.measures
    evidence_hits = sum(1 for m in measures if m.evidence and m.evidence in content)
    score = float(row.get("selection_score", 0))
    score += 3 if 80 <= len(content) <= 1000 else 0
    score += min(evidence_hits, 3) * 2
    score += 2 if 1 <= len(measures) <= 3 else 0
    score -= max(0, len(measures) - 4) * 2
    return score


def too_similar(title: str, selected: list[dict[str, str]]) -> bool:
    return any(SequenceMatcher(None, title, row["title"]).ratio() >= 0.78 for row in selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="用measure提取结果从候选池中挑选50条典型政策新闻")
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "policy_candidates.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "news_sample.csv")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "work" / "curation")
    args = parser.parse_args()

    rows = read_full_csv(args.input)
    news_rows = read_news(args.input)
    by_id = {row["news_id"]: row for row in rows}
    args.work_dir.mkdir(parents=True, exist_ok=True)
    measures_path = args.work_dir / "candidate_measures.jsonl"
    errors_path = args.work_dir / "errors.jsonl"
    measures_path.unlink(missing_ok=True); errors_path.unlink(missing_ok=True)

    llm = StructuredLLM(Settings.from_env())
    extractor = MeasureExtractor(llm, ROOT / "prompts" / "measure_prompt.txt")
    accepted: list[dict] = []

    def one(news: dict[str, str]):
        return news, extractor.extract(news)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(one, news): news for news in news_rows}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            news = futures[future]
            try:
                news, extraction = future.result()
                full = by_id[news["news_id"]]
                record = {"news": full, "result": extraction.model_dump()}
                append_jsonl(measures_path, record)
                if extraction.is_policy_news and extraction.measures:
                    accepted.append({
                        "row": full,
                        "extraction": extraction,
                        "quality_score": quality_score(full, extraction),
                    })
            except Exception as exc:
                append_jsonl(errors_path, {"news_id": news["news_id"], "error": repr(exc)})
            if i % 20 == 0 or i == len(futures):
                print(f"curation progress {i}/{len(futures)} accepted={len(accepted)}", flush=True)

    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in accepted:
        buckets[item["row"].get("candidate_theme", "综合政策")].append(item)
    for values in buckets.values():
        values.sort(key=lambda x: (x["quality_score"], x["row"]["date"]), reverse=True)

    selected: list[dict[str, str]] = []
    audit: list[dict[str, str | float | int]] = []
    theme_order = sorted(buckets, key=lambda name: len(buckets[name]))
    while len(selected) < args.count and any(buckets.values()):
        made_progress = False
        for name in theme_order:
            while buckets[name]:
                item = buckets[name].pop(0)
                row = item["row"]
                if too_similar(row["title"], selected):
                    continue
                out = {key: row[key] for key in ("news_id", "title", "date", "source", "url", "content")}
                out["candidate_theme"] = name
                out["selection_score"] = row.get("selection_score", "")
                out["curation_quality_score"] = str(round(item["quality_score"], 2))
                selected.append(out)
                audit.append({
                    "news_id": row["news_id"], "theme": name,
                    "quality_score": round(item["quality_score"], 2),
                    "measure_count": len(item["extraction"].measures),
                    "evidence_exact_hits": sum(m.evidence in row["content"] for m in item["extraction"].measures),
                })
                made_progress = True
                break
            if len(selected) >= args.count:
                break
        if not made_progress:
            break
    if len(selected) < args.count:
        raise RuntimeError(f"去重后只有 {len(selected)} 条有效政策新闻，少于要求的 {args.count} 条")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=selected[0].keys())
        writer.writeheader(); writer.writerows(selected)
    with (args.work_dir / "selection_audit.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit[0].keys()))
        writer.writeheader(); writer.writerows(audit)
    write_json(args.work_dir / "summary.json", {
        "candidate_count": len(rows), "valid_policy_count": len(accepted), "selected_count": len(selected),
        "theme_counts": {name: sum(row["candidate_theme"] == name for row in selected) for name in theme_order},
        "errors": len(errors_path.read_text(encoding="utf-8").splitlines()) if errors_path.exists() else 0,
        "llm": llm.stats(),
    })
    print(json.dumps({"selected": len(selected), "output": str(args.output), "llm": llm.stats()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
