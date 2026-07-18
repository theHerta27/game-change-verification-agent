"""Rule Engine Tool."""

from __future__ import annotations


class RuleEngineTool:
    name = "Rule Engine Tool"

    coupled_fields = [
        ["weapon_config.base_attack", "upgrade_config.attack_bonus"],
        ["upgrade_config.attack_bonus", "upgrade_config.cost_items"],
    ]

    def evaluate(self, structured_requirement: dict, configs: dict) -> dict:
        violations: list[dict] = []
        self._check_unique_ids(configs, violations)
        self._check_attack(structured_requirement, configs, violations)
        self._check_upgrade_levels(structured_requirement, configs, violations)
        self._check_upgrade_costs(configs, violations)
        self._check_rewards(configs, violations)
        self._check_runtime_configs(configs, violations)
        self._check_once_only(configs, violations)
        return {"violations": violations, "coupled_fields": self.coupled_fields}

    def _check_unique_ids(self, configs: dict, violations: list[dict]) -> None:
        for group, field in (
            ("item_config", "item_id"),
            ("weapon_config", "weapon_id"),
            ("reward_config", "reward_id"),
            ("enemy_config", "enemy_id"),
            ("skill_config", "skill_id"),
        ):
            values = [row.get(field) for row in configs.get(group, []) if isinstance(row, dict)]
            duplicates = sorted({value for value in values if values.count(value) > 1})
            for value in duplicates:
                violations.append(self._violation("duplicate_id", group, f"Duplicate {field}: {value}"))

    def _check_attack(self, structured_requirement: dict, configs: dict, violations: list[dict]) -> None:
        for index, weapon in enumerate(configs.get("weapon_config", [])):
            if not isinstance(weapon, dict):
                continue
            if weapon.get("base_attack", 0) <= 0:
                violations.append(self._violation("non_positive_attack", f"weapon_config[{index}].base_attack", "Attack must be positive."))

    def _check_upgrade_levels(self, structured_requirement: dict, configs: dict, violations: list[dict]) -> None:
        upgrades = [row for row in configs.get("upgrade_config", []) if isinstance(row, dict)]
        levels = sorted(row.get("level") for row in upgrades)
        expected_levels = list(range(1, structured_requirement.get("upgrade_times", 0) + 1))
        if levels != expected_levels:
            violations.append(
                self._violation(
                    "non_continuous_upgrade_levels",
                    "upgrade_config.level",
                    f"Expected levels {expected_levels}, got {levels}.",
                )
            )
        for index, row in enumerate(configs.get("upgrade_config", [])):
            if not isinstance(row, dict):
                continue
            if row.get("attack_bonus") != structured_requirement.get("upgrade_attack_bonus"):
                violations.append(
                    self._violation(
                        "upgrade_bonus_mismatch",
                        f"upgrade_config[{index}].attack_bonus",
                        "Attack bonus must match the structured requirement.",
                    )
                )

    def _check_upgrade_costs(self, configs: dict, violations: list[dict]) -> None:
        has_zero_gold_cost = False
        for index, row in enumerate(configs.get("upgrade_config", [])):
            if not isinstance(row, dict):
                continue
            for cost_index, cost in enumerate(row.get("cost_items", [])):
                if not isinstance(cost, dict):
                    continue
                if cost.get("amount", 0) < 0:
                    violations.append(
                        self._violation(
                            "negative_upgrade_cost",
                            f"upgrade_config[{index}].cost_items[{cost_index}].amount",
                            "Upgrade cost cannot be negative.",
                        )
                    )
                if cost.get("item_id") == "item_gold" and cost.get("amount") <= 0:
                    has_zero_gold_cost = True
        if has_zero_gold_cost:
            violations.append(
                self._violation(
                    "zero_gold_cost",
                    "upgrade_config.cost_items[item_gold].amount",
                    "Gold cost must be positive for upgrade progression.",
                )
            )

    def _check_rewards(self, configs: dict, violations: list[dict]) -> None:
        for index, reward in enumerate(configs.get("reward_config", [])):
            if not isinstance(reward, dict):
                continue
            for reward_item_index, reward_item in enumerate(reward.get("reward_items", [])):
                if not isinstance(reward_item, dict):
                    continue
                if reward_item.get("amount", 0) <= 0:
                    violations.append(
                        self._violation(
                            "non_positive_reward_amount",
                            f"reward_config[{index}].reward_items[{reward_item_index}].amount",
                            "Reward item amount must be positive.",
                        )
                    )

    def _check_runtime_configs(self, configs: dict, violations: list[dict]) -> None:
        for index, enemy in enumerate(configs.get("enemy_config", [])):
            if not isinstance(enemy, dict):
                continue
            for field in ("max_health", "attack", "move_speed"):
                if enemy.get(field, 0) <= 0:
                    violations.append(
                        self._violation(
                            "non_positive_enemy_stat",
                            f"enemy_config[{index}].{field}",
                            "Enemy combat stats must be positive.",
                        )
                    )

        wave_numbers = [row.get("wave") for row in configs.get("wave_config", []) if isinstance(row, dict)]
        if wave_numbers:
            expected = list(range(1, len(wave_numbers) + 1))
            if sorted(wave_numbers) != expected:
                violations.append(
                    self._violation(
                        "non_continuous_wave_numbers",
                        "wave_config.wave",
                        f"Expected waves {expected}, got {sorted(wave_numbers)}.",
                    )
                )
        for index, wave in enumerate(configs.get("wave_config", [])):
            if not isinstance(wave, dict):
                continue
            if wave.get("count", 0) <= 0:
                violations.append(
                    self._violation(
                        "non_positive_wave_count",
                        f"wave_config[{index}].count",
                        "Wave enemy count must be positive.",
                    )
                )

        for index, skill in enumerate(configs.get("skill_config", [])):
            if not isinstance(skill, dict):
                continue
            for field in ("damage", "cooldown", "range"):
                if skill.get(field, 0) <= 0:
                    violations.append(
                        self._violation(
                            "non_positive_skill_stat",
                            f"skill_config[{index}].{field}",
                            "Skill stats must be positive.",
                        )
                    )

        for index, target in enumerate(configs.get("runtime_target_config", [])):
            if not isinstance(target, dict):
                continue
            minimum = target.get("completion_time_seconds_min")
            maximum = target.get("completion_time_seconds_max")
            if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)) and minimum >= maximum:
                violations.append(
                    self._violation(
                        "invalid_completion_time_target",
                        f"runtime_target_config[{index}]",
                        "completion_time_seconds_min must be lower than completion_time_seconds_max.",
                    )
                )
            if target.get("enemies_defeated", 1) <= 0:
                violations.append(
                    self._violation(
                        "non_positive_enemy_target",
                        f"runtime_target_config[{index}].enemies_defeated",
                        "Target defeated enemy count must be positive.",
                    )
                )
            if target.get("skill_uses_min", 0) < 0:
                violations.append(
                    self._violation(
                        "negative_skill_use_target",
                        f"runtime_target_config[{index}].skill_uses_min",
                        "Target skill use count cannot be negative.",
                    )
                )

    def _check_once_only(self, configs: dict, violations: list[dict]) -> None:
        for index, reward in enumerate(configs.get("reward_config", [])):
            if not isinstance(reward, dict):
                continue
            if reward.get("source") == "beginner_quest" and reward.get("once_only") is not True:
                violations.append(
                    self._violation(
                        "beginner_reward_not_once_only",
                        f"reward_config[{index}].once_only",
                        "Beginner quest reward must be once_only=true.",
                    )
                )

    def _violation(self, code: str, path: str, message: str) -> dict:
        return {"source": self.name, "code": code, "path": path, "message": message}
