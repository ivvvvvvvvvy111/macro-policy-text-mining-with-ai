#!/usr/bin/env python3
"""Show concise progress for the calendar-article production run."""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work_scoring_v1/output/calendar_articles_20240801_20260131"
TOTAL = 4892


def lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> int:
    measures_file = OUTPUT / "measures.jsonl"
    completed = lines(measures_file)
    failures = lines(OUTPUT / "errors.jsonl")
    policy_news = nonpolicy_news = measures = 0
    if measures_file.exists():
        with measures_file.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                result = json.loads(line)["result"]
                measures += len(result.get("measures", []))
                if result.get("is_policy_news"):
                    policy_news += 1
                else:
                    nonpolicy_news += 1
    # In sandboxed desktop sessions process inspection may be unavailable, so
    # use the append-only result file as a heartbeat. Complex articles can take
    # several minutes before the next commit.
    age_seconds = time.time() - measures_file.stat().st_mtime if measures_file.exists() else None
    running = age_seconds is not None and age_seconds < 15 * 60
    percent = completed / TOTAL * 100 if TOTAL else 0
    print(f"运行状态：{'最近仍在写入' if running else '超过15分钟未见新结果，请检查后台任务'}")
    print(f"完成新闻：{completed:,} / {TOTAL:,}（{percent:.1f}%）")
    print(f"失败日志：{failures:,}（失败新闻会在后续重试）")
    print(f"政策新闻：{policy_news:,}；非政策新闻：{nonpolicy_news:,}")
    print(f"最小措施：{measures:,}")
    print(f"路由记录：{lines(OUTPUT / 'routing_results.jsonl'):,}")
    print(f"评分关系：{lines(OUTPUT / 'scores_relations.jsonl'):,}")
    print(f"行业/全A/风格评分：{lines(OUTPUT / 'scores_industry.jsonl'):,} / "
          f"{lines(OUTPUT / 'scores_all_a.jsonl'):,} / {lines(OUTPUT / 'scores_style.jsonl'):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
