from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from psycopg import Connection
from psycopg.types.json import Jsonb


class PostgresNewsStore:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def load_industry_catalog(self, path: Path) -> int:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        with self.connection.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO sw_industries (
                        classification_version, industry_l2_code, industry_l2_name,
                        industry_l1_name, source
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (classification_version, industry_l2_code)
                    DO UPDATE SET
                        industry_l2_name = EXCLUDED.industry_l2_name,
                        industry_l1_name = EXCLUDED.industry_l1_name,
                        source = EXCLUDED.source,
                        active = true
                    """,
                    (
                        row["classification_version"],
                        row["industry_l2_code"],
                        row["industry_l2_name"],
                        row["industry_l1_name"],
                        row["source"],
                    ),
                )
        self.connection.commit()
        return len(rows)

    def upsert_news(self, records: Iterable[dict[str, Any]]) -> dict[str, int]:
        counts = {"inserted": 0, "updated": 0, "unchanged": 0}
        with self.connection.cursor() as cursor:
            for record in records:
                cursor.execute(
                    "SELECT source_id FROM sources WHERE source_key = %s",
                    (record["source"],),
                )
                source = cursor.fetchone()
                if source is None:
                    raise ValueError(f"未知新闻源: {record['source']}")
                source_id = source[0]
                cursor.execute(
                    """
                    SELECT news_id, content_hash, current_version
                    FROM news_items
                    WHERE source_id = %s AND source_news_id = %s
                    FOR UPDATE
                    """,
                    (source_id, record["source_news_id"]),
                )
                existing = cursor.fetchone()
                if existing is None:
                    cursor.execute(
                        """
                        INSERT INTO news_items (
                            source_id, source_news_id, source_type, title, content, summary,
                            url, published_at, is_paid, content_hash, raw_payload
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING news_id
                        """,
                        (
                            source_id, record["source_news_id"], record["source_type"],
                            record["title"], record["content"], record.get("summary", ""),
                            record["url"], record["published_at"], record.get("is_paid", False),
                            record["content_hash"], Jsonb(record.get("raw_payload", {})),
                        ),
                    )
                    news_id = cursor.fetchone()[0]
                    cursor.execute(
                        """
                        INSERT INTO news_versions (
                            news_id, version_no, title, content, summary, content_hash, raw_payload
                        ) VALUES (%s, 1, %s, %s, %s, %s, %s)
                        """,
                        (
                            news_id, record["title"], record["content"], record.get("summary", ""),
                            record["content_hash"], Jsonb(record.get("raw_payload", {})),
                        ),
                    )
                    counts["inserted"] += 1
                elif existing[1] != record["content_hash"]:
                    news_id, _, current_version = existing
                    new_version = current_version + 1
                    cursor.execute(
                        """
                        UPDATE news_items SET
                            title=%s, content=%s, summary=%s, url=%s, published_at=%s,
                            last_seen_at=now(), is_paid=%s, content_hash=%s,
                            current_version=%s, raw_payload=%s
                        WHERE news_id=%s
                        """,
                        (
                            record["title"], record["content"], record.get("summary", ""),
                            record["url"], record["published_at"], record.get("is_paid", False),
                            record["content_hash"], new_version,
                            Jsonb(record.get("raw_payload", {})), news_id,
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO news_versions (
                            news_id, version_no, title, content, summary, content_hash, raw_payload
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            news_id, new_version, record["title"], record["content"],
                            record.get("summary", ""), record["content_hash"],
                            Jsonb(record.get("raw_payload", {})),
                        ),
                    )
                    counts["updated"] += 1
                else:
                    cursor.execute(
                        "UPDATE news_items SET last_seen_at=now(), raw_payload=%s WHERE news_id=%s",
                        (Jsonb(record.get("raw_payload", {})), existing[0]),
                    )
                    counts["unchanged"] += 1
        self.connection.commit()
        return counts

