"""Phase 2 real-run pipeline with provider abstraction and badcase capture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gameconfig_agent.agents.test_scenario import TestScenarioAgent
from gameconfig_agent.data.design_reference import BALANCE_POLICY_LOOKUP
from gameconfig_agent.data.evaluation_dataset import EVALUATION_DATASET
from gameconfig_agent.data.real_run_evaluation import REAL_RUN_EVALUATION_REQUIREMENTS
from gameconfig_agent.prompts import load_prompt
from gameconfig_agent.providers import LLMProvider, MockLLMProvider, OpenAICompatibleProvider
from gameconfig_agent.tools.evaluator import EvaluationTool
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool
from gameconfig_agent.tools.rule_engine import RuleEngineTool
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


def make_provider(provider_name: str) -> LLMProvider:
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name == "openai_compatible":
        return OpenAICompatibleProvider()
    raise ValueError(f"Unsupported provider: {provider_name}")


def failed_evaluation_result(provider_name: str, error: Exception, primary_requirement: str) -> dict:
    badcase = {
        "sample_id": "real_demo_input",
        "stage": "provider_initialization",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "raw_model_output": None,
        "provider": provider_name,
        "model": None,
    }
    result = {
        "sample_id": "real_demo_input",
        "requirement_text": primary_requirement,
        "provider": provider_name,
        "structured_requirement": {},
        "assumptions": [],
        "draft_configs": {},
        "draft_validation": {"schema_passed": False, "schema_errors": [], "reference_errors": [], "rule_errors": []},
        "review_findings": [],
        "repaired_configs": {},
        "repair_actions": [],
        "final_validation": {"passed": False, "schema_errors": [], "reference_errors": [], "rule_errors": []},
        "test_scenarios": [],
        "evaluation": EvaluationTool().evaluate([], EVALUATION_DATASET),
        "badcases": [badcase],
        "trace": [
            {
                "sample_id": "real_demo_input",
                "actor": provider_name,
                "action": "provider_initialization",
                "json_parse_success": False,
                "latency_ms": None,
            }
        ],
        "provider_metrics": [],
    }
    return {"provider": provider_name, "results": [result], "metrics": aggregate_metrics([result])}


class RealRunPipeline:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.schema_tool = SchemaValidatorTool()
        self.reference_tool = ReferenceCheckerTool()
        self.rule_tool = RuleEngineTool()
        self.evaluator = EvaluationTool()

    def run(self, requirement_text: str, *, sample_id: str = "input") -> dict[str, Any]:
        trace: list[dict] = []
        badcases: list[dict] = []
        provider_metrics: list[dict] = []

        generator_payload = self._call_json(
            "generator",
            requirement_text,
            trace,
            badcases,
            provider_metrics,
            sample_id=sample_id,
        )
        if generator_payload is None:
            return self._failed_result(sample_id, requirement_text, trace, badcases, provider_metrics)

        structured_requirement = generator_payload.get("structured_requirement", {})
        draft_configs = generator_payload.get("draft_configs", {})
        assumptions = generator_payload.get("assumptions", [])

        schema_errors = self.schema_tool.validate(structured_requirement, draft_configs)
        if schema_errors:
            badcases.append(
                {
                    "sample_id": sample_id,
                    "stage": "generator_schema_validation",
                    "reason": "schema validation failed",
                    "error_type": "SchemaValidationError",
                    "error_message": f"{len(schema_errors)} schema errors",
                    "raw_model_output": generator_payload,
                    "provider": self.provider.name,
                    "model": getattr(self.provider, "model", None),
                    "errors": schema_errors,
                }
            )
        reference_errors = self.reference_tool.check(draft_configs) if not schema_errors else []
        rule_result = self.rule_tool.evaluate(structured_requirement, draft_configs) if not schema_errors else {"violations": []}
        validation_errors = schema_errors + reference_errors + rule_result["violations"]

        reviewer_payload = self._call_json(
            "reviewer",
            json.dumps(
                {
                    "requirement_text": requirement_text,
                    "structured_requirement": structured_requirement,
                    "draft_configs": draft_configs,
                    "validation_errors": validation_errors,
                    "design_reference": BALANCE_POLICY_LOOKUP,
                },
                ensure_ascii=False,
            ),
            trace,
            badcases,
            provider_metrics,
            sample_id=sample_id,
        ) or {"review_findings": []}

        repairer_payload = self._call_json(
            "repairer",
            json.dumps(
                {
                    "structured_requirement": structured_requirement,
                    "draft_configs": draft_configs,
                    "validation_errors": validation_errors,
                    "review_findings": reviewer_payload.get("review_findings", []),
                    "design_reference": BALANCE_POLICY_LOOKUP,
                },
                ensure_ascii=False,
            ),
            trace,
            badcases,
            provider_metrics,
            sample_id=sample_id,
        )

        repaired_configs = {}
        repair_actions = []
        if repairer_payload is not None:
            repaired_configs = repairer_payload.get("repaired_configs", {})
            repair_actions = repairer_payload.get("repair_actions", [])
        else:
            badcases.append(
                {
                    "sample_id": sample_id,
                    "stage": "repairer",
                    "reason": "repairer JSON unavailable",
                    "error_type": "MissingPayload",
                    "error_message": "Repairer did not return usable JSON payload.",
                    "raw_model_output": None,
                    "provider": self.provider.name,
                    "model": getattr(self.provider, "model", None),
                }
            )

        final_schema_errors = self.schema_tool.validate(structured_requirement, repaired_configs) if repaired_configs else [
            {"source": "RealRunPipeline", "code": "missing_repaired_configs", "path": "repaired_configs", "message": "No repaired configs returned."}
        ]
        final_reference_errors = self.reference_tool.check(repaired_configs) if not final_schema_errors else []
        final_rule_errors = (
            self.rule_tool.evaluate(structured_requirement, repaired_configs)["violations"] if not final_schema_errors else []
        )
        final_errors = final_schema_errors + final_reference_errors + final_rule_errors
        if final_schema_errors:
            badcases.append(
                {
                    "sample_id": sample_id,
                    "stage": "final_schema_validation",
                    "reason": "schema validation failed",
                    "error_type": "SchemaValidationError",
                    "error_message": f"{len(final_schema_errors)} schema errors",
                    "raw_model_output": repaired_configs,
                    "provider": self.provider.name,
                    "model": getattr(self.provider, "model", None),
                    "errors": final_schema_errors,
                }
            )

        test_scenario_payload = self._call_json(
            "test_scenario",
            json.dumps(
                {
                    "structured_requirement": structured_requirement,
                    "final_configs": repaired_configs,
                    "evaluation_dataset": EVALUATION_DATASET,
                },
                ensure_ascii=False,
            ),
            trace,
            badcases,
            provider_metrics,
            sample_id=sample_id,
        )
        if test_scenario_payload and "test_scenarios" in test_scenario_payload:
            test_scenarios = test_scenario_payload["test_scenarios"]
        elif repaired_configs and not final_errors:
            test_scenarios = TestScenarioAgent().generate(repaired_configs)
            badcases.append(
                {
                    "sample_id": sample_id,
                    "stage": "test_scenario",
                    "reason": "provider test_scenarios unavailable; deterministic fallback used",
                    "error_type": "MissingPayload",
                    "error_message": "Provider did not return test_scenarios; deterministic fallback used.",
                    "raw_model_output": test_scenario_payload,
                    "provider": self.provider.name,
                    "model": getattr(self.provider, "model", None),
                }
            )
        else:
            test_scenarios = []

        evaluation = self.evaluator.evaluate(test_scenarios, EVALUATION_DATASET)
        return {
            "sample_id": sample_id,
            "requirement_text": requirement_text,
            "provider": self.provider.name,
            "structured_requirement": structured_requirement,
            "assumptions": assumptions,
            "draft_configs": draft_configs,
            "draft_validation": {
                "schema_passed": not schema_errors,
                "schema_errors": schema_errors,
                "reference_errors": reference_errors,
                "rule_errors": rule_result["violations"],
            },
            "review_findings": reviewer_payload.get("review_findings", []),
            "repaired_configs": repaired_configs,
            "repair_actions": repair_actions,
            "final_validation": {
                "passed": not final_errors,
                "schema_errors": final_schema_errors,
                "reference_errors": final_reference_errors,
                "rule_errors": final_rule_errors,
            },
            "test_scenarios": test_scenarios,
            "evaluation": evaluation,
            "badcases": badcases,
            "trace": trace,
            "provider_metrics": provider_metrics,
        }

    def _call_json(
        self,
        prompt_name: str,
        user_prompt: str,
        trace: list[dict],
        badcases: list[dict],
        provider_metrics: list[dict],
        *,
        sample_id: str,
    ) -> dict | None:
        system_prompt = load_prompt(prompt_name)
        raw_model_output = None
        try:
            response = self.provider.complete_json(
                prompt_name=prompt_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            raw_model_output = response.content
            provider_metrics.append(
                {
                    "prompt_name": prompt_name,
                    "latency_ms": response.latency_ms,
                    "usage": response.usage,
                    "token_estimate": response.token_estimate,
                }
            )
            payload = json.loads(response.content)
            trace.append(
                {
                    "sample_id": sample_id,
                    "actor": self.provider.name,
                    "action": f"{prompt_name}_prompt",
                    "json_parse_success": True,
                    "latency_ms": response.latency_ms,
                }
            )
            return payload
        except json.JSONDecodeError as exc:
            badcases.append(
                {
                    "sample_id": sample_id,
                    "stage": prompt_name,
                    "reason": "json parse failed",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "raw_model_output": raw_model_output,
                    "provider": self.provider.name,
                    "model": getattr(self.provider, "model", None),
                }
            )
        except Exception as exc:
            badcases.append(
                {
                    "sample_id": sample_id,
                    "stage": prompt_name,
                    "reason": "provider call failed",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "raw_model_output": raw_model_output,
                    "provider": self.provider.name,
                    "model": getattr(self.provider, "model", None),
                }
            )
        trace.append(
            {
                "sample_id": sample_id,
                "actor": self.provider.name,
                "action": f"{prompt_name}_prompt",
                "json_parse_success": False,
                "latency_ms": None,
            }
        )
        return None

    def _failed_result(
        self,
        sample_id: str,
        requirement_text: str,
        trace: list[dict],
        badcases: list[dict],
        provider_metrics: list[dict],
    ) -> dict:
        return {
            "sample_id": sample_id,
            "requirement_text": requirement_text,
            "provider": self.provider.name,
            "structured_requirement": {},
            "assumptions": [],
            "draft_configs": {},
            "draft_validation": {"schema_passed": False, "schema_errors": [], "reference_errors": [], "rule_errors": []},
            "review_findings": [],
            "repaired_configs": {},
            "repair_actions": [],
            "final_validation": {"passed": False, "schema_errors": [], "reference_errors": [], "rule_errors": []},
            "test_scenarios": [],
            "evaluation": self.evaluator.evaluate([], EVALUATION_DATASET),
            "badcases": badcases,
            "trace": trace,
            "provider_metrics": provider_metrics,
        }


def run_real_sample(provider: LLMProvider, requirement_text: str, *, sample_id: str = "real_demo_input") -> dict:
    """Run one interactive requirement without appending the offline evaluation dataset."""
    return _run_real_samples(
        provider,
        [{"sample_id": sample_id, "requirement_text": requirement_text}],
    )


def run_real_evaluation(provider: LLMProvider, primary_requirement: str) -> dict:
    """Run the primary requirement plus the fixed Phase 2 evaluation samples."""
    samples = [{"sample_id": "real_demo_input", "requirement_text": primary_requirement}]
    samples.extend(REAL_RUN_EVALUATION_REQUIREMENTS)
    return _run_real_samples(provider, samples)


def _run_real_samples(provider: LLMProvider, samples: list[dict[str, str]]) -> dict:
    pipeline = RealRunPipeline(provider)
    results = []
    for sample in samples:
        try:
            results.append(pipeline.run(sample["requirement_text"], sample_id=sample["sample_id"]))
        except Exception as exc:
            results.append(
                pipeline._failed_result(
                    sample["sample_id"],
                    sample["requirement_text"],
                    [
                        {
                            "sample_id": sample["sample_id"],
                            "actor": provider.name,
                            "action": "pipeline_run",
                            "json_parse_success": False,
                            "latency_ms": None,
                        }
                    ],
                    [
                        {
                            "sample_id": sample["sample_id"],
                            "stage": "pipeline_run",
                            "reason": "unexpected exception",
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                            "raw_model_output": None,
                            "provider": provider.name,
                            "model": getattr(provider, "model", None),
                        }
                    ],
                    [],
                )
            )
    metrics = aggregate_metrics(results)
    return {
        "provider": provider.name,
        "model": getattr(provider, "model", None),
        "results": results,
        "metrics": metrics,
    }


def aggregate_metrics(results: list[dict]) -> dict:
    total = len(results) or 1
    prompt_calls = [metric for result in results for metric in result["provider_metrics"]]
    parse_successes = sum(1 for result in results for event in result["trace"] if event["json_parse_success"])
    parse_attempts = sum(1 for result in results for event in result["trace"])
    latency_values = [metric["latency_ms"] for metric in prompt_calls if metric["latency_ms"] is not None]
    usage_values = [metric["usage"] for metric in prompt_calls if metric.get("usage")]
    token_estimates = [metric["token_estimate"] for metric in prompt_calls if metric.get("token_estimate") is not None]
    return {
        "sample_count": len(results),
        "json_parse_success_rate": parse_successes / parse_attempts if parse_attempts else 0,
        "schema_pass_rate": sum(1 for result in results if result["draft_validation"]["schema_passed"]) / total,
        "final_validation_pass_rate": sum(1 for result in results if result["final_validation"]["passed"]) / total,
        "repair_success_rate": sum(1 for result in results if result["repair_actions"] and result["final_validation"]["passed"]) / total,
        "test_scenario_coverage_rate": sum(result["evaluation"]["coverage"] for result in results) / total,
        "latency_ms": {
            "total": sum(latency_values),
            "average": round(sum(latency_values) / len(latency_values), 2) if latency_values else 0,
        },
        "token_estimate": sum(token_estimates) if token_estimates else None,
        "usage": usage_values or None,
        "badcase_count": sum(len(result["badcases"]) for result in results),
    }


def export_real_run(result: dict, output_dir: str | Path) -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    trace = [event for sample in result["results"] for event in sample["trace"]]
    badcases = [badcase for sample in result["results"] for badcase in sample["badcases"]]
    files = [
        _write_json(output_path / "real_run_result.json", result),
        _write_json(output_path / "real_run_trace.json", trace),
        _write_text(output_path / "real_run_report.md", _real_run_report(result)),
        _write_text(output_path / "badcases.md", _badcases_report(badcases)),
    ]
    return files


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    return path


def _real_run_report(result: dict) -> str:
    metrics = result["metrics"]
    lines = [
        "# Real Run Report",
        "",
        f"- Provider: `{result['provider']}`",
        f"- Sample count: {metrics['sample_count']}",
        f"- JSON parse success rate: {metrics['json_parse_success_rate']:.2%}",
        f"- Schema pass rate: {metrics['schema_pass_rate']:.2%}",
        f"- Final validation pass rate: {metrics['final_validation_pass_rate']:.2%}",
        f"- Repair success rate: {metrics['repair_success_rate']:.2%}",
        f"- Test scenario coverage rate: {metrics['test_scenario_coverage_rate']:.2%}",
        f"- Latency total ms: {metrics['latency_ms']['total']}",
        f"- Latency average ms: {metrics['latency_ms']['average']}",
        f"- Token estimate: {metrics['token_estimate']}",
        f"- Usage entries: {len(metrics['usage'] or [])}",
        f"- Badcase count: {metrics['badcase_count']}",
        "",
        "## Samples",
    ]
    for sample in result["results"]:
        lines.extend(
            [
                f"### {sample['sample_id']}",
                f"- Final validation: {sample['final_validation']['passed']}",
                f"- Scenarios: {len(sample['test_scenarios'])}",
                f"- Coverage: {sample['evaluation']['coverage_percent']}%",
                f"- Badcases: {len(sample['badcases'])}",
                "",
            ]
        )
    return "\n".join(lines)


def _badcases_report(badcases: list[dict]) -> str:
    lines = ["# Badcases", ""]
    if not badcases:
        lines.append("- None")
        return "\n".join(lines) + "\n"
    for index, badcase in enumerate(badcases, start=1):
        lines.extend(
            [
                f"## Badcase {index}",
                f"- Sample: `{badcase.get('sample_id')}`",
                f"- Stage: `{badcase.get('stage')}`",
                f"- Reason: {badcase.get('reason')}",
                f"- Error type: `{badcase.get('error_type')}`",
                f"- Error message: {badcase.get('error_message')}",
                f"- Provider: `{badcase.get('provider')}`",
                f"- Model: `{badcase.get('model')}`",
                f"- Detail: `{json.dumps(badcase, ensure_ascii=False)}`",
                "",
            ]
        )
    return "\n".join(lines)
