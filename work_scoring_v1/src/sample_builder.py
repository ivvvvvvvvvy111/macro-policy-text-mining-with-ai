from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set


SOURCE_DB_MAP = {
    "wallstreetcn": "wallstreetcn.sqlite3",
    "cls": "cls.sqlite3",
    "official_gov": "official.sqlite3",
    "official": "official.sqlite3",
    "sina_finance": "sina_finance.sqlite3",
}


@dataclass
class CandidateRow:
    event_id: str
    source: str
    published_at: str
    title: str
    url: str
    rule_score: int
    content_status: str
    is_best_content: bool


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def iter_candidates(path: Path) -> Iterator[CandidateRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                score = int(float(row.get("rule_score") or 0))
            except ValueError:
                score = 0
            yield CandidateRow(
                event_id=str(row.get("event_id") or "").strip(),
                source=str(row.get("source") or "").strip(),
                published_at=str(row.get("published_at") or "").strip(),
                title=str(row.get("title") or "").strip(),
                url=str(row.get("url") or "").strip(),
                rule_score=score,
                content_status=str(row.get("content_status") or "").strip(),
                is_best_content=_truthy(str(row.get("is_best_content") or "")),
            )


def _load_url_content_map(state_dir: Path, source: str, urls: Set[str]) -> Dict[str, str]:
    name = SOURCE_DB_MAP.get(source)
    if not name or not urls:
        return {}
    path = state_dir / name
    if not path.exists():
        return {}
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=120)
    out: Dict[str, str] = {}
    try:
        url_list = list(urls)
        chunk = 400
        for i in range(0, len(url_list), chunk):
            part = url_list[i : i + chunk]
            placeholders = ",".join("?" for _ in part)
            sql = (
                f"SELECT url, content FROM records WHERE url IN ({placeholders}) "
                "AND content IS NOT NULL AND length(content) > 0"
            )
            for url, content in con.execute(sql, part):
                if url and content:
                    out[str(url)] = str(content).strip()
    finally:
        con.close()
    return out


def build_sample(
    *,
    candidates_csv: Path,
    state_dir: Path,
    output_csv: Path,
    manifest_path: Path,
    target_n: int = 5000,
) -> Dict[str, Any]:
    filtered = [
        row
        for row in iter_candidates(candidates_csv)
        if row.is_best_content and row.content_status == "full" and row.url
    ]
    filtered.sort(key=lambda r: (-r.rule_score, r.published_at, r.url))

    # Prefetch a surplus pool so we can skip missing content.
    pool = filtered[: max(target_n * 3, target_n + 2000)]
    by_source: Dict[str, Set[str]] = defaultdict(set)
    for row in pool:
        by_source[row.source].add(row.url)

    content_by_url: Dict[str, str] = {}
    for source, urls in by_source.items():
        content_by_url.update(_load_url_content_map(state_dir, source, urls))

    selected: List[Dict[str, str]] = []
    skipped_no_content = 0
    seen_urls: Set[str] = set()

    for row in filtered:
        if len(selected) >= target_n:
            break
        if row.url in seen_urls:
            continue
        content = content_by_url.get(row.url)
        if not content:
            # lazy single-source refill if outside initial pool
            if row.url not in content_by_url:
                extra = _load_url_content_map(state_dir, row.source, {row.url})
                content_by_url.update(extra)
                content = content_by_url.get(row.url)
        if not content:
            skipped_no_content += 1
            continue
        seen_urls.add(row.url)
        news_id = "N{0:05d}".format(len(selected) + 1)
        selected.append(
            {
                "news_id": news_id,
                "event_id": row.event_id,
                "title": row.title,
                "date": (row.published_at or "")[:10],
                "source": row.source,
                "url": row.url,
                "content": content,
                "rule_score": str(row.rule_score),
                "content_status": row.content_status,
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "news_id",
                "event_id",
                "title",
                "date",
                "source",
                "url",
                "content",
                "rule_score",
                "content_status",
            ],
        )
        writer.writeheader()
        writer.writerows(selected)

    source_counts: Dict[str, int] = defaultdict(int)
    for item in selected:
        source_counts[item["source"]] += 1

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rule": "is_best_content=True AND content_status=full ORDER BY rule_score DESC, then fill content from sqlite",
        "target_n": target_n,
        "selected_n": len(selected),
        "candidate_pool_after_filter": len(filtered),
        "skipped_no_content": skipped_no_content,
        "source_counts": dict(source_counts),
        "candidates_csv": str(candidates_csv),
        "state_dir": str(state_dir),
        "output_csv": str(output_csv),
        "min_rule_score": int(selected[-1]["rule_score"]) if selected else None,
        "max_rule_score": int(selected[0]["rule_score"]) if selected else None,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
