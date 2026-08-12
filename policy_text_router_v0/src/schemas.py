from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Measure(StrictModel):
    measure_id: str = Field(description="新闻内从 M001 开始编号")
    summary: str = Field(description="一条独立政策措施的简洁概括")
    policy_action: str = Field(description="政策动作，如降低、提高、设立、限制、支持")
    target: str = Field(description="政策直接作用对象")
    mechanism: str = Field(description="政策影响经济或市场变量的直接机制")
    evidence: str = Field(description="新闻中支持该措施的最短必要证据")


class MeasureExtraction(StrictModel):
    schema_version: Literal["measure.v1"]
    is_policy_news: bool
    event_summary: str
    measures: list[Measure]
    exclusion_reason: str = Field(description="若不是政策新闻，说明原因；否则为空字符串")


class SWIndustryTag(StrictModel):
    industry_l2_code: str = Field(description="申万2021二级行业代码，不含 .SI 后缀")
    industry_l2_name: str = Field(description="申万2021二级行业名称")
    industry_l1_name: str = Field(description="该二级行业对应的申万一级行业名称")


class RoutingDecision(StrictModel):
    schema_version: Literal["routing.v2"]
    all_a: bool = Field(description="是否进入全A市场研究")
    style: bool = Field(description="是否进入风格研究")
    industry: bool = Field(description="是否进入行业研究")
    style_dimensions: list[
        Literal["size", "value_growth", "quality", "dividend", "liquidity", "volatility", "other"]
    ]
    industries_l2: list[SWIndustryTag] = Field(max_length=5)
    primary_route: Literal["all_a", "style", "industry", "multiple", "none"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
