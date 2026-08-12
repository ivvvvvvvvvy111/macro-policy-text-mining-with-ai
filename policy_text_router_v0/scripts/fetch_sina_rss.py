from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.sina import SINA_RSS_FEEDS, fetch_feed, parse_rss  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="获取新浪财经官方RSS当前新闻")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "realtime" / "sina_finance_rss.jsonl",
    )
    args = parser.parse_args()
    unique: dict[str, dict] = {}
    feed_counts: dict[str, int] = {}
    for feed_key, url in SINA_RSS_FEEDS.items():
        records = parse_rss(fetch_feed(url), feed_key=feed_key)
        feed_counts[feed_key] = len(records)
        for record in records:
            unique[record["source_news_id"]] = record
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in unique.values():
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {"feeds": feed_counts, "unique_records": len(unique), "output": str(args.output)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
