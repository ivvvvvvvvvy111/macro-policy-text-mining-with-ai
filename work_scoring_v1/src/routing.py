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
        if decision.style and not decision.style_dimensions:
            decision.style = False
        if (not decision.style) and decision.style_dimensions:
            decision.style = True
        if decision.industry and not decision.industries_l2:
            decision.industry = False
        if (not decision.industry) and decision.industries_l2:
            decision.industry = True

        seen: set[str] = set()
        deduped = []
        for item in decision.industries_l2:
            entry = self.catalog.canonicalize(
                item.industry_l2_code,
                item.industry_l2_name,
                item.industry_l1_name,
            )
            if entry.l2_code in seen:
                continue
            item.industry_l2_code = entry.l2_code
            item.industry_l2_name = entry.l2_name
            item.industry_l1_name = entry.l1_name
            seen.add(entry.l2_code)
            deduped.append(item)
        decision.industries_l2 = deduped
        if decision.industry != bool(decision.industries_l2):
            decision.industry = bool(decision.industries_l2)

        true_count = sum([decision.all_a, decision.style, decision.industry])
        if true_count == 0:
            decision.primary_route = "none"
        elif true_count > 1:
            decision.primary_route = "multiple"
        elif decision.all_a:
            decision.primary_route = "all_a"
        elif decision.style:
            decision.primary_route = "style"
        else:
            decision.primary_route = "industry"
        return decision
