import json

import pytest

from gameconfig_agent.cli import run_real_demo
from gameconfig_agent.prompts import load_prompt
from gameconfig_agent.providers.openai_compatible import OpenAICompatibleProvider
from gameconfig_agent.providers import MockLLMProvider
from gameconfig_agent.real_run import aggregate_metrics, run_real_sample


REQUIREMENT = "设计一个新手武器 Training Sword，基础攻击力 50，可升级 3 次，每级攻击力 +5。升级消耗金币和强化石。该武器作为新手任务奖励发放，只能领取一次。"


def test_prompt_templates_exist():
    for name in ("generator", "reviewer", "repairer", "test_scenario"):
        prompt = load_prompt(name)
        assert "Return only valid JSON" in prompt


def test_openai_compatible_provider_reads_environment(monkeypatch):
    monkeypatch.setenv("GAMECONFIG_LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("GAMECONFIG_LLM_API_KEY", "secret-from-env")
    monkeypatch.setenv("GAMECONFIG_LLM_MODEL", "test-model")

    provider = OpenAICompatibleProvider()

    assert provider.base_url == "https://example.test/v1"
    assert provider.api_key == "secret-from-env"
    assert provider.model == "test-model"
    assert provider._chat_completions_url() == "https://example.test/v1/chat/completions"


def test_openai_compatible_provider_requires_environment(monkeypatch):
    monkeypatch.delenv("GAMECONFIG_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("GAMECONFIG_LLM_API_KEY", raising=False)
    monkeypatch.delenv("GAMECONFIG_LLM_MODEL", raising=False)

    with pytest.raises(ValueError):
        OpenAICompatibleProvider()


def test_run_real_demo_with_mock_provider_generates_phase2_outputs(tmp_path):
    input_path = tmp_path / "requirement.txt"
    input_path.write_text(REQUIREMENT, encoding="utf-8")

    result = run_real_demo(input_path, tmp_path / "phase2", "mock")

    assert result["provider"] == "mock"
    assert result["metrics"]["sample_count"] == 4
    assert result["metrics"]["json_parse_success_rate"] == 1.0
    assert result["metrics"]["schema_pass_rate"] == 1.0
    assert result["metrics"]["final_validation_pass_rate"] == 1.0
    assert result["metrics"]["repair_success_rate"] == 1.0
    assert result["metrics"]["test_scenario_coverage_rate"] == 1.0
    assert result["metrics"]["badcase_count"] == 0

    expected_files = {
        "real_run_result.json",
        "real_run_trace.json",
        "real_run_report.md",
        "badcases.md",
    }
    assert expected_files == {path.name for path in (tmp_path / "phase2").iterdir()}
    badcases = (tmp_path / "phase2" / "badcases.md").read_text(encoding="utf-8")
    assert "- None" in badcases

    real_run_result = json.loads((tmp_path / "phase2" / "real_run_result.json").read_text(encoding="utf-8"))
    assert real_run_result["metrics"]["sample_count"] == 4


def test_aggregate_metrics_counts_badcases():
    metrics = aggregate_metrics(
        [
            {
                "trace": [{"json_parse_success": False}],
                "provider_metrics": [{"latency_ms": 1, "token_estimate": 5, "usage": None}],
                "draft_validation": {"schema_passed": False},
                "final_validation": {"passed": False},
                "repair_actions": [],
                "evaluation": {"coverage": 0},
                "badcases": [{"reason": "json parse failed"}],
            }
        ]
    )

    assert metrics["json_parse_success_rate"] == 0
    assert metrics["badcase_count"] == 1


def test_run_real_sample_only_runs_interactive_requirement():
    result = run_real_sample(MockLLMProvider(), REQUIREMENT)

    assert result["metrics"]["sample_count"] == 1
    assert "model" in result
    assert [sample["sample_id"] for sample in result["results"]] == ["real_demo_input"]
