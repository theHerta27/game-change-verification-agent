"""Config Repair Agent."""

from __future__ import annotations

from copy import deepcopy

from gameconfig_agent.data.design_reference import RESOURCE_ITEM_CATALOG


class ConfigRepairAgent:
    name = "Config Repair Agent"

    def repair(self, blackboard: dict) -> list[dict]:
        requirement = blackboard["structured_requirement"]
        policy = blackboard["design_reference"][requirement["category"]]
        repaired = deepcopy(blackboard["draft_configs"])
        actions: list[dict] = []

        weapon = repaired["weapon_config"][0]
        if weapon["base_attack"] != requirement["base_attack"]:
            before = weapon["base_attack"]
            weapon["base_attack"] = requirement["base_attack"]
            actions.append(
                {
                    "action": "set_base_attack",
                    "scope": "weapon_config.base_attack",
                    "before": before,
                    "after": weapon["base_attack"],
                    "reason": "Align with original requirement and beginner policy.",
                }
            )

        item_ids = {item["item_id"] for item in repaired["item_config"]}
        referenced_cost_ids = {
            cost.get("item_id")
            for upgrade in repaired.get("upgrade_config", [])
            for cost in upgrade.get("cost_items", [])
            if isinstance(cost, dict) and cost.get("item_id")
        }
        referenced_cost_ids.update(
            tag if tag.startswith("item_") else f"item_{tag}"
            for tag in requirement.get("cost_item_tags", [])
        )
        unresolved_item_ids: list[str] = []
        for item_id in sorted(referenced_cost_ids - item_ids):
            catalog_item = RESOURCE_ITEM_CATALOG.get(item_id)
            if catalog_item is None:
                unresolved_item_ids.append(item_id)
                actions.append(
                    {
                        "action": "record_unresolved_item_reference",
                        "scope": "item_config",
                        "before": None,
                        "after": item_id,
                        "reason": "Referenced item is not present in the deterministic resource catalog.",
                    }
                )
                continue
            item = deepcopy(catalog_item)
            repaired["item_config"].append(item)
            item_ids.add(item_id)
            actions.append(
                {
                    "action": "add_missing_item_reference",
                    "scope": "item_config",
                    "before": None,
                    "after": item,
                    "reason": "Referenced item is known by the deterministic resource catalog.",
                }
            )

        existing_by_level = {row["level"]: row for row in repaired["upgrade_config"]}
        normalized_upgrades = []
        for index, level in enumerate(range(1, requirement["upgrade_times"] + 1)):
            before = deepcopy(existing_by_level.get(level))
            row = deepcopy(
                existing_by_level.get(
                    level,
                    {
                        "weapon_id": repaired["weapon_config"][0]["weapon_id"],
                        "level": level,
                        "attack_bonus": requirement["upgrade_attack_bonus"],
                        "cost_items": [],
                    },
                )
            )
            row["attack_bonus"] = requirement["upgrade_attack_bonus"]
            row["cost_items"] = [
                {"item_id": "item_gold", "amount": policy["recommended_gold_cost"][index]},
                {
                    "item_id": "item_refine_stone",
                    "amount": policy["recommended_refine_stone_cost"][index],
                },
            ]
            normalized_upgrades.append(row)
            if before != row:
                actions.append(
                    {
                        "action": "normalize_upgrade_level",
                        "scope": f"upgrade_config[level={level}]",
                        "before": before,
                        "after": row,
                        "reason": "Repair coupled level, attack bonus, and cost fields locally.",
                    }
                )
        repaired["upgrade_config"] = normalized_upgrades

        reward = repaired["reward_config"][0]
        if reward["once_only"] is not True:
            before = reward["once_only"]
            reward["once_only"] = True
            actions.append(
                {
                    "action": "set_reward_once_only",
                    "scope": "reward_config.once_only",
                    "before": before,
                    "after": True,
                    "reason": "Beginner quest reward must be one-time.",
                }
            )

        blackboard["repaired_configs"] = repaired
        blackboard["repair_actions"] = actions
        blackboard["requires_regeneration"] = bool(unresolved_item_ids)
        return actions
