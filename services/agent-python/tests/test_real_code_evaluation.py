import json
from pathlib import Path

from fastapi.testclient import TestClient
import workflow.real_code_evaluation as real_code_evaluation_module

from api.server import create_unified_app
from gameconfig_agent.cli import main
from gameconfig_agent.providers.base import LLMResponse
from workflow.real_code_evaluation import (
    load_real_code_dataset,
    replay_real_code_evaluation,
    run_real_code_evaluation,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAFE_PATCH = REPOSITORY_ROOT / "examples/csharp/runtime_args_null_guard.patch"


class FakeProvider:
    model = "fake-real-code-model"

    def __init__(self, content: str) -> None:
        self.content = content

    def complete_json(self, **_kwargs) -> LLMResponse:
        return LLMResponse(
            content=self.content,
            latency_ms=25,
            usage={"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
        )


def _single_sample_dataset(path: Path) -> Path:
    value = {
        "dataset_id": "real_code_test_v1",
        "title": "test",
        "prompt_name": "code_change_generator",
        "scope": "test",
        "samples": [
            {
                "sample_id": "real_test_null_guard",
                "title": "null guard",
                "requirement_text": "为 RuntimeRunSettings.FromArgs 增加 args 空值保护。",
                "target_files": ["game-unity/Assets/Scripts/RuntimeRunSettings.cs"],
                "semantic_checks": [
                    {"check_id": "null", "description": "null", "patterns": ["args\\s*==\\s*null"]},
                    {"check_id": "exception", "description": "exception", "patterns": ["ArgumentNullException"]},
                ],
            }
        ],
    }
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _payload() -> str:
    return json.dumps(
        {
            "summary": "args null guard",
            "assumptions": ["preserve non-null behavior"],
            "target_files": ["game-unity/Assets/Scripts/RuntimeRunSettings.cs"],
            "diff": SAFE_PATCH.read_text(encoding="utf-8"),
        }
    )


def test_real_dataset_has_five_unique_bounded_samples():
    dataset = load_real_code_dataset(REPOSITORY_ROOT)

    assert dataset["dataset_id"] == "real_code_generation_v1"
    assert len(dataset["samples"]) == 5
    assert len({sample["sample_id"] for sample in dataset["samples"]}) == 5
    assert all(len(sample["target_files"]) <= 3 for sample in dataset["samples"])


def test_missing_provider_configuration_exports_blocked_report(tmp_path: Path):
    def missing(_timeout: int):
        raise ValueError("Missing required environment variables: GAMECONFIG_LLM_API_KEY")

    result = run_real_code_evaluation(
        REPOSITORY_ROOT,
        tmp_path,
        provider_factory=missing,
    )

    assert result["run_status"] == "blocked"
    assert result["metrics"]["provider_call_success_rate"] is None
    assert result["configuration_error"]["stage"] == "provider_configuration"
    assert result["metrics"]["repository_unchanged"] is True
    assert (tmp_path / "real_code_evaluation.json").is_file()
    assert (tmp_path / "badcases.md").is_file()


def test_fake_real_provider_passes_static_semantic_evaluation(tmp_path: Path):
    dataset = _single_sample_dataset(tmp_path / "dataset.json")
    output = tmp_path / "output"

    result = run_real_code_evaluation(
        REPOSITORY_ROOT,
        output,
        dataset_path=dataset,
        provider_factory=lambda _timeout: FakeProvider(_payload()),
    )

    assert result["run_status"] == "completed"
    assert result["model"] == "fake-real-code-model"
    assert result["metrics"]["candidate_ready_rate"] == 1
    assert result["metrics"]["semantic_intent_pass_rate"] == 1
    assert result["metrics"]["semantic_requirement_pass_rate"] == 1
    assert result["metrics"]["usage"]["total_tokens"] == 100
    assert result["metrics"]["repository_unchanged"] is True
    assert result["samples"][0]["proposal_status"] == "generated"


def test_malformed_real_output_is_badcase_not_crash(tmp_path: Path):
    dataset = _single_sample_dataset(tmp_path / "dataset.json")
    result = run_real_code_evaluation(
        REPOSITORY_ROOT,
        tmp_path / "output",
        dataset_path=dataset,
        provider_factory=lambda _timeout: FakeProvider("{bad json"),
    )

    assert result["run_status"] == "completed"
    assert result["metrics"]["provider_call_success_rate"] == 1
    assert result["metrics"]["json_parse_success_rate"] == 0
    assert result["metrics"]["badcase_count"] == 1
    assert result["badcases"][0]["stage"] == "provider_or_json_parse"
    assert result["badcases"][0]["provider_evidence"]["latency_ms"] == 25


def test_saved_real_output_can_be_replayed_without_provider_call(tmp_path: Path):
    dataset = _single_sample_dataset(tmp_path / "dataset.json")
    output = tmp_path / "output"
    run_real_code_evaluation(
        REPOSITORY_ROOT,
        output,
        dataset_path=dataset,
        provider_factory=lambda _timeout: FakeProvider(_payload()),
    )

    replayed = replay_real_code_evaluation(
        REPOSITORY_ROOT,
        output,
        dataset_path=dataset,
    )

    assert replayed["run_status"] == "completed"
    assert replayed["replayed_at"]
    assert replayed["metrics"]["semantic_intent_pass_rate"] == 1
    assert replayed["metrics"]["candidate_ready_rate"] == 1


def test_api_exposes_real_dataset_config_and_blocked_report(tmp_path: Path):
    def missing(_timeout: int):
        raise ValueError("missing test provider")

    client = TestClient(
        create_unified_app(
            real_code_evaluation_dir=tmp_path,
            real_code_provider_factory=missing,
        )
    )

    config = client.get("/api/code-change-agent/real-evaluation/config")
    dataset = client.get("/api/code-change-agent/real-evaluation/dataset")
    result = client.post(
        "/api/code-change-agent/real-evaluation",
        json={"timeout_seconds": 20},
    )

    assert config.status_code == 200
    assert config.json()["configured"] is True
    assert dataset.json()["sample_count"] == 5
    assert result.status_code == 200
    assert result.json()["run_status"] == "blocked"
    latest = client.get("/api/code-change-agent/real-evaluation/latest")
    assert latest.status_code == 200
    assert latest.json()["run_status"] == "blocked"
    replay = client.post("/api/code-change-agent/real-evaluation/replay")
    assert replay.status_code == 409


def test_cli_missing_configuration_returns_nonzero_and_artifacts(tmp_path: Path, monkeypatch):
    def missing_provider(**_kwargs):
        raise ValueError("Missing required environment variables: GAMECONFIG_LLM_API_KEY")

    monkeypatch.setattr(real_code_evaluation_module, "OpenAICompatibleProvider", missing_provider)

    exit_code = main(["run_real_code_evaluation", "--output", str(tmp_path)])

    assert exit_code == 2
    assert (tmp_path / "real_code_evaluation.json").is_file()
