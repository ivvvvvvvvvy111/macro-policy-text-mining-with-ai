from __future__ import annotations

import unittest
from pathlib import Path

from src.dedup import hamming_distance, simhash64
from src.industry_catalog import SWIndustryCatalog
from src.ingestion.wallstreetcn import clean_html, normalize_live
from src.ingestion.sina import parse_rss

ROOT = Path(__file__).resolve().parents[1]


class CoreV2Tests(unittest.TestCase):
    def test_industry_catalog_loads_and_is_unique(self) -> None:
        catalog = SWIndustryCatalog(ROOT / "data" / "sw2021_l2_industries.csv")
        self.assertGreaterEqual(len(catalog.entries), 120)
        self.assertEqual(len(catalog.entries), len(catalog.by_code))

    def test_html_cleaning(self) -> None:
        self.assertEqual(clean_html("<p>政策&nbsp;出台</p>"), "政策 出台")

    def test_live_normalization_has_stable_hash(self) -> None:
        item = {
            "id": 1,
            "title": "测试政策",
            "content_text": "降低交易费用。",
            "display_time": 1700000000,
            "uri": "https://example.com/1",
        }
        left = normalize_live(item)
        right = normalize_live(item)
        self.assertEqual(left["content_hash"], right["content_hash"])

    def test_simhash_identical_text(self) -> None:
        value = simhash64("深化资本市场投融资综合改革")
        self.assertEqual(hamming_distance(value, value), 0)

    def test_sina_rss_parser(self) -> None:
        xml = b"""<?xml version='1.0' encoding='utf-8'?>
        <rss><channel><item><title>Policy News</title>
        <link>https://finance.sina.com.cn/test</link>
        <description>Policy Content</description>
        <guid>test-1</guid><pubDate>Fri, 08 Aug 2026 01:00:00 GMT</pubDate>
        </item></channel></rss>"""
        rows = parse_rss(xml, feed_key="test")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_news_id"], "test-1")
        self.assertEqual(rows[0]["source"], "sina_finance")


if __name__ == "__main__":
    unittest.main()
