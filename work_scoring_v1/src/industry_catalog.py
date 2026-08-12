from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SWIndustry:
    l2_code: str
    l2_name: str
    l1_name: str


class SWIndustryCatalog:
    def __init__(self, path: Path) -> None:
        self.path = path
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError(f"申万二级行业字典为空: {path}")

        entries: list[SWIndustry] = []
        for row in rows:
            code = row.get("industry_l2_code", "").strip().removesuffix(".SI")
            name = row.get("industry_l2_name", "").strip()
            parent = row.get("industry_l1_name", "").strip()
            if not code or not name or not parent:
                raise ValueError(f"申万行业字典存在缺失字段: {row}")
            entries.append(SWIndustry(code, name, parent))

        self.entries = tuple(entries)
        self.by_code = {entry.l2_code: entry for entry in entries}
        self.by_name = {entry.l2_name: entry for entry in entries}
        if len(self.by_code) != len(entries) or len(self.by_name) != len(entries):
            raise ValueError("申万二级行业字典存在重复代码或重复名称。")

    def validate(self, code: str, name: str, l1_name: str) -> None:
        normalized_code = code.strip().removesuffix(".SI")
        entry = self.by_code.get(normalized_code)
        if entry is None:
            raise ValueError(f"模型输出了字典外的申万二级行业代码: {code}")
        if (entry.l2_name, entry.l1_name) != (name.strip(), l1_name.strip()):
            raise ValueError(
                f"申万行业代码与名称不一致: {code}/{name}/{l1_name}; "
                f"应为 {entry.l2_name}/{entry.l1_name}"
            )

    def canonicalize(self, code: str, name: str = "", l1_name: str = "") -> SWIndustry:
        """Prefer code; if code valid, return catalog names (ignore model name noise)."""
        normalized_code = code.strip().removesuffix(".SI")
        entry = self.by_code.get(normalized_code)
        if entry is not None:
            return entry
        # fallback by exact name
        by_name = self.by_name.get(name.strip())
        if by_name is not None:
            return by_name
        raise ValueError(f"无法规范化申万行业: {code}/{name}/{l1_name}")

    def prompt_text(self) -> str:
        groups: dict[str, list[SWIndustry]] = {}
        for entry in self.entries:
            groups.setdefault(entry.l1_name, []).append(entry)
        lines = ["申万2021版二级行业允许值（代码:名称）："]
        for parent, children in groups.items():
            values = "、".join(f"{item.l2_code}:{item.l2_name}" for item in children)
            lines.append(f"- {parent}：{values}")
        return "\n".join(lines)
