import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.server import create_unified_app
from gameconfig_agent.bullet_hell import propose_mock_change, simulate_telemetry
from gameconfig_agent.providers.base import LLMResponse
from workflow.bullet_hell_workflow import BulletHellWorkflowService


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _service(tmp_path: Path, runner=None, provider_factory=None) -> BulletHellWorkflowService:
    return BulletHellWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "bullet-workflows",
        unity_executable=tmp_path / "BulletHellDemo.exe",
        telemetry_runner=runner or (lambda config, _directory, seed: simulate_telemetry(config, seed=seed)),
        provider_factory=provider_factory,
    )


def _requirement() -> str:
    return "第二阶段改为双向螺旋弹，提高密度，但同时存在的子弹不能超过350发，最低帧率不能低于55 FPS。"


def _wait(service: BulletHellWorkflowService, workflow_id: str) -> dict:
    for _ in range(100):
        value = service.get(workflow_id)
        if value["status"] in {"evidence_ready", "budget_exhausted", "blocked", "failed"}:
            return value
        time.sleep(0.01)
    raise AssertionError("workflow did not finish")


def test_create_requires_authorization_and_never_changes_baseline(tmp_path):
    service = _service(tmp_path)
    baseline_before = service.baseline_path.read_bytes()

    workflow = service.create(requirement_text=_requirement())

    assert workflow["status"] == "awaiting_authorization"
    assert workflow["static_validation"]["passed"]
    assert workflow["config_diff"]
    assert workflow["structured_goal"]["target_phase_id"] == "phase_2"
    assert service.latest()["workflow_id"] == workflow["workflow_id"]
    with pytest.raises(ValueError, match="cannot run"):
        service.start(workflow["workflow_id"])
    assert service.baseline_path.read_bytes() == baseline_before


def test_authorized_workflow_runs_paired_evidence_and_can_be_accepted(tmp_path):
    service = _service(tmp_path)
    created = service.create(requirement_text=_requirement())
    workflow_id = created["workflow_id"]

    service.authorize(workflow_id, actor="designer", note="允许最多三轮隔离测试")
    service.start(workflow_id)
    completed = _wait(service, workflow_id)
    accepted = service.decide(
        workflow_id,
        decision="accept",
        actor="designer",
        note="固定轨迹证据达到当前目标",
    )

    assert completed["status"] == "evidence_ready"
    assert completed["baseline_telemetry"]
    assert completed["candidate_telemetry"]
    assert completed["comparison_report"]["passed"]
    assert [run["agent_name"] for run in completed["agent_runs"]] == [
        "requirement_agent",
        "quality_review_agent",
    ]
    assert completed["quality_reviews"][0]["policy_gate"]["effective_decision"] == "accept"
    assert completed["budget"]["model_calls_used"] == 0
    assert accepted["status"] == "accepted"
    assert accepted["final_decision"]["baseline_overwritten"] is False


def test_failed_first_candidate_uses_bounded_repair(tmp_path):
    calls = {"candidate": 0}

    def runner(config, directory, seed):
        telemetry = simulate_telemetry(config, seed=seed)
        if directory.name.startswith("candidate"):
            calls["candidate"] += 1
            if calls["candidate"] == 1:
                telemetry["peak_alive_bullets"] = 420
        return telemetry

    service = _service(tmp_path, runner)
    created = service.create(requirement_text=_requirement())
    service.authorize(created["workflow_id"], actor="designer")
    service.start(created["workflow_id"])
    completed = _wait(service, created["workflow_id"])

    assert completed["status"] == "evidence_ready"
    assert completed["budget"]["unity_runs_used"] == 2
    assert completed["repair_history"][0]["action"] == "REDUCE_BULLETS_PER_WAVE"
    assert completed["candidate_history"][-1]["evaluation"]["passed"]


def test_dangerous_request_is_blocked_without_runner(tmp_path):
    called = False

    def runner(_config, _directory, _seed):
        nonlocal called
        called = True
        return {}

    service = _service(tmp_path, runner)
    workflow = service.create(requirement_text="每0.02秒发射200颗高速弹，越密越好。")

    assert workflow["status"] == "blocked"
    assert not called
    with pytest.raises(ValueError, match="cannot be authorized"):
        service.authorize(workflow["workflow_id"], actor="designer")


def test_api_exposes_bullet_hell_workflow(tmp_path):
    service = _service(tmp_path)
    client = TestClient(create_unified_app(bullet_hell_workflow_service=service))

    capabilities = client.get("/api/bullet-hell/capabilities")
    created = client.post(
        "/api/bullet-hell/workflows",
        json={"requirement_text": _requirement(), "provider": "mock"},
    )

    assert capabilities.status_code == 200
    assert capabilities.json()["patterns"] == ["ring", "aimed_fan", "spiral", "petal"]
    assert created.status_code == 200
    workflow_id = created.json()["workflow_id"]
    blocked = client.post(f"/api/bullet-hell/workflows/{workflow_id}/run")
    assert blocked.status_code == 409
    authorized = client.post(
        f"/api/bullet-hell/workflows/{workflow_id}/authorize",
        json={"actor": "designer", "note": "隔离运行"},
    )
    assert authorized.status_code == 200


def test_gameplay_failure_exit_code_keeps_valid_telemetry(tmp_path, monkeypatch):
    executable = tmp_path / "BulletHellDemo.exe"
    executable.write_bytes(b"placeholder")
    service = BulletHellWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "workflows",
        unity_executable=executable,
    )

    def fake_run(command, **_kwargs):
        telemetry_path = Path(command[command.index("--telemetry-output") + 1])
        telemetry_path.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "random_seed": 20260727,
                    "player_hits": 5,
                    "phase_results": [],
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr("workflow.engines.unity.subprocess.run", fake_run)
    baseline = json.loads(
        (REPOSITORY_ROOT / "configs" / "bullet-hell" / "baseline.json").read_text(encoding="utf-8")
    )
    telemetry = service._run_unity(baseline, tmp_path / "run", 20260727)

    assert telemetry["status"] == "failed"
    assert telemetry["player_hits"] == 5


def test_visual_comparison_uses_fixed_variants_and_strict_artifacts(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.unity_executable.write_bytes(b"placeholder")
    created = service.create(requirement_text=_requirement())
    service.authorize(created["workflow_id"], actor="designer")
    service.start(created["workflow_id"])
    completed = _wait(service, created["workflow_id"])
    assert completed["status"] == "evidence_ready"

    def fake_capture(config_path, output_dir, variant, seed, **_kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        captures = []
        for second in (10, 20, 30):
            filename = f"capture_{second:02d}s.png"
            (output_dir / filename).write_bytes(f"{variant}-{second}".encode())
            captures.append(
                {
                    "time_seconds": second,
                    "phase_id": "phase_2",
                    "phase_name": "Spiral",
                    "pattern_type": "spiral",
                    "file_name": filename,
                }
            )
        return {
            "variant": variant,
            "duration_seconds": 36,
            "random_seed": seed,
            "run_mode": "auto",
            "fixed_trajectory": True,
            "captures": captures,
            "telemetry_file": f"visual-comparison/{variant}/telemetry.json",
            "player_exit_code": 0,
        }

    monkeypatch.setattr(service, "_run_visual_capture", fake_capture)
    service.generate_visual_comparison(created["workflow_id"])
    for _ in range(100):
        visual = service.get(created["workflow_id"])["visual_comparison"]
        if visual and visual["status"] != "running":
            break
        time.sleep(0.01)

    assert visual["status"] == "completed"
    assert visual["random_seed"] == 20260727
    assert visual["fixed_trajectory"] is True
    assert visual["capture_times_seconds"] == [10, 20, 30]
    assert visual["variants"]["baseline"]["config_sha256"] != visual["variants"]["candidate"]["config_sha256"]
    image = service.visual_artifact(created["workflow_id"], "baseline", "capture_20s.png")
    assert image.read_bytes() == b"baseline-20"
    client = TestClient(create_unified_app(bullet_hell_workflow_service=service))
    image_response = client.get(
        f"/api/bullet-hell/workflows/{created['workflow_id']}/visuals/baseline/capture_20s.png"
    )
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    invalid_variant = client.post(
        f"/api/bullet-hell/workflows/{created['workflow_id']}/play/arbitrary"
    )
    assert invalid_variant.status_code == 409
    with pytest.raises(ValueError, match="Unsupported visual"):
        service.visual_artifact(created["workflow_id"], "..", "capture_20s.png")
    with pytest.raises(ValueError, match="Unsupported visual artifact"):
        service.visual_artifact(created["workflow_id"], "baseline", "../baseline_config.json")


def test_manual_play_is_restricted_to_workflow_snapshots(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.unity_executable.write_bytes(b"placeholder")
    created = service.create(requirement_text=_requirement())
    service.authorize(created["workflow_id"], actor="designer")
    commands = []

    def fake_popen(command, **_kwargs):
        commands.append(command)
        return SimpleNamespace(pid=1234)

    monkeypatch.setattr("workflow.engines.unity.subprocess.Popen", fake_popen)
    before = service.launch_manual(created["workflow_id"], variant="baseline")
    after = service.launch_manual(created["workflow_id"], variant="candidate")

    assert before["config_artifact"] == "baseline_config.json"
    assert after["config_artifact"] == "candidate_config.json"
    assert commands[0][commands[0].index("--config-input") + 1].endswith("baseline_config.json")
    assert commands[1][commands[1].index("--config-input") + 1].endswith("candidate_config.json")
    with pytest.raises(ValueError, match="Unsupported manual play variant"):
        service.launch_manual(created["workflow_id"], variant="../../arbitrary.exe")


def test_real_provider_uses_distinct_requirement_and_quality_review_calls(tmp_path):
    baseline = json.loads(
        (REPOSITORY_ROOT / "configs" / "bullet-hell" / "baseline.json").read_text(encoding="utf-8")
    )
    candidate, goal, _ = propose_mock_change(baseline, _requirement())
    provider = _QueueProvider(
        {
            "bullet_hell_requirement_agent": json.dumps(
                {"structured_goal": goal, "candidate_config": candidate},
                ensure_ascii=False,
            ),
            "bullet_hell_quality_review_agent": json.dumps(
                {
                    "decision": "accept",
                    "repair_action": None,
                    "reason": "所有确定性运行检查均已通过。",
                    "evidence_refs": ["comparison_report.json.evaluation.checks"],
                },
                ensure_ascii=False,
            ),
        }
    )
    service = _service(tmp_path, provider_factory=lambda _timeout: provider)

    created = service.create(
        requirement_text=_requirement(),
        provider="openai_compatible",
    )
    service.authorize(created["workflow_id"], actor="designer")
    service.start(created["workflow_id"])
    completed = _wait(service, created["workflow_id"])

    assert completed["status"] == "evidence_ready"
    assert provider.calls == [
        "bullet_hell_requirement_agent",
        "bullet_hell_quality_review_agent",
    ]
    assert completed["budget"]["model_calls_used"] == 2
    assert [run["agent_name"] for run in completed["agent_runs"]] == [
        "requirement_agent",
        "quality_review_agent",
    ]
    assert all(run["provider"] == "openai_compatible" for run in completed["agent_runs"])


def test_malformed_quality_review_is_blocked_and_recorded_as_badcase(tmp_path):
    baseline = json.loads(
        (REPOSITORY_ROOT / "configs" / "bullet-hell" / "baseline.json").read_text(encoding="utf-8")
    )
    candidate, goal, _ = propose_mock_change(baseline, _requirement())
    provider = _QueueProvider(
        {
            "bullet_hell_requirement_agent": json.dumps(
                {"structured_goal": goal, "candidate_config": candidate},
                ensure_ascii=False,
            ),
            "bullet_hell_quality_review_agent": "{not valid json",
        }
    )
    service = _service(tmp_path, provider_factory=lambda _timeout: provider)

    created = service.create(
        requirement_text=_requirement(),
        provider="openai_compatible",
    )
    service.authorize(created["workflow_id"], actor="designer")
    service.start(created["workflow_id"])
    completed = _wait(service, created["workflow_id"])

    assert completed["status"] == "blocked"
    assert completed["error"]["stage"] == "quality_review_agent"
    assert completed["badcases"][0]["raw_model_output"] == "{not valid json"
    assert completed["budget"]["model_calls_used"] == 2
    assert completed["agent_runs"][-1]["status"] == "failed"


class _QueueProvider:
    model = "test-model"

    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def complete_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str) -> LLMResponse:
        assert system_prompt
        assert user_prompt
        self.calls.append(prompt_name)
        return LLMResponse(
            content=self.responses[prompt_name],
            latency_ms=7,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
