from __future__ import annotations

from src.formulas import all_a_state_score, industry_state_score, style_a_unit, style_surprise
from src.schemas import AllARelation, IndustryRelation, StyleRelation


def test_industry_state_score_basic() -> None:
    rel = IndustryRelation(
        relation_id="R001",
        industry_l2_code="801080",
        industry_l2_name="dummy",
        industry_l1_name="dummy",
        channel="demand",
        directness="direct",
        direction=2,
        intensity=4,
        coverage=4,
        certainty=4,
        persistence=4,
        onset_speed="short",
        confidence=0.9,
        evidence="e",
        rationale="r",
    )
    assert industry_state_score(rel) == 2.0


def test_industry_state_score_null_when_missing() -> None:
    rel = IndustryRelation(
        relation_id="R001",
        industry_l2_code="801080",
        industry_l2_name="dummy",
        industry_l1_name="dummy",
        channel="demand",
        directness="direct",
        direction=1,
        intensity=None,
        coverage=4,
        certainty=4,
        persistence=2,
        onset_speed="short",
        confidence=0.8,
        evidence="e",
        rationale="r",
    )
    assert industry_state_score(rel) is None


def test_all_a_and_style_formulas() -> None:
    alla = AllARelation(
        relation_id="R001",
        channel="market_backstop",
        horizon="short",
        direction=1,
        intensity=4,
        coverage=4,
        certainty=4,
        info_increment=None,
        persistence=4,
        confidence=0.5,
        evidence="e",
        rationale="r",
    )
    assert all_a_state_score(alla) == 0.5

    style = StyleRelation(
        relation_id="R001",
        channel="listing_financing",
        style_axis="size",
        horizon="medium",
        direction=1,
        relative_strength=4,
        coverage=4,
        certainty=4,
        info_increment=2,
        persistence=2,
        confidence=1.0,
        evidence="e",
        rationale="r",
    )
    assert style_a_unit(style) == 1.0
    assert style_surprise(style) == 0.5


def test_style_surprise_null_without_info_increment() -> None:
    style = StyleRelation(
        relation_id="R001",
        channel="listing_financing",
        style_axis="quality",
        horizon="medium",
        direction=-1,
        relative_strength=2,
        coverage=2,
        certainty=2,
        info_increment=None,
        persistence=None,
        confidence=0.8,
        evidence="e",
        rationale="r",
    )
    assert style_surprise(style) is None
