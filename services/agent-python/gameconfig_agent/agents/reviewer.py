"""Config Reviewer Agent."""

from __future__ import annotations


class ConfigReviewerAgent:
    name = "Config Reviewer Agent"

    def review(self, blackboard: dict) -> list[dict]:
        requirement = blackboard["structured_requirement"]
        configs = blackboard["draft_configs"]
        policy = blackboard["design_reference"][requirement["category"]]
        findings: list[dict] = []

        weapon = configs["weapon_config"][0]
        if weapon["base_attack"] != requirement["base_attack"]:
            findings.append(
                {
                    "section": "Balance & Consistency Review",
                    "issue": "base_attack does not match the requirement and exceeds beginner policy",
                    "evidence": {
                        "actual": weapon["base_attack"],
                        "required": requirement["base_attack"],
                        "recommended_range": policy["base_attack_range"],
                    },
                    "severity": "high",
                    "recommended_range": policy["base_attack_range"],
                    "preferred_fix": "Set base_attack to the requested value 50.",
                }
            )

        levels = sorted(row["level"] for row in configs["upgrade_config"])
        expected_levels = list(range(1, requirement["upgrade_times"] + 1))
        if levels != expected_levels:
            findings.append(
                {
                    "section": "Balance & Consistency Review",
                    "issue": "upgrade levels are not continuous",
                    "evidence": {"actual_levels": levels, "expected_levels": expected_levels},
                    "severity": "high",
                    "recommended_range": expected_levels,
                    "preferred_fix": "Create a local level 2 upgrade row and normalize all level costs.",
                }
            )

        gold_amounts = [
            cost["amount"]
            for row in configs["upgrade_config"]
            for cost in row["cost_items"]
            if cost["item_id"] == "item_gold"
        ]
        if any(amount <= 0 for amount in gold_amounts):
            findings.append(
                {
                    "section": "Balance & Consistency Review",
                    "issue": "upgrade gold cost is too low for the recommended curve",
                    "evidence": {"actual_gold_costs": gold_amounts},
                    "severity": "medium",
                    "recommended_range": policy["recommended_gold_cost"],
                    "preferred_fix": "Use the deterministic beginner curve 100, 150, 200.",
                }
            )

        reward = configs["reward_config"][0]
        if reward["once_only"] is not True:
            findings.append(
                {
                    "section": "Risk Review",
                    "issue": "beginner quest reward can be claimed repeatedly",
                    "evidence": {"once_only": reward["once_only"]},
                    "severity": "critical",
                    "recommended_range": [True],
                    "preferred_fix": "Set reward_config.once_only to true.",
                }
            )

        missing_reference_errors = [
            error for error in blackboard["validation_errors"] if error.get("code") == "missing_reference"
        ]
        if missing_reference_errors:
            findings.append(
                {
                    "section": "Risk Review",
                    "issue": "configuration contains missing item references",
                    "evidence": missing_reference_errors,
                    "severity": "high",
                    "recommended_range": ["all referenced item_id values exist in item_config"],
                    "preferred_fix": "Add a minimal item_refine_stone item definition.",
                }
            )

        blackboard["review_findings"] = findings
        return findings
