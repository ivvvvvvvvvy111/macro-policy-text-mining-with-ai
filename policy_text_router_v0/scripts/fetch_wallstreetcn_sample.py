from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

API_URL = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&client=pc&limit={limit}"


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="获取华尔街见闻公开 7x24 快讯样例")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("data/news_sample.csv"))
    args = parser.parse_args()

    request = urllib.request.Request(
        API_URL.format(limit=max(args.count + 10, 60)),
        headers={"User-Agent": "Mozilla/5.0 policy-text-router research prototype"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    items = payload["data"]["items"]
    rows = []
    for item in items:
        content = clean(item.get("content_text") or item.get("content") or "")
        if not content:
            continue
        title = clean(item.get("title") or "") or content[:70]
        dt = datetime.fromtimestamp(item["display_time"], ZoneInfo("Asia/Shanghai"))
        rows.append(
            {
                "news_id": str(item["id"]),
                "title": title,
                "date": dt.isoformat(timespec="seconds"),
                "source": "华尔街见闻-7x24快讯",
                "url": item.get("uri", ""),
                "content": content,
            }
        )
        if len(rows) == args.count:
            break
    if len(rows) < args.count:
        raise RuntimeError(f"仅获取到 {len(rows)} 条有效新闻，少于要求的 {args.count} 条。")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"已写入 {len(rows)} 条新闻：{args.output}")


if __name__ == "__main__":
    main()

