"""Classic interview demo cases and their deterministic evaluation metadata."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLASSIC_CASE_DIR = PROJECT_ROOT / "examples" / "classic_cases"

CLASSIC_CASES = [
    {
        "case_id": "case_01_baseline_trial",
        "title": "标准新手试炼关卡",
        "category": "baseline_trial",
        "file_path": "examples/classic_cases/case_01_baseline_trial.md",
        "demo_priority": "main",
        "expected_findings": ["baseline_evidence_chain", "runtime_target_deviation"],
        "expected_runtime_targets": {
            "reward_grants": {"item_gold": 300, "item_refine_stone": 3},
            "completion_time_seconds": {"min": 60.0, "max": 90.0},
            "enemies_defeated": 5,
            "skill_uses_min": 1,
            "first_upgrade_affordable": True,
            "second_upgrade_affordable_after_first": False,
        },
    },
    {
        "case_id": "case_02_reward_overgrant",
        "title": "首通奖励过量风险",
        "category": "reward_economy",
        "file_path": "examples/classic_cases/case_02_reward_overgrant.md",
        "demo_priority": "main",
        "expected_findings": ["first_upgrade_affordable", "reward_overgrant"],
        "expected_runtime_targets": {
            "reward_grants": {"item_gold": 300, "item_refine_stone": 3},
            "first_upgrade_affordable": True,
            "second_upgrade_affordable_after_first": False,
        },
    },
    {
        "case_id": "case_03_combat_too_fast",
        "title": "关卡节奏过快风险",
        "category": "combat_pacing",
        "file_path": "examples/classic_cases/case_03_combat_too_fast.md",
        "demo_priority": "main",
        "expected_findings": ["completion_time_below_target"],
        "expected_runtime_targets": {"completion_time_seconds": {"min": 60.0, "max": 90.0}},
    },
    {
        "case_id": "case_04_missing_reference",
        "title": "Trial Medal 引用缺失",
        "category": "missing_reference",
        "file_path": "examples/classic_cases/case_04_missing_reference.md",
        "demo_priority": "backup",
        "expected_findings": ["missing_reference", "bounded_reference_repair"],
        "expected_runtime_targets": {},
    },
    {
        "case_id": "case_05_skill_guidance_balance",
        "title": "技能引导与战斗平衡",
        "category": "skill_guidance",
        "file_path": "examples/classic_cases/case_05_skill_guidance_balance.md",
        "demo_priority": "backup",
        "expected_findings": ["skill_usage_weak_validation"],
        "expected_runtime_targets": {
            "skill_uses_min": 1,
            "completion_time_seconds": {"min": 60.0, "max": 90.0},
            "validation_strength": "weak",
        },
    },
]


def list_classic_cases() -> list[dict]:
    return [load_classic_case(case["case_id"]) for case in CLASSIC_CASES]


def load_classic_case(case_id: str) -> dict:
    metadata = next((case for case in CLASSIC_CASES if case["case_id"] == case_id), None)
    if metadata is None:
        raise KeyError(f"Unknown classic case: {case_id}")
    path = PROJECT_ROOT / metadata["file_path"]
    sections = _parse_sections(path.read_text(encoding="utf-8"))
    value = deepcopy(metadata)
    value["requirement_text"] = sections.get("requirement_text", "").strip()
    value["expected_observations"] = _parse_bullets(sections.get("expected_observations", ""))
    value["recommended_demo_usage"] = sections.get("recommended_demo_usage", "").strip()
    return value


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    active: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            active = line[3:].strip()
            sections[active] = []
        elif active is not None:
            sections[active].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _parse_bullets(text: str) -> list[str]:
    return [line[2:].strip() for line in text.splitlines() if line.startswith("- ")]
