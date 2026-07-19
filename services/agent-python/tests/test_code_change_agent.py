import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.server import create_unified_app
from gameconfig_agent.providers.base import LLMResponse
from workflow.code_change_agent import CodeChangeAgentService, MOCK_TARGET
from workflow.code_workflow import CodeWorkflowService


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAFE_PATCH = REPOSITORY_ROOT / "examples" / "csharp" / "runtime_args_null_guard.patch"
UNSAFE_PATCH = REPOSITORY_ROOT / "examples" / "csharp" / "unsafe_process_launch.patch"


class FakeProvider:
    model = "fake-code-model"

    def __init__(self, content: str) -> None:
        self.content = content

    def complete_json(self, **_kwargs) -> LLMResponse:
        return LLMResponse(content=self.content, latency_ms=12, usage={"total_tokens": 100})


def _service(tmp_path: Path, provider_content: str | None = None) -> CodeChangeAgentService:
    code_workflows = CodeWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "code_workflows",
    )
    return CodeChangeAgentService(
        repository_root=REPOSITORY_ROOT,
        proposals_dir=tmp_path / "code_generation",
        code_workflows=code_workflows,
        provider_factory=(lambda _timeout: FakeProvider(provider_content or "{}")),
    )


def _requirement() -> str:
    return "为 RuntimeRunSettings.FromArgs 增加 args 空值保护，不改变现有玩法。"


def _provider_payload(patch: Path = SAFE_PATCH) -> str:
    return json.dumps(
        {
            "summary": "为运行参数解析增加空值保护",
            "assumptions": ["现有非空参数行为保持不变"],
            "target_files": [MOCK_TARGET],
            "diff": patch.read_text(encoding="utf-8"),
        },
        ensure_ascii=False,
    )


def test_capabilities_expose_bounded_runtime_files_and_mock_recipe(tmp_path: Path):
    capabilities = _service(tmp_path).capabilities()

    assert MOCK_TARGET in capabilities["allowed_target_files"]
    assert capabilities["max_target_files"] == 3
    assert capabilities["mock_recipes"][0]["recipe_id"] == "runtime_args_null_guard"


def test_deterministic_mock_generates_candidate_then_reuses_code_workflow(tmp_path: Path):
    service = _service(tmp_path)

    result = service.propose(
        requirement_text=_requirement(),
        target_files=[MOCK_TARGET],
        provider="mock",
    )

    assert result["status"] == "generated"
    assert result["model"] == "deterministic-code-recipe-v1"
    assert result["feasibility_gate"]["mock_recipe_id"] == "runtime_args_null_guard"
    assert result["code_workflow"]["status"] == "proposed"
    assert result["code_workflow"]["source"] == "code_change_agent"
    assert result["code_workflow"]["provider"] == "mock"
    assert "ArgumentNullException" in result["generation"]["diff"]


def test_mock_does_not_pretend_to_support_arbitrary_code_requests(tmp_path: Path):
    result = _service(tmp_path).propose(
        requirement_text="给玩家新增冲刺和无敌帧",
        target_files=[MOCK_TARGET],
        provider="mock",
    )

    assert result["status"] == "needs_clarification"
    assert result["generation"] is None
    assert "只支持" in result["feasibility_gate"]["reason"]


def test_off_topic_and_outside_target_are_rejected_before_provider(tmp_path: Path):
    service = _service(tmp_path)
    off_topic = service.propose(
        requirement_text="帮我讲一个笑话",
        target_files=[MOCK_TARGET],
        provider="openai_compatible",
    )
    outside = service.propose(
        requirement_text=_requirement(),
        target_files=["services/agent-python/api/server.py"],
        provider="openai_compatible",
    )

    assert off_topic["status"] == "rejected"
    assert outside["status"] == "rejected"
    assert outside["feasibility_gate"]["errors"]


def test_malformed_provider_json_records_badcase(tmp_path: Path):
    service = _service(tmp_path, "{bad json")

    result = service.propose(
        requirement_text=_requirement(),
        target_files=[MOCK_TARGET],
        provider="openai_compatible",
    )

    assert result["status"] == "failed"
    assert result["badcase"]["stage"] == "provider_or_json_parse"
    assert result["badcase"]["raw_model_output"] == "{bad json"
    assert result["badcase"]["provider_evidence"]["latency_ms"] == 12
    assert (
        tmp_path / "code_generation" / result["proposal_id"] / "badcase.md"
    ).is_file()


def test_provider_patch_with_dangerous_api_records_safety_badcase(tmp_path: Path):
    service = _service(tmp_path, _provider_payload(UNSAFE_PATCH))

    result = service.propose(
        requirement_text=_requirement(),
        target_files=[MOCK_TARGET],
        provider="openai_compatible",
    )

    assert result["status"] == "failed"
    assert result["badcase"]["stage"] == "patch_safety_gate"
    assert "process_launch" in {
        item["rule_id"] for item in result["badcase"]["details"]
    }


def test_valid_real_provider_candidate_enters_deterministic_review(tmp_path: Path):
    service = _service(tmp_path, _provider_payload())

    result = service.propose(
        requirement_text=_requirement(),
        target_files=[MOCK_TARGET],
        provider="openai_compatible",
    )

    assert result["status"] == "generated"
    assert result["model"] == "fake-code-model"
    assert result["generation"]["provider_evidence"]["usage"]["total_tokens"] == 100
    assert result["code_workflow"]["status"] == "proposed"


def test_code_change_agent_api_exposes_capabilities_and_mock_proposal(tmp_path: Path):
    service = _service(tmp_path)
    client = TestClient(create_unified_app(code_change_agent_service=service))

    capabilities = client.get("/api/code-change-agent/capabilities")
    proposal = client.post(
        "/api/code-change-agent/proposals",
        json={
            "requirement_text": _requirement(),
            "target_files": [MOCK_TARGET],
            "provider": "mock",
        },
    )

    assert capabilities.status_code == 200
    assert MOCK_TARGET in capabilities.json()["allowed_target_files"]
    assert proposal.status_code == 200
    assert proposal.json()["status"] == "generated"
    loaded = client.get(
        f"/api/code-change-agent/proposals/{proposal.json()['proposal_id']}"
    )
    assert loaded.status_code == 200
    assert loaded.json()["code_workflow"]["status"] == "proposed"
