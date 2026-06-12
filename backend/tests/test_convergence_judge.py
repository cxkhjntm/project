"""Tests for LLM convergence judge service."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.convergence_judge import ConvergenceJudge


@pytest.mark.asyncio
async def test_convergence_judge_applies_thresholds(db_session):
    judge = ConvergenceJudge(db_session)
    client = SimpleNamespace(
        chat_completion=AsyncMock(
            return_value=SimpleNamespace(
                content='{"agreement_score": 90, "conflict_score": 3, "reasoning": "方向一致"}'
            )
        )
    )
    judge._get_client = AsyncMock(return_value=client)

    result = await judge.judge(
        messages=[
            {"sender_id": "专家A", "content": "我赞成这个方向"},
            {"sender_id": "专家B", "content": "核心方案一致"},
        ],
        current_round=2,
        goal="设计系统",
        agreement_threshold=85,
        conflict_threshold=5,
        fallback_provider_id="provider-1",
    )

    assert result.agreement_score == 90
    assert result.conflict_score == 3
    assert result.should_converge is True
    assert result.reasoning == "方向一致"


@pytest.mark.asyncio
async def test_convergence_judge_parses_fenced_json_and_rejects_conflict(db_session):
    judge = ConvergenceJudge(db_session)
    client = SimpleNamespace(
        chat_completion=AsyncMock(
            return_value=SimpleNamespace(
                content='```json\n{"agreement_score": 90, "conflict_score": 20, "reasoning": "仍有冲突"}\n```'
            )
        )
    )
    judge._get_client = AsyncMock(return_value=client)

    result = await judge.judge(
        messages=[
            {"sender_id": "专家A", "content": "倾向使用方案A"},
            {"sender_id": "专家B", "content": "方案B更合适"},
        ],
        current_round=2,
        goal="选择方案",
        agreement_threshold=85,
        conflict_threshold=5,
        fallback_provider_id="provider-1",
    )

    assert result.agreement_score == 90
    assert result.conflict_score == 20
    assert result.should_converge is False
