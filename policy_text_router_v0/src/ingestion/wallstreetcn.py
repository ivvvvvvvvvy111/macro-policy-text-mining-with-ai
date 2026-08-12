from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

API_ROOT = "https://api-one.wallstcn.com/apiv1/content"
SHANGHAI = ZoneInfo("Asia/Shanghai")


def clean_html(value: str) -> str:
    value = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", value or "", flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalized_hash(title: str, content: str) -> str:
    normalized = re.sub(r"[\W_]+", "", (title + "\n" + content).lower(), flags=re.UNICODE)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class WallstreetCNClient:
    def __init__(self, *, timeout: float = 40.0, retries: int = 3) -> None:
        self.timeout = timeout
        self.retries = retries
        self.headers = {
            "User-Agent": "Mozilla/5.0 policy-text-router internal-research",
            "Accept": "application/json,text/plain,*/*",
        }

    def _get_json(self, url: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                request = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception as exc:  # 网络错误统一退避重试
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"请求失败: {url}") from last_error

    def iter_lives(
        self,
        *,
        since_timestamp: int,
        max_pages: int = 1000,
        page_size: int = 100,
        pause: float = 0.15,
    ) -> Iterator[dict[str, Any]]:
        cursor: str | None = None
        seen: set[str] = set()
        for _ in range(max_pages):
            query = {"channel": "global-channel", "client": "pc", "limit": page_size}
            if cursor:
                query["cursor"] = cursor
            payload = self._get_json(f"{API_ROOT}/lives?{urllib.parse.urlencode(query)}")
            data = payload.get("data", {})
            batch = data.get("items", []) or []
            page_times = [int(item.get("display_time") or 0) for item in batch]
            for item in batch:
                item_id = str(item.get("id") or "")
                display_time = int(item.get("display_time") or 0)
                if item_id and item_id not in seen and display_time >= since_timestamp:
                    seen.add(item_id)
                    yield item
            cursor = data.get("next_cursor")
            if not batch or not cursor or (page_times and max(page_times) < since_timestamp):
                break
            time.sleep(pause)

    def iter_articles(
        self,
        *,
        since_timestamp: int,
        max_pages: int = 1000,
        page_size: int = 20,
        pause: float = 0.15,
    ) -> Iterator[dict[str, Any]]:
        cursor: str | None = None
        seen: set[str] = set()
        for _ in range(max_pages):
            query = {"channel": "global", "accept": "article", "limit": page_size}
            if cursor:
                query["cursor"] = cursor
            payload = self._get_json(
                f"{API_ROOT}/information-flow?{urllib.parse.urlencode(query)}"
            )
            data = payload.get("data", {})
            batch = data.get("items", []) or []
            resources = [item.get("resource", item) for item in batch]
            page_times = [int(item.get("display_time") or 0) for item in resources]
            for item in resources:
                item_id = str(item.get("id") or "")
                display_time = int(item.get("display_time") or 0)
                if item_id and item_id not in seen and display_time >= since_timestamp:
                    seen.add(item_id)
                    yield item
            cursor = data.get("next_cursor")
            if not batch or not cursor or (page_times and max(page_times) < since_timestamp):
                break
            time.sleep(pause)

    def article_detail(self, article_id: str) -> dict[str, Any]:
        payload = self._get_json(f"{API_ROOT}/articles/{article_id}?extract=0")
        if payload.get("code") not in (0, 20000, None):
            raise RuntimeError(f"文章 {article_id} 返回错误: {payload.get('message')}")
        return payload.get("data", {})


def normalize_live(item: dict[str, Any]) -> dict[str, Any]:
    content = clean_html(item.get("content_text") or item.get("content") or "")
    title = clean_html(item.get("title") or "") or content[:70]
    timestamp = int(item.get("display_time") or 0)
    item_id = str(item.get("id") or "")
    return {
        "source": "wallstreetcn",
        "source_type": "flash",
        "source_news_id": item_id,
        "title": title,
        "content": content,
        "summary": "",
        "url": item.get("uri") or f"https://wallstreetcn.com/livenews/{item_id}",
        "published_at": datetime.fromtimestamp(timestamp, SHANGHAI).isoformat(),
        "is_paid": False,
        "content_hash": normalized_hash(title, content),
        "raw_payload": item,
    }


def normalize_article(list_item: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, Any]:
    record = detail or list_item
    title = clean_html(record.get("title") or list_item.get("title") or "")
    summary = clean_html(record.get("content_short") or list_item.get("content_short") or "")
    content = clean_html(record.get("content") or "") or summary
    timestamp = int(record.get("display_time") or list_item.get("display_time") or 0)
    item_id = str(record.get("id") or list_item.get("id") or "")
    is_paid = bool(
        record.get("is_need_pay")
        or record.get("is_priced")
        or list_item.get("is_priced")
        or list_item.get("is_paid")
    )
    return {
        "source": "wallstreetcn",
        "source_type": "article",
        "source_news_id": item_id,
        "title": title,
        "content": content,
        "summary": summary,
        "url": list_item.get("uri") or f"https://wallstreetcn.com/articles/{item_id}",
        "published_at": datetime.fromtimestamp(timestamp, SHANGHAI).isoformat(),
        "is_paid": is_paid,
        "content_hash": normalized_hash(title, content),
        "raw_payload": {"list": list_item, "detail": detail},
    }

