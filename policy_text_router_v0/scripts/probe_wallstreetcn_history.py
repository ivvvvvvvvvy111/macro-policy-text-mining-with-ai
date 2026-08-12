from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion.wallstreetcn import (  # noqa: E402
    WallstreetCNClient,
    normalize_article,
    normalize_live,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def median_length(rows: list[dict]) -> int:
    return int(statistics.median([len(row["content"]) for row in rows])) if rows else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="回拉华尔街见闻快讯与长文并统计数量比")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=1000)
    parser.add_argument("--article-detail-limit", type=int, default=5000)
    parser.add_argument("--pause", type=float, default=0.15)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "history_probe" / "wallstreetcn",
    )
    args = parser.parse_args()

    now = datetime.now(SHANGHAI)
    since = now - timedelta(days=args.days)
    since_timestamp = int(since.timestamp())
    client = WallstreetCNClient()

    flashes = [
        normalize_live(item)
        for item in client.iter_lives(
            since_timestamp=since_timestamp,
            max_pages=args.max_pages,
            pause=args.pause,
        )
    ]

    article_list = list(
        client.iter_articles(
            since_timestamp=since_timestamp,
            max_pages=args.max_pages,
            pause=args.pause,
        )
    )
    articles: list[dict] = []
    detail_errors: list[dict] = []
    for index, item in enumerate(article_list):
        detail = None
        if index < args.article_detail_limit:
            try:
                detail = client.article_detail(str(item["id"]))
            except Exception as exc:
                detail_errors.append({"article_id": str(item.get("id")), "error": repr(exc)})
            time.sleep(args.pause)
        articles.append(normalize_article(item, detail))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "flashes.jsonl", flashes)
    write_jsonl(args.output_dir / "articles.jsonl", articles)
    write_jsonl(args.output_dir / "article_detail_errors.jsonl", detail_errors)

    daily_flash = Counter(row["published_at"][:10] for row in flashes)
    daily_article = Counter(row["published_at"][:10] for row in articles)
    summary = {
        "window": {"days": args.days, "since": since.isoformat(), "until": now.isoformat()},
        "counts": {
            "flash": len(flashes),
            "article": len(articles),
            "all": len(flashes) + len(articles),
            "article_to_flash_ratio": round(len(articles) / len(flashes), 4) if flashes else None,
            "article_detail_errors": len(detail_errors),
            "paid_articles": sum(row["is_paid"] for row in articles),
        },
        "content_length": {
            "flash_median": median_length(flashes),
            "article_median": median_length(articles),
            "articles_over_500_chars": sum(len(row["content"]) >= 500 for row in articles),
        },
        "daily": {
            date: {"flash": daily_flash[date], "article": daily_article[date]}
            for date in sorted(set(daily_flash) | set(daily_article))
        },
        "outputs": {
            "flashes": str(args.output_dir / "flashes.jsonl"),
            "articles": str(args.output_dir / "articles.jsonl"),
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
