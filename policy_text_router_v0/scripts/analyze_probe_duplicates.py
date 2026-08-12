from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dedup import cluster_near_duplicates  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="分析探测数据中的完全重复和近重复")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--max-hours", type=int, default=48)
    parser.add_argument("--max-hamming", type=int, default=8)
    args = parser.parse_args()

    records = read_jsonl(args.input_dir / "flashes.jsonl") + read_jsonl(
        args.input_dir / "articles.jsonl"
    )
    exact = Counter(record["content_hash"] for record in records)
    exact_duplicate_records = sum(count - 1 for count in exact.values() if count > 1)
    clusters, matches = cluster_near_duplicates(
        records, max_hours=args.max_hours, max_hamming=args.max_hamming
    )
    cluster_rows = []
    for cluster_no, indices in enumerate(clusters, start=1):
        for index in indices:
            record = records[index]
            cluster_rows.append(
                {
                    "cluster_id": cluster_no,
                    "source_type": record["source_type"],
                    "source_news_id": record["source_news_id"],
                    "published_at": record["published_at"],
                    "title": record["title"],
                    "url": record["url"],
                }
            )
    output = args.input_dir / "near_duplicate_clusters.jsonl"
    with output.open("w", encoding="utf-8") as handle:
        for row in cluster_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "records": len(records),
        "exact_duplicate_records": exact_duplicate_records,
        "near_duplicate_clusters": len(clusters),
        "records_in_near_duplicate_clusters": sum(len(cluster) for cluster in clusters),
        "candidate_matches": len(matches),
        "method": "48小时窗口 + 中文字符二元组SimHash；用于候选召回，不能替代语义事件判定",
        "output": str(output),
    }
    (args.input_dir / "dedup_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
