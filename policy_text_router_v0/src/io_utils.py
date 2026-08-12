from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


REQUIRED_NEWS_COLUMNS = {"news_id", "title", "date", "source", "url", "content"}


def read_news(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_NEWS_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"输入 CSV 缺少字段: {', '.join(sorted(missing))}")
        rows = [dict(row) for row in reader]
    rows = [row for row in rows if row.get("content", "").strip()]
    return rows[:limit] if limit is not None else rows


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, records: Iterable[dict[str, Any]]) -> None:
    rows = list(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

