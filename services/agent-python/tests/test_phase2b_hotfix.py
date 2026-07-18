import json

from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.providers.base import LLMResponse
from gameconfig_agent.real_run import RealRunPipeline, export_real_run
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


VALID_REQUIREMENT = {
    "request_id": "req",
    "item_name": "Training Sword",
    "category": "beginner_weapon",
    "base_attack": 50,
    "upgrade_times": 3,
    "upgrade_attack_bonus": 5,
    "cost_item_tags": ["gold", "refine_stone"],
    "reward_channel": "beginner_quest",
    "once_only": True,
}


def _base_configs(**overrides):
    configs = {
        "item_config": [],
        "weapon_config": [],
        "upgrade_config": [],
        "reward_config": [],
    }
    configs.update(overrides)
    return configs


def test_schema_validator_handles_bad_upgrade_row_without_crashing():
    errors = SchemaValidatorTool().validate(
        VALID_REQUIREMENT,
        _base_configs(upgrade_config=["bad string"]),
    )

    assert any(error["path"] == "upgrade_config[0]" for error in errors)
    assert any("Expected object, got str" in error["message"] for error in errors)


def test_schema_validator_handles_bad_cost_item_without_crashing():
    errors = SchemaValidatorTool().validate(
        VALID_REQUIREMENT,
        _base_configs(
            upgrade_config=[
                {
                    "weapon_id": "weapon_training_sword",
                    "level": 1,
                    "attack_bonus": 5,
                    "cost_items": ["bad cost"],
                }
            ]
        ),
    )

    assert any(error["path"] == "upgrade_config[0].cost_items[0]" for error in errors)
    assert any("Expected object, got str" in error["message"] for error in errors)


def test_schema_validator_handles_non_list_groups_without_crashing():
    errors = SchemaValidatorTool().validate(
        VALID_REQUIREMENT,
        _base_configs(item_config="bad items", weapon_config="bad weapons", reward_config="bad rewards"),
    )

    assert any(error["path"] == "item_config" and "Expected list" in error["message"] for error in errors)
    assert any(error["path"] == "weapon_config" and "Expected list" in error["message"] for error in errors)
    assert any(error["path"] == "reward_config" and "Expected list" in error["message"] for error in errors)


def test_dotenv_loader_reads_values_without_overriding_existing_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "GAMECONFIG_LLM_BASE_URL=https://from-env-file.example/v1",
                "GAMECONFIG_LLM_API_KEY=from-env-file",
                "GAMECONFIG_LLM_MODEL=model-from-env-file",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GAMECONFIG_LLM_API_KEY", "already-set")
    monkeypatch.delenv("GAMECONFIG_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("GAMECONFIG_LLM_MODEL", raising=False)

    loaded = load_dotenv(env_file)

    assert loaded["GAMECONFIG_LLM_BASE_URL"] == "https://from-env-file.example/v1"
    assert "GAMECONFIG_LLM_API_KEY" not in loaded
    assert loaded["GAMECONFIG_LLM_MODEL"] == "model-from-env-file"
    assert loaded["GAMECONFIG_LLM_API_KEY"] if "GAMECONFIG_LLM_API_KEY" in loaded else True
    assert __import__("os").environ["GAMECONFIG_LLM_API_KEY"] == "already-set"


class MalformedProvider:
    name = "malformed"
    model = "malformed-model"

    def complete_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str) -> LLMResponse:
        if prompt_name == "generator":
            content = json.dumps(
                {
                    "structured_requirement": VALID_REQUIREMENT,
                    "assumptions": [],
                    "draft_configs": _base_configs(upgrade_config=["bad string"]),
                }
            )
        else:
            content = "{}"
        return LLMResponse(content=content, latency_ms=1, token_estimate=1)


def test_real_run_pipeline_records_badcase_for_malformed_provider_output(tmp_path):
    result = RealRunPipeline(MalformedProvider()).run("training sword", sample_id="bad_sample")
    files = export_real_run({"provider": "malformed", "results": [result], "metrics": {"sample_count": 1, "json_parse_success_rate": 1, "schema_pass_rate": 0, "final_validation_pass_rate": 0, "repair_success_rate": 0, "test_scenario_coverage_rate": 0, "latency_ms": {"total": 1, "average": 1}, "token_estimate": 1, "usage": None, "badcase_count": len(result["badcases"])}}, tmp_path)

    assert result["badcases"]
    assert any(badcase["stage"] == "generator_schema_validation" for badcase in result["badcases"])
    badcases_md = (tmp_path / "badcases.md").read_text(encoding="utf-8")
    assert "SchemaValidationError" in badcases_md
    assert "malformed-model" in badcases_md
    assert {path.name for path in files} == {
        "real_run_result.json",
        "real_run_trace.json",
        "real_run_report.md",
        "badcases.md",
    }
