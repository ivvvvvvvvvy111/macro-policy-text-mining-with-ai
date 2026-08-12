from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model_measure: str
    model_routing: str
    model_scoring: str
    timeout_seconds: float
    max_tokens_measure: int
    max_tokens_routing: int
    max_tokens_scoring: int
    project_root: Path = PROJECT_ROOT
    repo_root: Path = REPO_ROOT

    @classmethod
    def from_env(cls, require_api_key: bool = True) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        provider = os.getenv("LLM_PROVIDER", "siliconflow").strip().lower()
        if provider != "siliconflow":
            raise RuntimeError("当前仅配置了 siliconflow provider。")
        api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
        if require_api_key and (not api_key or api_key == "your-key-here"):
            raise RuntimeError(
                "未找到有效的 SILICONFLOW_API_KEY。请复制 .env.example 为 .env 并填入 Key。"
            )
        return cls(
            api_key=api_key,
            base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").strip(),
            model_measure=os.getenv("SILICONFLOW_MODEL_MEASURE", "Qwen/Qwen3.5-9B").strip(),
            model_routing=os.getenv("SILICONFLOW_MODEL_ROUTING", "Qwen/Qwen3.5-9B").strip(),
            model_scoring=os.getenv(
                "SILICONFLOW_MODEL_SCORING", "Qwen/Qwen3.5-35B-A3B"
            ).strip(),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "180")),
            max_tokens_measure=int(os.getenv("LLM_MAX_TOKENS_MEASURE", "2500")),
            max_tokens_routing=int(os.getenv("LLM_MAX_TOKENS_ROUTING", "2000")),
            max_tokens_scoring=int(os.getenv("LLM_MAX_TOKENS_SCORING", "3500")),
        )
