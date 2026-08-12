from __future__ import annotations

from pathlib import Path
from typing import Any

from .formulas import (
    all_a_news_score,
    all_a_state_score,
    industry_news_score,
    industry_state_score,
    style_a_unit,
    style_surprise,
)
from .industry_catalog import SWIndustryCatalog
from .llm_client import StructuredLLM
from .schemas import (
    AllAScoreResult,
    IndustryScoreResult,
    Measure,
    RoutingDecision,
    StyleScoreResult,
)


class RelationScorer:
    def __init__(
        self,
        llm: StructuredLLM,
        *,
        industry_prompt: Path,
        all_a_prompt: Path,
        style_prompt: Path,
        industry_catalog_path: Path,
    ) -> None:
        self.llm = llm
        self.industry_instructions = industry_prompt.read_text(encoding="utf-8")
        self.all_a_instructions = all_a_prompt.read_text(encoding="utf-8")
        self.style_instructions = style_prompt.read_text(encoding="utf-8")
        self.catalog = SWIndustryCatalog(industry_catalog_path)

    @staticmethod
    def _measure_block(title: str, measure: Measure) -> str:
        return (
            f"原新闻标题：{title}\n"
            f"措施ID：{measure.measure_id}\n"
            f"措施概括：{measure.summary}\n"
            f"政策动作：{measure.policy_action}\n"
            f"直接对象：{measure.target}\n"
            f"传导机制：{measure.mechanism}\n"
            f"原文证据：{measure.evidence}"
        )

    def score_industry(
        self, *, title: str, measure: Measure, routing: RoutingDecision
    ) -> IndustryScoreResult:
        industries = "\n".join(
            f"- {i.industry_l2_code}:{i.industry_l2_name}（{i.industry_l1_name}）"
            for i in routing.industries_l2
        )
        text = (
            self._measure_block(title, measure)
            + "\n路由命中行业：\n"
            + (industries or "(空)")
            + "\n\n注意：本阶段无历史比较基准，不要输出 policy_delta / novelty；"
            "这两个字段由系统固定为 null。"
        )
        result = self.llm.parse(
            instructions=self.industry_instructions,
            user_input=text,
            schema=IndustryScoreResult,
        )
        for rel in result.relations:
            entry = self.catalog.canonicalize(
                rel.industry_l2_code, rel.industry_l2_name, rel.industry_l1_name
            )
            rel.industry_l2_code = entry.l2_code
            rel.industry_l2_name = entry.l2_name
            rel.industry_l1_name = entry.l1_name
        return result

    def score_all_a(self, *, title: str, measure: Measure) -> AllAScoreResult:
        text = (
            self._measure_block(title, measure)
            + "\n\n注意：本阶段无历史比较基准；policy_delta 与 novelty 由系统固定为 null。"
            "信息增量 info_increment 若证据不足可输出 null。"
        )
        return self.llm.parse(
            instructions=self.all_a_instructions,
            user_input=text,
            schema=AllAScoreResult,
        )

    def score_style(self, *, title: str, measure: Measure) -> StyleScoreResult:
        text = (
            self._measure_block(title, measure)
            + "\n\n注意：禁止直接回答“利好什么风格”。"
            "先识别渠道与相对受益的公司特征，再映射到风格轴。"
            "本阶段 policy_delta / novelty 由系统固定为 null。"
        )
        return self.llm.parse(
            instructions=self.style_instructions,
            user_input=text,
            schema=StyleScoreResult,
        )


def flatten_industry_rows(
    *,
    news: dict[str, str],
    measure: dict[str, Any],
    routing: dict[str, Any],
    result: IndustryScoreResult,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in result.relations:
        rows.append(
            {
                "track": "industry",
                "news_id": news["news_id"],
                "date": news.get("date", ""),
                "title": news.get("title", ""),
                "source": news.get("source", ""),
                "url": news.get("url", ""),
                "measure_id": measure["measure_id"],
                "measure_summary": measure["summary"],
                "relation_id": rel.relation_id,
                "channel": rel.channel,
                "horizon": rel.onset_speed,
                "style_axis": "",
                "industry_l2_code": rel.industry_l2_code,
                "industry_l2_name": rel.industry_l2_name,
                "industry_l1_name": rel.industry_l1_name,
                "directness": rel.directness,
                "direction": rel.direction,
                "intensity": rel.intensity,
                "relative_strength": None,
                "coverage": rel.coverage,
                "certainty": rel.certainty,
                "persistence": rel.persistence,
                "info_increment": None,
                "policy_delta": None,
                "novelty": None,
                "confidence": rel.confidence,
                "state_score": industry_state_score(rel),
                "news_score": industry_news_score(rel),
                "a_unit": None,
                "surprise": None,
                "null_reason": "缺少比较基准",
                "evidence": rel.evidence,
                "rationale": rel.rationale,
                "routing_primary": routing.get("primary_route"),
                "routing_confidence": routing.get("confidence"),
            }
        )
    return rows


def flatten_all_a_rows(
    *,
    news: dict[str, str],
    measure: dict[str, Any],
    routing: dict[str, Any],
    result: AllAScoreResult,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in result.relations:
        rows.append(
            {
                "track": "all_a",
                "news_id": news["news_id"],
                "date": news.get("date", ""),
                "title": news.get("title", ""),
                "source": news.get("source", ""),
                "url": news.get("url", ""),
                "measure_id": measure["measure_id"],
                "measure_summary": measure["summary"],
                "relation_id": rel.relation_id,
                "channel": rel.channel,
                "horizon": rel.horizon,
                "style_axis": "",
                "industry_l2_code": "",
                "industry_l2_name": "",
                "industry_l1_name": "",
                "directness": "",
                "direction": rel.direction,
                "intensity": rel.intensity,
                "relative_strength": None,
                "coverage": rel.coverage,
                "certainty": rel.certainty,
                "persistence": rel.persistence,
                "info_increment": rel.info_increment,
                "policy_delta": None,
                "novelty": None,
                "confidence": rel.confidence,
                "state_score": all_a_state_score(rel),
                "news_score": all_a_news_score(rel),
                "a_unit": None,
                "surprise": None,
                "null_reason": "缺少比较基准",
                "evidence": rel.evidence,
                "rationale": rel.rationale,
                "routing_primary": routing.get("primary_route"),
                "routing_confidence": routing.get("confidence"),
            }
        )
    return rows


def flatten_style_rows(
    *,
    news: dict[str, str],
    measure: dict[str, Any],
    routing: dict[str, Any],
    result: StyleScoreResult,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in result.relations:
        rows.append(
            {
                "track": "style",
                "news_id": news["news_id"],
                "date": news.get("date", ""),
                "title": news.get("title", ""),
                "source": news.get("source", ""),
                "url": news.get("url", ""),
                "measure_id": measure["measure_id"],
                "measure_summary": measure["summary"],
                "relation_id": rel.relation_id,
                "channel": rel.channel,
                "horizon": rel.horizon,
                "style_axis": rel.style_axis,
                "industry_l2_code": "",
                "industry_l2_name": "",
                "industry_l1_name": "",
                "directness": "",
                "direction": rel.direction,
                "intensity": None,
                "relative_strength": rel.relative_strength,
                "coverage": rel.coverage,
                "certainty": rel.certainty,
                "persistence": rel.persistence,
                "info_increment": rel.info_increment,
                "policy_delta": None,
                "novelty": None,
                "confidence": rel.confidence,
                "state_score": None,
                "news_score": None,
                "a_unit": style_a_unit(rel),
                "surprise": style_surprise(rel),
                "null_reason": "缺少比较基准",
                "evidence": rel.evidence,
                "rationale": rel.rationale,
                "routing_primary": routing.get("primary_route"),
                "routing_confidence": routing.get("confidence"),
            }
        )
    return rows
