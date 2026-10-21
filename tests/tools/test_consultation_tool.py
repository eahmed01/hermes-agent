"""Tests for consultation response-budget calculations."""

import asyncio
import json
from unittest.mock import AsyncMock

from tools import consultation_tool

from tools.consultation_tool import (
    _estimate_cost,
    _estimate_input_cost,
    _max_output_tokens_for_budget,
)


def test_configured_output_cap_is_not_reduced_to_1000_tokens_per_dollar():
    """A $5 budget at $20/M output can support the configured 30k cap."""
    cap = _max_output_tokens_for_budget(
        input_chars=20_000,
        remaining_budget=5.0,
        max_output_tokens=30_000,
        input_price=5.0,
        output_price=20.0,
    )

    assert cap == 30_000


def test_output_budget_reserves_estimated_input_cost():
    """The affordable output is based on budget remaining after input."""
    cap = _max_output_tokens_for_budget(
        input_chars=400_000,  # 100k estimated input tokens, costing $0.20
        remaining_budget=0.50,
        max_output_tokens=30_000,
        input_price=2.0,
        output_price=20.0,
    )

    assert cap == 15_000


def test_exhausted_input_budget_allows_no_output():
    cap = _max_output_tokens_for_budget(
        input_chars=1_000_000,  # 250k estimated tokens at $20/M costs $5
        remaining_budget=5.0,
        max_output_tokens=30_000,
        input_price=20.0,
        output_price=20.0,
    )

    assert cap == 0


def test_zero_output_price_uses_configured_cap_when_input_is_affordable():
    cap = _max_output_tokens_for_budget(
        input_chars=4_000,
        remaining_budget=1.0,
        max_output_tokens=12_000,
        input_price=5.0,
        output_price=0.0,
    )

    assert cap == 12_000


def test_estimated_cost_uses_input_estimator_and_configured_output_cap():
    assert _estimate_input_cost(4_000, 5.0) == 0.005
    assert _estimate_cost(4_000, 30_000, 5.0, 20.0) == 0.605


def test_consultation_ask_passes_full_configured_cap_to_provider(monkeypatch):
    config = {
        "models": [{
            "name": "opus",
            "provider": "anthropic",
            "model": "test-model",
            "budget_per_call": 5.0,
            "max_output_tokens": 30_000,
            "input_price_per_m": 5.0,
            "output_price_per_m": 20.0,
        }],
        "session_budget": 20.0,
        "session_budget_alert": 0.8,
        "require_approval": False,
    }
    provider_call = AsyncMock(return_value=("complete answer", 100, 100))
    monkeypatch.setattr(consultation_tool, "_load_consultation_config", lambda: config)
    monkeypatch.setattr(consultation_tool, "_get_session_spent", lambda: 0.0)
    monkeypatch.setattr(consultation_tool, "_resolve_api_key", lambda _model: "test-key")
    monkeypatch.setattr(consultation_tool, "_call_anthropic", provider_call)
    monkeypatch.setattr(consultation_tool, "_record_cost", lambda *_args: None)

    result = asyncio.run(consultation_tool.consultation_ask({
        "model": "opus",
        "prompt": "Give a concise advisory.",
    }))

    assert json.loads(result)["response"] == "complete answer"
    call_args = provider_call.await_args
    assert call_args is not None
    assert call_args.args[3] == 30_000
