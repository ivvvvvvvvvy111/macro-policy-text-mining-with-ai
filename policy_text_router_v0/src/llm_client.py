from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, TypeVar

from openai import OpenAI, RateLimitError
from pydantic import BaseModel

from .config import Settings

T = TypeVar("T", bound=BaseModel)


class StructuredLLM:
    """SiliconFlow OpenAI-compatible JSON-mode client with validation and retry."""

    def __init__(self, settings: Settings) -> None:
        self.model = settings.model
        self.max_tokens = settings.max_tokens
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            max_retries=3,
        )
        self._lock = threading.Lock()
        self._stats: dict[str, float] = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_seconds": 0,
            "validation_retries": 0,
            "rate_limit_retries": 0,
        }

    @staticmethod
    def _extract_json(text: str) -> str:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end < start:
            raise ValueError("模型输出中未找到完整 JSON 对象")
        return cleaned[start : end + 1]

    def _record(self, response: Any, latency: float) -> None:
        usage = getattr(response, "usage", None)
        with self._lock:
            self._stats["calls"] += 1
            self._stats["latency_seconds"] += latency
            if usage:
                for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    self._stats[name] += float(getattr(usage, name, 0) or 0)

    def stats(self) -> dict[str, int | float | str]:
        with self._lock:
            values = dict(self._stats)
        values["model"] = self.model
        values["calls"] = int(values["calls"])
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "validation_retries", "rate_limit_retries"):
            values[key] = int(values[key])
        values["latency_seconds"] = round(float(values["latency_seconds"]), 3)
        return values

    def parse(self, *, instructions: str, user_input: str, schema: type[T]) -> T:
        json_schema = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        system = (
            instructions
            + "\n\n只输出一个JSON对象，不要输出Markdown代码块或额外说明。"
            + "\n必须满足以下JSON Schema：\n"
            + json_schema
        )
        last_error: Exception | None = None
        current_input = user_input
        for attempt in range(3):
            response = None
            started = time.perf_counter()
            for rate_attempt in range(6):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": current_input},
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=self.max_tokens,
                        temperature=0.1,
                        extra_body={"enable_thinking": False},
                    )
                    break
                except RateLimitError:
                    if rate_attempt == 5:
                        raise
                    with self._lock:
                        self._stats["rate_limit_retries"] += 1
                    time.sleep(min(60, 8 * (2**rate_attempt)))
            if response is None:
                raise RuntimeError("API请求未返回响应")
            self._record(response, time.perf_counter() - started)
            content = response.choices[0].message.content or ""
            try:
                return schema.model_validate(json.loads(self._extract_json(content)))
            except Exception as exc:
                last_error = exc
                with self._lock:
                    self._stats["validation_retries"] += 1
                current_input = (
                    user_input
                    + "\n\n上一次输出未通过结构校验。请重新生成完整JSON；不要解释。"
                    + f"\n校验错误：{str(exc)[:500]}"
                )
        raise RuntimeError(f"模型连续3次未返回有效结构: {last_error}")
