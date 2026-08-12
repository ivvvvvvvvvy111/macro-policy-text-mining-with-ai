from __future__ import annotations

from datetime import date, timedelta

from src.aggregate import (
    decay_signal,
    dispersion,
    half_life_days,
    build_style_panels,
    RelationEvent,
)


def test_half_life_mapping() -> None:
    assert half_life_days("immediate") == 5
    assert half_life_days("short") == 20
    assert half_life_days("medium") == 60
    assert half_life_days("long") == 120
    assert half_life_days("unknown") == 20
    assert half_life_days("") == 20


def test_decay_at_half_life() -> None:
    assert abs(decay_signal(1.0, 20, 20) - 0.5) < 1e-12
    assert abs(decay_signal(-2.0, 0, 20) + 2.0) < 1e-12


def test_dispersion() -> None:
    # pos=3, neg=-1 => net=2; |3|+|-1|-|2|=2
    assert abs(dispersion(3.0, -1.0) - 2.0) < 1e-12


def test_style_axes_not_mixed() -> None:
    events = [
        RelationEvent(
            track="style",
            t0=date(2024, 1, 1),
            score=1.0,
            half_life=5,
            channel="listing_financing",
            industry_l2_code="",
            industry_l2_name="",
            industry_l1_name="",
            style_axis="size",
            news_id="N1",
            horizon="immediate",
        ),
        RelationEvent(
            track="style",
            t0=date(2024, 1, 1),
            score=-1.0,
            half_life=5,
            channel="corporate_governance",
            industry_l2_code="",
            industry_l2_name="",
            industry_l1_name="",
            style_axis="quality",
            news_id="N2",
            horizon="immediate",
        ),
    ]
    rows, _, _ = build_style_panels(events)
    by_axis = {(r["date"], r["style_axis"]): r for r in rows if r["date"] == "2024-01-01"}
    assert by_axis[("2024-01-01", "size")]["net"] > 0
    assert by_axis[("2024-01-01", "quality")]["net"] < 0
    # no combined total axis
    assert all(r["style_axis"] in {"size", "quality"} for r in rows)


def test_positive_negative_split_same_day() -> None:
    events = [
        RelationEvent(
            track="style",
            t0=date(2024, 2, 1),
            score=0.8,
            half_life=20,
            channel="other",
            industry_l2_code="",
            industry_l2_name="",
            industry_l1_name="",
            style_axis="dividend",
            news_id="A",
            horizon="short",
        ),
        RelationEvent(
            track="style",
            t0=date(2024, 2, 1),
            score=-0.3,
            half_life=20,
            channel="other",
            industry_l2_code="",
            industry_l2_name="",
            industry_l1_name="",
            style_axis="dividend",
            news_id="B",
            horizon="short",
        ),
    ]
    rows, _, _ = build_style_panels(events)
    row = next(r for r in rows if r["date"] == "2024-02-01" and r["style_axis"] == "dividend")
    assert row["positive"] > 0
    assert row["negative"] < 0
    assert abs(row["net"] - (row["positive"] + row["negative"])) < 1e-12
