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
    rows = [row for row in rows if (row.get("content") or "").strip()]
    return rows[:limit] if limit is not None else rows


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_done_ids(path: Path, key: str = "news_id") -> set[str]:
    done: set[str] = set()
    for row in read_jsonl(path):
        if key == "news_id":
            news = row.get("news") or {}
            value = news.get("news_id") or row.get("news_id")
        else:
            value = row.get(key)
        if value:
            done.add(str(value))
    return done


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, records: Iterable[dict[str, Any]]) -> None:
    rows = list(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
