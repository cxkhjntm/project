"""LLM-based convergence judge for expert discussions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import Provider
from app.models.settings import AppSettings
from app.services.crypto import crypto_service
from app.services.model_client import create_model_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ConvergenceResult:
    """Structured convergence judgment result."""

    agreement_score: int
    conflict_score: int
    should_converge: bool
    reasoning: str


class ConvergenceJudge:
    """Use a model to decide whether a discussion has actually converged."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def judge(
        self,
        messages: list[dict[str, Any]],
        current_round: int,
        goal: str,
        agreement_threshold: int = 85,
        conflict_threshold: int = 5,
        provider_id: str | None = None,
        model_override: str | None = None,
        fallback_provider_id: str | None = None,
    ) -> ConvergenceResult:
        """Analyze expert messages and decide whether convergence thresholds are met."""
        client = await self._get_client(provider_id, model_override, fallback_provider_id)
        prompt = self._build_prompt(messages, current_round, goal)
        response = await client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )
        payload = self._parse_json(response.content)
        agreement_score = self._bounded_score(payload.get("agreement_score"))
        conflict_score = self._bounded_score(payload.get("conflict_score"))
        reasoning = str(payload.get("reasoning", "")).strip()[:200]
        should_converge = (
            agreement_score >= agreement_threshold
            and conflict_score <= conflict_threshold
        )
        return ConvergenceResult(
            agreement_score=agreement_score,
            conflict_score=conflict_score,
            should_converge=should_converge,
            reasoning=reasoning,
        )

    async def _get_client(
        self,
        provider_id: str | None,
        model_override: str | None,
        fallback_provider_id: str | None,
    ):
        settings = await self._get_settings()
        selected_provider_id = (
            provider_id
            or settings.get("convergence_provider_id")
            or fallback_provider_id
        )
        if not selected_provider_id:
            raise ValueError("No convergence judge provider configured")

        provider = await self.session.get(Provider, selected_provider_id)
        if provider is None:
            raise ValueError(f"Convergence judge provider not found: {selected_provider_id}")

        selected_model = (
            model_override
            or settings.get("convergence_model_override")
            or provider.default_model
        )
        api_key = crypto_service.decrypt(provider.api_key_encrypted)
        return create_model_client(
            base_url=provider.base_url,
            api_key=api_key,
            model=selected_model,
            temperature=0,
            max_tokens=500,
        )

    async def _get_settings(self) -> dict[str, str]:
        result = await self.session.execute(select(AppSettings))
        return {
            item.key: item.value
            for item in result.scalars().all()
            if item.value
        }

    def _build_prompt(
        self,
        messages: list[dict[str, Any]],
        current_round: int,
        goal: str,
    ) -> str:
        return f"""你是一个讨论收敛判断分析器。请分析以下专家讨论，判断讨论的收敛程度。

## 讨论目标
{goal}

## 当前轮次
第 {current_round} 轮

## 本轮专家发言
{self._format_messages(messages)}

## 输出要求
请严格输出以下 JSON 格式（不要输出其他内容）：
```json
{{
  "agreement_score": <0-100的整数，表示专家们在核心方向上的一致程度>,
  "conflict_score": <0-100的整数，表示专家之间存在的方案冲突程度>,
  "reasoning": "<简要说明判断依据，50字以内>"
}}
```

## 判断标准
- agreement_score: 所有专家对核心问题的方向是否一致。注意“同意某个细节”不代表整体收敛。
- conflict_score: 是否存在互斥的技术路线、根本性分歧或未解决的关键争议。
- 仅当所有专家都对核心方向明确表态一致时，agreement_score 才应 >= 85。
- 如果任何专家提出了未被回应的重大反对意见，conflict_score 应 >= 20。"""

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        lines = []
        for message in messages:
            sender = message.get("sender_id") or message.get("sender_type") or "未知专家"
            content = str(message.get("content", "")).strip()
            if len(content) > 1000:
                content = content[:1000] + "...(已截断)"
            lines.append(f"### {sender}\n{content}")
        return "\n\n".join(lines) if lines else "无专家发言"

    def _parse_json(self, content: str) -> dict[str, Any]:
        text = content.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1)
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Convergence judge returned non-object JSON")
        return data

    def _bounded_score(self, value: Any) -> int:
        score = int(value)
        return max(0, min(100, score))
