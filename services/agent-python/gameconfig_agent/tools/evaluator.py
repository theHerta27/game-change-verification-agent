"""Evaluation Tool for Phase 1 test scenario coverage."""

from __future__ import annotations


class EvaluationTool:
    name = "Evaluation Tool"

    def evaluate(self, scenarios: list[dict], dataset: dict) -> dict:
        expected_tags = set(dataset["expected_coverage_tags"])
        covered_tags = {
            tag
            for scenario in scenarios
            for tag in scenario.get("coverage_tags", [])
            if tag in expected_tags
        }
        missing_tags = sorted(expected_tags - covered_tags)
        coverage = len(covered_tags) / len(expected_tags) if expected_tags else 1.0
        return {
            "dataset_id": dataset["dataset_id"],
            "scenario_count": len(scenarios),
            "expected_tag_count": len(expected_tags),
            "covered_tag_count": len(covered_tags),
            "coverage": coverage,
            "coverage_percent": round(coverage * 100, 2),
            "covered_tags": sorted(covered_tags),
            "missing_tags": missing_tags,
            "passed": coverage >= dataset.get("minimum_coverage", 1.0),
        }
