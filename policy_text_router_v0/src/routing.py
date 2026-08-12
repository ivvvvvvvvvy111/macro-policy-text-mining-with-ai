from __future__ import annotations

from pathlib import Path

from .industry_catalog import SWIndustryCatalog
from .llm_client import StructuredLLM
from .schemas import Measure, RoutingDecision


class MeasureRouter:
    def __init__(self, llm: StructuredLLM, prompt_path: Path, industry_catalog_path: Path) -> None:
        self.llm = llm
        self.catalog = SWIndustryCatalog(industry_catalog_path)
        self.instructions = (
            prompt_path.read_text(encoding="utf-8").rstrip()
            + "\n\n"
            + self.catalog.prompt_text()
        )

    def route(self, *, title: str, measure: Measure) -> RoutingDecision:
        text = (
            f"原新闻标题：{title}\n"
            f"措施概括：{measure.summary}\n"
            f"政策动作：{measure.policy_action}\n"
            f"直接对象：{measure.target}\n"
            f"传导机制：{measure.mechanism}\n"
            f"原文证据：{measure.evidence}"
        )
        decision = self.llm.parse(
            instructions=self.instructions,
            user_input=text,
            schema=RoutingDecision,
        )
        if decision.style != bool(decision.style_dimensions):
            raise ValueError("style 与 style_dimensions 不一致。")
        if decision.industry != bool(decision.industries_l2):
            raise ValueError("industry 与 industries_l2 不一致。")
        seen: set[str] = set()
        for item in decision.industries_l2:
            self.catalog.validate(
                item.industry_l2_code,
                item.industry_l2_name,
                item.industry_l1_name,
            )
            if item.industry_l2_code in seen:
                raise ValueError(f"重复的申万二级行业: {item.industry_l2_code}")
            seen.add(item.industry_l2_code)
        return decision
