from __future__ import annotations

import csv
from pathlib import Path

from src.sample_builder import CandidateRow, _truthy


def test_truthy() -> None:
    assert _truthy("True")
    assert _truthy("true")
    assert not _truthy("False")


def test_candidate_sort_key_logic() -> None:
    rows = [
        CandidateRow("1", "a", "2024-01-01", "t1", "u1", 5, "full", True),
        CandidateRow("2", "a", "2024-01-02", "t2", "u2", 9, "full", True),
        CandidateRow("3", "a", "2024-01-03", "t3", "u3", 9, "full", True),
    ]
    rows.sort(key=lambda r: (-r.rule_score, r.published_at, r.url))
    assert [r.event_id for r in rows] == ["2", "3", "1"]


def test_sw_catalog_readable() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "sw2021_l2_industries.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 100
