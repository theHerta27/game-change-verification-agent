"""Small real-provider evaluation for bounded Unity C# candidate generation."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
import csv
import hashlib
import json
import re
import shutil

from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.prompts import load_prompt
from gameconfig_agent.providers import OpenAICompatibleProvider
from workflow.code_change_agent import CodeChangeAgentService
from workflow.code_patch import apply_csharp_patch, inspect_csharp_patch
from workflow.code_workflow import CodeWorkflowService


DEFAULT_DATASET = "evals/real_code_generation_v1.json"
ProviderFactory = Callable[[int], Any]


def load_real_code_dataset(
    repository_root: Path,
    dataset_path: str | Path = DEFAULT_DATASET,
) -> dict[str, Any]:
    path = Path(dataset_path)
    if not path.is_absolute():
        path = repository_root / path
    dataset = json.loads(path.read_text(encoding="utf-8-sig"))
    samples = dataset.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Real code evaluation dataset must contain non-empty samples.")
    ids = [sample.get("sample_id") for sample in samples]
    if any(not isinstance(sample_id, str) or not sample_id for sample_id in ids):
        raise ValueError("Every real code sample must have a non-empty sample_id.")
    if len(ids) != len(set(ids)):
        raise ValueError("Real code evaluation sample_id values must be unique.")
    for sample in samples:
        if not sample.get("requirement_text") or not sample.get("target_files") or not sample.get("semantic_checks"):
            raise ValueError(f"Incomplete real code sample: {sample.get('sample_id')}")
    return dataset


def real_provider_configuration_status(repository_root: Path) -> dict[str, Any]:
    load_dotenv(repository_root / ".env")
    import os

    required = ["GAMECONFIG_LLM_BASE_URL", "GAMECONFIG_LLM_API_KEY", "GAMECONFIG_LLM_MODEL"]
    present = {name: bool(os.environ.get(name)) for name in required}
    return {
        "configured": all(present.values()),
        "variables": present,
        "missing": [name for name, value in present.items() if not value],
    }


def run_real_code_evaluation(
    repository_root: Path,
    output_dir: str | Path,
    *,
    dataset_path: str | Path = DEFAULT_DATASET,
    timeout_seconds: int = 60,
    provider_factory: ProviderFactory | None = None,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    dataset = load_real_code_dataset(repository_root, dataset_path)
    prompt_text = load_prompt(dataset["prompt_name"])
    baseline_hashes = _runtime_source_hashes(repository_root)
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        load_dotenv(repository_root / ".env")
        provider = (
            provider_factory(timeout_seconds)
            if provider_factory
            else OpenAICompatibleProvider(timeout_seconds=timeout_seconds)
        )
    except Exception as exc:  # noqa: BLE001 - configuration failures must still export evidence
        result = _blocked_result(dataset, prompt_text, started_at, exc, baseline_hashes == _runtime_source_hashes(repository_root))
        result["exported_files"] = [str(path) for path in export_real_code_evaluation(result, output_path)]
        _write_json(output_path / "real_code_evaluation.json", result)
        return result

    sample_results: list[dict[str, Any]] = []
    aggregate_badcases: list[dict[str, Any]] = []
    for sample in dataset["samples"]:
        sample_root = output_path / "sample_runs" / sample["sample_id"]
        workflows = CodeWorkflowService(
            repository_root=repository_root,
            workflows_dir=sample_root / "code_workflows",
        )
        service = CodeChangeAgentService(
            repository_root=repository_root,
            proposals_dir=sample_root / "proposals",
            code_workflows=workflows,
            provider_factory=lambda _timeout, client=provider: client,
        )
        result = service.propose(
            requirement_text=sample["requirement_text"],
            target_files=sample["target_files"],
            provider="openai_compatible",
            timeout_seconds=timeout_seconds,
        )
        evaluated = _evaluate_sample(repository_root, sample_root, sample, result)
        sample_results.append(evaluated)
        if evaluated["badcase"]:
            aggregate_badcases.append(evaluated["badcase"])

    repository_unchanged = baseline_hashes == _runtime_source_hashes(repository_root)
    metrics = _metrics(sample_results, repository_unchanged)
    result = {
        "run_status": "completed",
        "dataset_id": dataset["dataset_id"],
        "dataset_title": dataset["title"],
        "provider": "openai_compatible",
        "model": getattr(provider, "model", None),
        "prompt_name": dataset["prompt_name"],
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "dataset_sha256": _dataset_sha256(repository_root, dataset_path),
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": "静态生成、质量审查、补丁可应用性和固定语义断言；未自动审批、未编译、未启动 Unity。",
        "metrics": metrics,
        "samples": sample_results,
        "badcases": aggregate_badcases,
        "configuration_error": None,
    }
    result["exported_files"] = [str(path) for path in export_real_code_evaluation(result, output_path)]
    _write_json(output_path / "real_code_evaluation.json", result)
    return result


def replay_real_code_evaluation(
    repository_root: Path,
    output_dir: str | Path,
    *,
    dataset_path: str | Path = DEFAULT_DATASET,
) -> dict[str, Any]:
    """Re-run local evaluators against saved provider outputs without new API calls."""
    repository_root = repository_root.resolve()
    output_path = Path(output_dir).resolve()
    result_path = output_path / "real_code_evaluation.json"
    if not result_path.is_file():
        raise FileNotFoundError(f"Real code evaluation result not found: {result_path}")
    previous = _read_json(result_path)
    if previous.get("run_status") != "completed":
        raise ValueError("Only a completed real code evaluation can be replayed.")
    dataset = load_real_code_dataset(repository_root, dataset_path)
    baseline_hashes = _runtime_source_hashes(repository_root)
    samples: list[dict[str, Any]] = []
    badcases: list[dict[str, Any]] = []
    for sample in dataset["samples"]:
        sample_root = output_path / "sample_runs" / sample["sample_id"]
        proposal_paths = sorted(
            (sample_root / "proposals").glob("codegen_*/proposal_result.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not proposal_paths:
            raise FileNotFoundError(f"Proposal artifact missing for replay: {sample['sample_id']}")
        evaluated = _evaluate_sample(repository_root, sample_root, sample, _read_json(proposal_paths[0]))
        samples.append(evaluated)
        if evaluated["badcase"]:
            badcases.append(evaluated["badcase"])
    replayed = {
        **previous,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "replayed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": "基于已保存真实输出进行离线重放：静态质量、补丁可应用性和固定语义断言；未再次调用模型、未自动审批、未编译、未启动 Unity。",
        "metrics": _metrics(samples, baseline_hashes == _runtime_source_hashes(repository_root)),
        "samples": samples,
        "badcases": badcases,
    }
    replayed["exported_files"] = [str(path) for path in export_real_code_evaluation(replayed, output_path)]
    _write_json(result_path, replayed)
    return replayed


def export_real_code_evaluation(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = _write_json(output_dir / "real_code_evaluation.json", result)
    report_path = output_dir / "evaluation_report.md"
    report_path.write_text(_markdown_report(result), encoding="utf-8")
    badcases_path = output_dir / "badcases.md"
    badcases_path.write_text(_badcases_report(result), encoding="utf-8")
    csv_path = output_dir / "sample_summary.csv"
    _write_csv(csv_path, result["samples"])
    return [json_path, report_path, badcases_path, csv_path]


def _evaluate_sample(
    repository_root: Path,
    sample_root: Path,
    sample: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    badcase = proposal.get("badcase")
    proposal_dir = sample_root / "proposals" / proposal["proposal_id"]
    generation_path = proposal_dir / "code_generation.json"
    generation = _read_json(generation_path) if generation_path.is_file() else None
    raw_output = (badcase or {}).get("raw_model_output")
    provider_call_success = generation is not None or raw_output is not None
    json_parse_success = generation is not None or _is_json(raw_output)
    generation_contract_pass = generation is not None
    patch_gate = inspect_csharp_patch(generation["diff"], repository_root) if generation else None
    patch_safety_pass = bool(patch_gate and patch_gate["passed"])
    generated_paths = {
        item["new_path"] for item in (patch_gate or {}).get("parsed_diff", {}).get("files", [])
    }
    target_scope_pass = bool(
        generation
        and set(generation["target_files"]).issubset(set(sample["target_files"]))
        and generated_paths.issubset(set(sample["target_files"]))
    )
    quality_review_pass = bool(
        proposal.get("code_workflow")
        and proposal["code_workflow"].get("status") == "proposed"
    )
    semantic_intent_checks = (
        _semantic_checks_for_text(
            _baseline_source_text(repository_root, sample["target_files"])
            + "\n"
            + generation["diff"],
            sample,
        )
        if generation
        else []
    )
    semantic_intent_pass = bool(semantic_intent_checks) and all(
        check["passed"] for check in semantic_intent_checks
    )
    apply_success = False
    semantic_checks: list[dict[str, Any]] = []
    apply_error: str | None = None
    if generation_contract_pass and patch_safety_pass and target_scope_pass:
        workspace = sample_root / "semantic_workspace"
        try:
            _copy_target_sources(repository_root, workspace, sample["target_files"])
            apply_csharp_patch(generation["diff"], workspace)
            apply_success = True
            semantic_checks = _semantic_checks(workspace, sample)
        except Exception as exc:  # noqa: BLE001 - apply failures are evaluation evidence
            apply_error = str(exc)
    semantic_pass = bool(semantic_checks) and all(check["passed"] for check in semantic_checks)
    candidate_ready = quality_review_pass and apply_success and semantic_pass
    provider_evidence = (
        (generation or {}).get("provider_evidence")
        or (badcase or {}).get("provider_evidence")
        or {}
    )

    evaluation_badcase = None
    if badcase:
        evaluation_badcase = {"sample_id": sample["sample_id"], **badcase}
    elif apply_error:
        evaluation_badcase = _evaluation_badcase(sample, proposal, "patch_apply", "PatchApplyError", apply_error, generation)
    elif generation_contract_pass and not semantic_pass:
        missing = [check["check_id"] for check in semantic_checks if not check["passed"]]
        evaluation_badcase = _evaluation_badcase(
            sample,
            proposal,
            "semantic_validation",
            "SemanticRequirementFailed",
            f"Missing semantic evidence: {', '.join(missing) or 'checks unavailable'}",
            generation,
        )

    return {
        "sample_id": sample["sample_id"],
        "title": sample["title"],
        "requirement_text": sample["requirement_text"],
        "target_files": sample["target_files"],
        "proposal_id": proposal["proposal_id"],
        "proposal_status": proposal["status"],
        "model": proposal.get("model"),
        "stages": {
            "provider_call_success": provider_call_success,
            "json_parse_success": json_parse_success,
            "generation_contract_pass": generation_contract_pass,
            "patch_safety_pass": patch_safety_pass,
            "target_scope_pass": target_scope_pass,
            "quality_review_pass": quality_review_pass,
            "patch_apply_success": apply_success,
            "semantic_intent_pass": semantic_intent_pass,
            "semantic_requirement_pass": semantic_pass,
            "candidate_ready": candidate_ready,
        },
        "semantic_intent_checks": semantic_intent_checks,
        "semantic_checks": semantic_checks,
        "provider_evidence": provider_evidence,
        "badcase": evaluation_badcase,
    }


def _semantic_checks(workspace: Path, sample: dict[str, Any]) -> list[dict[str, Any]]:
    source = "\n".join(
        workspace.joinpath(*PurePosixPath(path).parts).read_text(encoding="utf-8-sig")
        for path in sample["target_files"]
    )
    return _semantic_checks_for_text(source, sample)


def _semantic_checks_for_text(source: str, sample: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for check in sample["semantic_checks"]:
        matches = [pattern for pattern in check["patterns"] if re.search(pattern, source, re.MULTILINE)]
        results.append(
            {
                "check_id": check["check_id"],
                "description": check["description"],
                "passed": bool(matches),
                "matched_patterns": matches,
            }
        )
    return results


def _baseline_source_text(repository_root: Path, targets: list[str]) -> str:
    return "\n".join(
        repository_root.joinpath(*PurePosixPath(path).parts).read_text(encoding="utf-8-sig")
        for path in targets
    )


def _copy_target_sources(repository_root: Path, workspace: Path, targets: list[str]) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    for relative in targets:
        source = repository_root.joinpath(*PurePosixPath(relative).parts)
        destination = workspace.joinpath(*PurePosixPath(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _metrics(samples: list[dict[str, Any]], repository_unchanged: bool) -> dict[str, Any]:
    count = len(samples)
    stage_names = list(samples[0]["stages"]) if samples else []
    metrics = {
        f"{name}_rate": _rate(sum(sample["stages"][name] for sample in samples), count)
        for name in stage_names
    }
    latencies = [
        sample["provider_evidence"].get("latency_ms")
        for sample in samples
        if isinstance(sample["provider_evidence"].get("latency_ms"), (int, float))
    ]
    usage: Counter[str] = Counter()
    token_estimate = 0
    for sample in samples:
        evidence = sample["provider_evidence"]
        for key, value in (evidence.get("usage") or {}).items():
            if isinstance(value, (int, float)):
                usage[key] += value
        if isinstance(evidence.get("token_estimate"), int):
            token_estimate += evidence["token_estimate"]
    failure_stages = Counter(
        sample["badcase"]["stage"] for sample in samples if sample["badcase"]
    )
    return {
        "sample_count": count,
        **metrics,
        "badcase_count": sum(bool(sample["badcase"]) for sample in samples),
        "failure_stage_distribution": dict(sorted(failure_stages.items())),
        "latency_ms": {
            "total": sum(latencies),
            "average": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "max": max(latencies) if latencies else None,
        },
        "usage": dict(usage) or None,
        "token_estimate": token_estimate or None,
        "repository_unchanged": repository_unchanged,
    }


def _blocked_result(
    dataset: dict[str, Any],
    prompt_text: str,
    started_at: str,
    exc: Exception,
    repository_unchanged: bool,
) -> dict[str, Any]:
    badcase = {
        "sample_id": "batch",
        "stage": "provider_configuration",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "raw_model_output": None,
        "provider": "openai_compatible",
        "model": None,
        "target_files": [],
        "details": None,
        "provider_evidence": None,
    }
    samples = [
        {
            "sample_id": sample["sample_id"],
            "title": sample["title"],
            "requirement_text": sample["requirement_text"],
            "target_files": sample["target_files"],
            "proposal_id": None,
            "proposal_status": "not_run",
            "model": None,
            "stages": {},
            "semantic_intent_checks": [],
            "semantic_checks": [],
            "provider_evidence": {},
            "badcase": None,
        }
        for sample in dataset["samples"]
    ]
    return {
        "run_status": "blocked",
        "dataset_id": dataset["dataset_id"],
        "dataset_title": dataset["title"],
        "provider": "openai_compatible",
        "model": None,
        "prompt_name": dataset["prompt_name"],
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "dataset_sha256": None,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": "Provider 未配置，未发生模型调用；不得将空指标解释为模型 0 分。",
        "metrics": {
            "sample_count": len(samples),
            "provider_call_success_rate": None,
            "json_parse_success_rate": None,
            "generation_contract_pass_rate": None,
            "patch_safety_pass_rate": None,
            "target_scope_pass_rate": None,
            "quality_review_pass_rate": None,
            "patch_apply_success_rate": None,
            "semantic_intent_pass_rate": None,
            "semantic_requirement_pass_rate": None,
            "candidate_ready_rate": None,
            "badcase_count": 1,
            "failure_stage_distribution": {"provider_configuration": 1},
            "latency_ms": {"total": 0, "average": None, "max": None},
            "usage": None,
            "token_estimate": None,
            "repository_unchanged": repository_unchanged,
        },
        "samples": samples,
        "badcases": [badcase],
        "configuration_error": badcase,
    }


def _evaluation_badcase(
    sample: dict[str, Any],
    proposal: dict[str, Any],
    stage: str,
    error_type: str,
    message: str,
    generation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "sample_id": sample["sample_id"],
        "stage": stage,
        "error_type": error_type,
        "error_message": message,
        "raw_model_output": json.dumps(generation, ensure_ascii=False) if generation else None,
        "provider": "openai_compatible",
        "model": proposal.get("model"),
        "target_files": sample["target_files"],
        "details": None,
        "provider_evidence": (generation or {}).get("provider_evidence"),
    }


def _is_json(raw: str | None) -> bool:
    if raw is None:
        return False
    try:
        json.loads(raw)
        return True
    except json.JSONDecodeError:
        return False


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _runtime_source_hashes(repository_root: Path) -> dict[str, str]:
    scripts = repository_root / "game-unity/Assets/Scripts"
    return {
        path.relative_to(repository_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(scripts.rglob("*.cs"))
    }


def _dataset_sha256(repository_root: Path, dataset_path: str | Path) -> str:
    path = Path(dataset_path)
    if not path.is_absolute():
        path = repository_root / path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# 真实 Provider 代码生成评测报告",
        "",
        f"- Run status：`{result['run_status']}`",
        f"- Dataset：`{result['dataset_id']}`",
        f"- Provider：`{result['provider']}`",
        f"- Model：`{result['model'] or '-'}`",
        f"- Prompt SHA256：`{result['prompt_sha256']}`",
        f"- 证据边界：{result['evidence_boundary']}",
        "",
    ]
    if result["run_status"] == "blocked":
        lines.extend(["## 阻塞原因", "", result["configuration_error"]["error_message"], ""])
        return "\n".join(lines)
    lines.extend(["## 指标", ""])
    for key, value in result["metrics"].items():
        lines.append(f"- `{key}`：{value}")
    lines.extend([
        "",
        "## 样本",
        "",
        "| sample_id | proposal_status | contract | safety | quality | apply | intent | semantic | ready |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for sample in result["samples"]:
        stages = sample["stages"]
        lines.append(
            f"| `{sample['sample_id']}` | {sample['proposal_status']} | "
            f"{stages['generation_contract_pass']} | {stages['patch_safety_pass']} | "
            f"{stages['quality_review_pass']} | {stages['patch_apply_success']} | "
            f"{stages['semantic_intent_pass']} | "
            f"{stages['semantic_requirement_pass']} | {stages['candidate_ready']} |"
        )
    return "\n".join(lines) + "\n"


def _badcases_report(result: dict[str, Any]) -> str:
    lines = ["# 真实 Provider 代码生成 Badcases", ""]
    if not result["badcases"]:
        return "\n".join(lines + ["- 无。", ""])
    for badcase in result["badcases"]:
        lines.extend([
            f"## {badcase['sample_id']}",
            f"- stage: `{badcase['stage']}`",
            f"- error_type: `{badcase['error_type']}`",
            f"- provider: `{badcase['provider']}`",
            f"- model: `{badcase['model'] or '-'}`",
            f"- error_message: {badcase['error_message']}",
            "",
            "```text",
            badcase.get("raw_model_output") or "unavailable",
            "```",
            "",
        ])
    return "\n".join(lines)


def _write_csv(path: Path, samples: list[dict[str, Any]]) -> None:
    fields = [
        "sample_id", "proposal_status", "provider_call_success", "json_parse_success",
        "generation_contract_pass", "patch_safety_pass", "target_scope_pass",
        "quality_review_pass", "patch_apply_success", "semantic_intent_pass", "semantic_requirement_pass",
        "candidate_ready", "latency_ms", "badcase_stage",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for sample in samples:
            stages = sample["stages"]
            writer.writerow({
                "sample_id": sample["sample_id"],
                "proposal_status": sample["proposal_status"],
                **{name: stages.get(name) for name in fields if name in stages},
                "latency_ms": sample["provider_evidence"].get("latency_ms"),
                "badcase_stage": (sample["badcase"] or {}).get("stage"),
            })


def _write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))
