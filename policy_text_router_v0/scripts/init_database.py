from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("请在 .env 中配置 DATABASE_URL。")
    schema = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(schema)
    print("PostgreSQL schema 初始化完成。")


if __name__ == "__main__":
    main()

