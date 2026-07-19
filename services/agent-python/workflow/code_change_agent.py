"""Bounded candidate-diff generation that feeds the existing C# review workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
import difflib
import hashlib
import json
import re
import uuid

from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.prompts import load_prompt
from gameconfig_agent.providers import OpenAICompatibleProvider
from workflow.code_patch import inspect_csharp_patch
from workflow.code_workflow import CodeWorkflowService


ProviderFactory = Callable[[int], Any]
MAX_TARGET_FILES = 3
MAX_SOURCE_CONTEXT_CHARS = 60_000
MOCK_TARGET = "game-unity/Assets/Scripts/RuntimeRunSettings.cs"


class CodeChangeAgentService:
    def __init__(
        self,
        *,
        repository_root: Path,
        proposals_dir: Path,
        code_workflows: CodeWorkflowService,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.proposals_dir = proposals_dir
        self.code_workflows = code_workflows
        self.provider_factory = provider_factory or self._provider_factory

    def capabilities(self) -> dict[str, Any]:
        return {
            "max_target_files": MAX_TARGET_FILES,
            "allowed_target_files": self.allowed_target_files(),
            "mock_recipes": [
                {
                    "recipe_id": "runtime_args_null_guard",
                    "title": "运行参数空值保护",
                    "target_files": [MOCK_TARGET],
                    "requirement_example": "为 RuntimeRunSettings.FromArgs 增加 args 空值保护，不改变现有玩法。",
                    "boundary": "确定性 Mock recipe，不代表模型理解任意 C# 需求。",
                }
            ],
        }

    def allowed_target_files(self) -> list[str]:
        scripts_root = self.repository_root / "game-unity" / "Assets" / "Scripts"
        return sorted(
            path.relative_to(self.repository_root).as_posix()
            for path in scripts_root.rglob("*.cs")
            if path.is_file()
        )

    def propose(
        self,
        *,
        requirement_text: str,
        target_files: list[str],
        provider: str = "mock",
        timeout_seconds: int = 60,
    ) -> dict[str, Any]:
        requirement_text = requirement_text.strip()
        if not requirement_text:
            raise ValueError("requirement_text must not be blank.")
        if provider not in {"mock", "openai_compatible"}:
            raise ValueError(f"Unsupported provider: {provider}")

        proposal_id = _new_proposal_id()
        proposal_dir = self.proposals_dir / proposal_id
        proposal_dir.mkdir(parents=True, exist_ok=False)
        (proposal_dir / "requirement.txt").write_text(requirement_text, encoding="utf-8")
        gate = self._feasibility_gate(requirement_text, target_files, provider)
        result: dict[str, Any] = {
            "proposal_id": proposal_id,
            "status": gate["decision"],
            "provider": provider,
            "model": None,
            "requirement_text": requirement_text,
            "target_files": gate["target_files"],
            "feasibility_gate": gate,
            "generation": None,
            "code_workflow": None,
            "badcase": None,
            "created_at": _utc_now(),
        }
        _write_json(proposal_dir / "feasibility_gate.json", gate)
        if gate["decision"] != "accepted":
            self._write_result(proposal_dir, result)
            return result

        raw_output: str | None = None
        model: str | None = None
        provider_evidence: dict[str, Any] | None = None
        try:
            sources = self._load_sources(gate["target_files"])
            if provider == "mock":
                generation = self._mock_generation(requirement_text, sources)
                model = "deterministic-code-recipe-v1"
                provider_evidence = {"latency_ms": 0, "usage": None, "token_estimate": None}
            else:
                load_dotenv(self.repository_root / ".env")
                client = self.provider_factory(timeout_seconds)
                response = client.complete_json(
                    prompt_name="code_change_generator",
                    system_prompt=load_prompt("code_change_generator"),
                    user_prompt=_build_user_prompt(requirement_text, sources),
                )
                raw_output = response.content
                model = getattr(client, "model", None)
                provider_evidence = {
                    "latency_ms": response.latency_ms,
                    "usage": response.usage,
                    "token_estimate": response.token_estimate,
                }
                generation = _parse_generation(response.content, gate["target_files"])

            raw_output = raw_output or json.dumps(generation, ensure_ascii=False)
            generation["source_hashes"] = {
                path: hashlib.sha256(text.encode("utf-8")).hexdigest()
                for path, text in sources.items()
            }
            generation["provider_evidence"] = provider_evidence
            _write_json(proposal_dir / "code_generation.json", generation)
            (proposal_dir / "candidate.patch").write_text(generation["diff"], encoding="utf-8")
            patch_gate = inspect_csharp_patch(generation["diff"], self.repository_root)
            if not patch_gate["passed"]:
                raise CandidateGenerationError(
                    "Generated patch failed Patch Safety Gate.",
                    stage="patch_safety_gate",
                    details=patch_gate["errors"],
                )
            generated_paths = {
                file["new_path"] for file in patch_gate["parsed_diff"]["files"]
            }
            if not generated_paths.issubset(set(gate["target_files"])):
                raise CandidateGenerationError(
                    "Generated patch modified a file outside the selected targets.",
                    stage="target_scope_validation",
                    details=sorted(generated_paths),
                )

            code_workflow = self.code_workflows.create(
                title=generation["summary"],
                change_reason=requirement_text,
                diff_text=generation["diff"],
                provider="mock",
                timeout_seconds=timeout_seconds,
                source="code_change_agent",
                generation_evidence={
                    "proposal_id": proposal_id,
                    "provider": provider,
                    "model": model,
                    **generation,
                },
            )
            result["status"] = "generated" if code_workflow["status"] == "proposed" else "rejected"
            result["model"] = model
            result["generation"] = generation
            result["code_workflow"] = code_workflow
            if code_workflow["status"] != "proposed":
                result["badcase"] = _badcase(
                    proposal_id,
                    "quality_review",
                    "CandidateRejected",
                    "Generated patch did not pass the existing C# quality workflow.",
                    raw_output,
                    provider,
                    model,
                    gate["target_files"],
                    provider_evidence=provider_evidence,
                )
                _write_badcase_markdown(proposal_dir / "badcase.md", result["badcase"])
        except Exception as exc:  # noqa: BLE001 - provider and contract failures become artifacts
            stage = exc.stage if isinstance(exc, CandidateGenerationError) else "provider_or_json_parse"
            result["status"] = "failed"
            result["model"] = model
            result["badcase"] = _badcase(
                proposal_id,
                stage,
                type(exc).__name__,
                str(exc),
                raw_output,
                provider,
                model,
                gate["target_files"],
                details=exc.details if isinstance(exc, CandidateGenerationError) else None,
                provider_evidence=provider_evidence,
            )
            _write_badcase_markdown(proposal_dir / "badcase.md", result["badcase"])

        self._write_result(proposal_dir, result)
        return result

    def get(self, proposal_id: str) -> dict[str, Any]:
        if not proposal_id.startswith("codegen_") or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for char in proposal_id
        ):
            raise KeyError("Invalid code generation proposal id.")
        path = self.proposals_dir / proposal_id / "proposal_result.json"
        if not path.is_file():
            raise KeyError(f"Unknown code generation proposal: {proposal_id}")
        result = _read_json(path)
        if result.get("code_workflow"):
            result["code_workflow"] = self.code_workflows.get(
                result["code_workflow"]["workflow_id"]
            )
        return result

    def _feasibility_gate(
        self,
        requirement_text: str,
        target_files: list[str],
        provider: str,
    ) -> dict[str, Any]:
        normalized = list(dict.fromkeys(path.replace("\\", "/").strip() for path in target_files if path.strip()))
        allowed = set(self.allowed_target_files())
        errors: list[str] = []
        if not normalized:
            errors.append("请至少选择一个运行时 C# 目标文件。")
        if len(normalized) > MAX_TARGET_FILES:
            errors.append(f"目标文件不能超过 {MAX_TARGET_FILES} 个。")
        outside = [path for path in normalized if path not in allowed]
        if outside:
            errors.append(f"目标文件不在允许范围：{', '.join(outside)}")
        off_topic = bool(re.search(r"笑话|诗歌|精美角色|画一张|天气|新闻", requirement_text, re.IGNORECASE))
        if off_topic:
            return {
                "decision": "rejected",
                "reason": "需求不属于 Unity C# 代码变更。",
                "target_files": normalized,
                "errors": errors,
                "mock_recipe_id": None,
            }
        if errors:
            return {
                "decision": "rejected",
                "reason": "目标文件范围不满足受控生成要求。",
                "target_files": normalized,
                "errors": errors,
                "mock_recipe_id": None,
            }
        if provider == "mock" and not _matches_mock_recipe(requirement_text, normalized):
            return {
                "decision": "needs_clarification",
                "reason": "确定性 Mock 只支持 RuntimeRunSettings.FromArgs 的 args 空值保护 recipe。请使用推荐需求，或切换真实 Provider。",
                "target_files": normalized,
                "errors": [],
                "mock_recipe_id": None,
            }
        return {
            "decision": "accepted",
            "reason": "需求和目标文件已进入受控候选生成范围。",
            "target_files": normalized,
            "errors": [],
            "mock_recipe_id": "runtime_args_null_guard" if provider == "mock" else None,
        }

    def _load_sources(self, target_files: list[str]) -> dict[str, str]:
        sources: dict[str, str] = {}
        total = 0
        for relative in target_files:
            path = self.repository_root.joinpath(*PurePosixPath(relative).parts)
            text = path.read_text(encoding="utf-8-sig")
            total += len(text)
            if total > MAX_SOURCE_CONTEXT_CHARS:
                raise CandidateGenerationError(
                    f"Selected source context exceeds {MAX_SOURCE_CONTEXT_CHARS} characters.",
                    stage="source_context",
                )
            sources[relative] = text
        return sources

    def _mock_generation(self, requirement_text: str, sources: dict[str, str]) -> dict[str, Any]:
        source = sources[MOCK_TARGET]
        guard = "            if (args == null)\n                throw new ArgumentNullException(nameof(args));"
        if guard in source:
            raise CandidateGenerationError("Null guard already exists in the selected baseline.", stage="mock_recipe")
        marker = "        {\n            RuntimeRunSettings settings = new()"
        if marker not in source:
            raise CandidateGenerationError("Mock recipe source marker no longer matches the baseline.", stage="mock_recipe")
        updated = source.replace("        {\n            RuntimeRunSettings settings = new()", f"        {{\n{guard}\n            RuntimeRunSettings settings = new()", 1)
        body = "\n".join(
            difflib.unified_diff(
                source.splitlines(),
                updated.splitlines(),
                fromfile=f"a/{MOCK_TARGET}",
                tofile=f"b/{MOCK_TARGET}",
                lineterm="",
                n=3,
            )
        )
        diff = f"diff --git a/{MOCK_TARGET} b/{MOCK_TARGET}\n{body}\n"
        return {
            "summary": "为运行参数解析增加 args 空值保护",
            "assumptions": [
                "FromArgs 的现有非空参数行为保持不变。",
                "这是确定性 Mock recipe，不代表模型理解任意 C# 需求。",
            ],
            "target_files": [MOCK_TARGET],
            "diff": diff,
            "requirement_echo": requirement_text,
        }

    def _provider_factory(self, timeout_seconds: int) -> Any:
        return OpenAICompatibleProvider(timeout_seconds=timeout_seconds)

    def _write_result(self, proposal_dir: Path, result: dict[str, Any]) -> None:
        _write_json(proposal_dir / "proposal_result.json", result)


class CandidateGenerationError(RuntimeError):
    def __init__(self, message: str, *, stage: str, details: Any = None) -> None:
        super().__init__(message)
        self.stage = stage
        self.details = details


def _matches_mock_recipe(requirement_text: str, target_files: list[str]) -> bool:
    lowered = requirement_text.lower()
    has_null = "空值" in requirement_text or "空参数" in requirement_text or "null" in lowered or "args" in lowered
    has_guard = any(token in requirement_text for token in ("保护", "校验", "防护")) or "guard" in lowered
    return target_files == [MOCK_TARGET] and has_null and has_guard


def _parse_generation(raw: str, selected_targets: list[str]) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise CandidateGenerationError("Provider output must be one JSON object.", stage="generation_contract")
    expected = {"summary", "assumptions", "target_files", "diff"}
    if set(value) != expected:
        raise CandidateGenerationError(
            f"Provider output keys must be exactly {sorted(expected)}.",
            stage="generation_contract",
        )
    if not isinstance(value["summary"], str) or not value["summary"].strip():
        raise CandidateGenerationError("summary must be a non-empty string.", stage="generation_contract")
    if not isinstance(value["assumptions"], list) or not all(
        isinstance(item, str) and item.strip() for item in value["assumptions"]
    ):
        raise CandidateGenerationError("assumptions must be an array of non-empty strings.", stage="generation_contract")
    if not isinstance(value["target_files"], list) or not all(
        isinstance(item, str) for item in value["target_files"]
    ):
        raise CandidateGenerationError("target_files must be an array of strings.", stage="generation_contract")
    if not set(value["target_files"]).issubset(set(selected_targets)):
        raise CandidateGenerationError("Provider declared a target outside the selected files.", stage="target_scope_validation")
    if not isinstance(value["diff"], str) or not value["diff"].strip():
        raise CandidateGenerationError("diff must be a non-empty unified diff.", stage="generation_contract")
    return value


def _build_user_prompt(requirement_text: str, sources: dict[str, str]) -> str:
    payload = {
        "requirement_text": requirement_text,
        "selected_sources": [
            {"path": path, "content": content}
            for path, content in sources.items()
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _badcase(
    proposal_id: str,
    stage: str,
    error_type: str,
    error_message: str,
    raw_model_output: str | None,
    provider: str,
    model: str | None,
    target_files: list[str],
    *,
    details: Any = None,
    provider_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "stage": stage,
        "error_type": error_type,
        "error_message": error_message,
        "raw_model_output": raw_model_output,
        "provider": provider,
        "model": model,
        "target_files": target_files,
        "details": details,
        "provider_evidence": provider_evidence,
    }


def _write_badcase_markdown(path: Path, badcase: dict[str, Any]) -> None:
    lines = [
        "# Code Change Agent Badcase",
        "",
        f"- proposal_id: `{badcase['proposal_id']}`",
        f"- stage: `{badcase['stage']}`",
        f"- error_type: `{badcase['error_type']}`",
        f"- provider: `{badcase['provider']}`",
        f"- model: `{badcase['model'] or '-'}`",
        f"- error_message: {badcase['error_message']}",
        "",
        "## Raw Model Output",
        "",
        "```text",
        badcase["raw_model_output"] or "unavailable",
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _new_proposal_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"codegen_{timestamp}_{uuid.uuid4().hex[:8]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))
