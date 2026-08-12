from __future__ import annotations

import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .wallstreetcn import clean_html, normalized_hash

SINA_RSS_FEEDS = {
    "finance_hot": "https://rss.sina.com.cn/roll/finance/hot_roll.xml",
    "stock_hot": "https://rss.sina.com.cn/roll/stock/hot_roll.xml",
}


def parse_rss(xml_bytes: bytes, *, feed_key: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    records: list[dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        title = clean_html(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        description = clean_html(item.findtext("description") or "")
        guid = (item.findtext("guid") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        try:
            published = parsedate_to_datetime(pub_date)
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            published = datetime.now(timezone.utc)
        source_news_id = guid or link or hashlib.sha256(
            f"{title}|{pub_date}".encode("utf-8")
        ).hexdigest()
        records.append(
            {
                "source": "sina_finance",
                "source_type": "article",
                "source_news_id": source_news_id,
                "title": title,
                "content": description,
                "summary": description,
                "url": link,
                "published_at": published.isoformat(),
                "is_paid": False,
                "content_hash": normalized_hash(title, description),
                "raw_payload": {"feed_key": feed_key, "pub_date": pub_date, "guid": guid},
            }
        )
    return records


def fetch_feed(url: str, *, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 policy-text-router internal-research"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()

