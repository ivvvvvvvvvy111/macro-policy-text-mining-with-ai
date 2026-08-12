from __future__ import annotations

from typing import List, Literal, Optional

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
    measures: List[Measure]
    exclusion_reason: str = Field(description="若不是政策新闻，说明原因；否则为空字符串")


class SWIndustryTag(StrictModel):
    industry_l2_code: str = Field(description="申万2021二级行业代码，不含 .SI 后缀")
    industry_l2_name: str = Field(description="申万2021二级行业名称")
    industry_l1_name: str = Field(description="该二级行业对应的申万一级行业名称")


class RoutingDecision(StrictModel):
    schema_version: Literal["routing.v2"]
    all_a: bool
    style: bool
    industry: bool
    style_dimensions: List[
        Literal["size", "value_growth", "quality", "dividend", "liquidity", "volatility", "other"]
    ]
    industries_l2: List[SWIndustryTag] = Field(max_length=5)
    primary_route: Literal["all_a", "style", "industry", "multiple", "none"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


IndustryChannel = Literal[
    "demand",
    "price",
    "cost",
    "supply",
    "competition",
    "capex",
    "targeted_finance",
    "technology",
]

AllAChannel = Literal[
    "market_backstop",
    "incremental_capital",
    "trading_cost_liquidity",
    "financing_share_supply",
    "governance_quality",
    "regulatory_risk",
    "institutional_openness",
    "uncertainty_coordination",
]

StyleAxis = Literal[
    "size",
    "growth_value",
    "quality",
    "risk",
    "dividend",
    "liquidity",
]

StyleChannel = Literal[
    "listing_financing",
    "trading_system",
    "corporate_governance",
    "mna_restructuring",
    "dividend_buyback",
    "long_term_capital",
    "other",
]

Horizon = Literal["immediate", "short", "medium", "long", "unknown"]


class IndustryRelation(StrictModel):
    relation_id: str
    industry_l2_code: str
    industry_l2_name: str
    industry_l1_name: str
    channel: IndustryChannel
    directness: Literal["direct", "indirect"]
    direction: Optional[int] = Field(default=None, ge=-2, le=2)
    intensity: Optional[int] = Field(default=None, ge=0, le=4)
    coverage: Optional[int] = Field(default=None, ge=0, le=4)
    certainty: Optional[int] = Field(default=None, ge=0, le=4)
    persistence: Optional[int] = Field(default=None, ge=0, le=4)
    onset_speed: Horizon = "unknown"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    rationale: str


class IndustryScoreResult(StrictModel):
    schema_version: Literal["industry_score.v1"]
    relations: List[IndustryRelation]


class AllARelation(StrictModel):
    relation_id: str
    channel: AllAChannel
    horizon: Horizon
    direction: Optional[int] = Field(default=None, ge=-1, le=1)
    intensity: Optional[int] = Field(default=None, ge=0, le=4)
    coverage: Optional[int] = Field(default=None, ge=0, le=4)
    certainty: Optional[int] = Field(default=None, ge=0, le=4)
    info_increment: Optional[int] = Field(default=None, ge=0, le=4)
    persistence: Optional[int] = Field(default=None, ge=0, le=4)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    rationale: str


class AllAScoreResult(StrictModel):
    schema_version: Literal["all_a_score.v1"]
    relations: List[AllARelation]


class StyleRelation(StrictModel):
    relation_id: str
    channel: StyleChannel
    style_axis: StyleAxis
    horizon: Horizon
    direction: Optional[int] = Field(default=None, ge=-1, le=1)
    relative_strength: Optional[int] = Field(default=None, ge=0, le=4)
    coverage: Optional[int] = Field(default=None, ge=0, le=4)
    certainty: Optional[int] = Field(default=None, ge=0, le=4)
    info_increment: Optional[int] = Field(default=None, ge=0, le=4)
    persistence: Optional[int] = Field(default=None, ge=0, le=4)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    rationale: str


class StyleScoreResult(StrictModel):
    schema_version: Literal["style_score.v1"]
    relations: List[StyleRelation]


class ComposedScores(StrictModel):
    policy_delta: Optional[int] = None
    novelty: Optional[int] = None
    state_score: Optional[float] = None
    news_score: Optional[float] = None
    a_unit: Optional[float] = None
    surprise: Optional[float] = None
    null_reason: str = "缺少比较基准"
