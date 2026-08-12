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
        source_text = news["title"] + "\n" + news["content"]
        text = (
            f"新闻标题：{news['title']}\n"
            f"发布时间：{news['date']}\n"
            f"来源：{news['source']}\n"
            f"新闻内容：{news['content']}"
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
            clauses = [news["title"]] + [part.strip() for part in re.split(r"(?<=[。！？；])", news["content"]) if part.strip()]
            for measure in result.measures:
                if measure.evidence in source_text:
                    continue
                candidates = clauses + ["".join(clauses[i : i + 2]) for i in range(max(0, len(clauses) - 1))]
                aligned = max(candidates, key=lambda x: SequenceMatcher(None, measure.evidence, x).ratio(), default="")
                ratio = SequenceMatcher(None, measure.evidence, aligned).ratio() if aligned else 0.0
                if ratio < 0.35:
                    raise ValueError("evidence 无法可靠对齐到原文连续片段")
                measure.evidence = aligned
        if any(m.evidence not in source_text for m in result.measures):
            raise ValueError("evidence 原文对齐后仍未通过校验")
        return result
