from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

from .llm_client import StructuredLLM
from .schemas import MeasureExtraction


class MeasureExtractor:
    def __init__(self, llm: StructuredLLM, prompt_path: Path) -> None:
        self.llm = llm
        self.instructions = prompt_path.read_text(encoding="utf-8")

    def extract(self, news: dict[str, str]) -> MeasureExtraction:
        content = news["content"]
        if len(content) > 8000:
            content = content[:8000] + "\n…[正文过长已截断]"
        news_local = dict(news)
        news_local["content"] = content
        source_text = news_local["title"] + "\n" + news_local["content"]
        text = (
            f"新闻标题：{news_local['title']}\n"
            f"发布时间：{news_local['date']}\n"
            f"来源：{news_local['source']}\n"
            f"新闻内容：{news_local['content']}"
        )
        result = self.llm.parse(
            instructions=self.instructions,
            user_input=text,
            schema=MeasureExtraction,
        )
        invalid = [m.evidence for m in result.measures if m.evidence not in source_text]
        if invalid:
            repair_text = (
                text
                + "\n\n重要校验：上一次有 evidence 不是原文连续片段。请重新完成全部输出，"
                + "每条 evidence 必须从‘新闻内容’中逐字复制一个连续片段。"
            )
            result = self.llm.parse(
                instructions=self.instructions,
                user_input=repair_text,
                schema=MeasureExtraction,
            )
        invalid = [m.evidence for m in result.measures if m.evidence not in source_text]
        if invalid:
            clauses = [news_local["title"]] + [
                part.strip()
                for part in re.split(r"(?<=[。！？；\n])", news_local["content"])
                if part.strip()
            ]
            kept = []
            for measure in result.measures:
                if measure.evidence in source_text:
                    kept.append(measure)
                    continue
                candidates = clauses + [
                    "".join(clauses[i : i + 2]) for i in range(max(0, len(clauses) - 1))
                ]
                aligned = max(
                    candidates,
                    key=lambda x: SequenceMatcher(None, measure.evidence, x).ratio(),
                    default="",
                )
                ratio = (
                    SequenceMatcher(None, measure.evidence, aligned).ratio()
                    if aligned
                    else 0.0
                )
                if ratio >= 0.30 and aligned:
                    measure.evidence = aligned
                    kept.append(measure)
            result.measures = kept
            if result.is_policy_news and not result.measures:
                result.is_policy_news = False
                result.exclusion_reason = (
                    result.exclusion_reason or "evidence无法对齐原文，已丢弃全部措施"
                )
        return result
