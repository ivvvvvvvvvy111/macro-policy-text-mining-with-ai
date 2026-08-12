from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work_scoring_v1" / "output"
DATA = ROOT / "work_scoring_v1" / "data"


def jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def csv_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def main() -> None:
    summary_path = OUT / "run_summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    print("政策新闻信息提取项目状态")
    print(f"- 输入新闻: {csv_count(DATA / 'sample_5000.csv'):,}")
    print(f"- 拆分输出新闻: {jsonl_count(OUT / 'measures.jsonl'):,}")
    print(f"- 措施路由: {jsonl_count(OUT / 'routing_results.jsonl'):,}")
    print(f"- 评分关系: {csv_count(OUT / 'scores_relations.csv'):,}")
    print(f"- 错误日志行: {jsonl_count(OUT / 'errors.jsonl'):,}")
    print(f"- 最近运行状态: {summary.get('status', '未知')}")


if __name__ == "__main__":
    main()
