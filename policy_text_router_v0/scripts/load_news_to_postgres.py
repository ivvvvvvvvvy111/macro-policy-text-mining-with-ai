from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.postgres_store import PostgresNewsStore  # noqa: E402


def read_jsonl(paths: list[Path]):
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="将历史新闻JSONL写入PostgreSQL")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("请在 .env 中配置 DATABASE_URL。")
    with psycopg.connect(database_url) as connection:
        store = PostgresNewsStore(connection)
        industries = store.load_industry_catalog(ROOT / "data" / "sw2021_l2_industries.csv")
        counts = store.upsert_news(read_jsonl(args.paths))
    print(json.dumps({"industries": industries, **counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
