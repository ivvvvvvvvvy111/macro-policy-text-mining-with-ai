from __future__ import annotations

from .schemas import AllARelation, IndustryRelation, StyleRelation


def _all_present(*values) -> bool:
    return all(v is not None for v in values)


def industry_state_score(rel: IndustryRelation):
    if not _all_present(rel.direction, rel.intensity, rel.coverage, rel.certainty):
        return None
    persistence = rel.persistence if rel.persistence is not None else 0
    return (
        float(rel.direction)
        * (float(rel.intensity) / 4.0)
        * (float(rel.coverage) / 4.0)
        * (float(rel.certainty) / 4.0)
        * (0.5 + 0.5 * (float(persistence) / 4.0))
    )


def industry_news_score(rel: IndustryRelation):
    # novelty fixed null this phase
    return None


def all_a_state_score(rel: AllARelation):
    if not _all_present(
        rel.direction, rel.intensity, rel.coverage, rel.certainty, rel.persistence
    ):
        return None
    return (
        float(rel.direction)
        * (float(rel.intensity) / 4.0)
        * (float(rel.coverage) / 4.0)
        * (float(rel.certainty) / 4.0)
        * (float(rel.persistence) / 4.0)
        * float(rel.confidence)
    )


def all_a_news_score(rel: AllARelation):
    # info_increment may exist, but novelty/policy_delta are null by design;
    # NewsScore uses N (novelty) which is null this phase.
    return None


def style_a_unit(rel: StyleRelation):
    if not _all_present(
        rel.direction, rel.relative_strength, rel.coverage, rel.certainty
    ):
        return None
    return (
        float(rel.direction)
        * (float(rel.relative_strength) / 4.0)
        * (float(rel.coverage) / 4.0)
        * (float(rel.certainty) / 4.0)
        * float(rel.confidence)
    )


def style_surprise(rel: StyleRelation):
    # Surprise = A_unit * info_increment/4; if info_increment null -> null
    a = style_a_unit(rel)
    if a is None or rel.info_increment is None:
        return None
    return a * (float(rel.info_increment) / 4.0)
