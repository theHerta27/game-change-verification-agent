"""Schema Validator Tool."""

from __future__ import annotations

from gameconfig_agent.schemas import (
    CONFIG_GROUPS,
    ENEMY_FIELDS,
    ENUMS,
    ITEM_FIELDS,
    OPTIONAL_CONFIG_GROUPS,
    REWARD_ITEM_FIELDS,
    REWARD_FIELDS,
    RUNTIME_TARGET_FIELDS,
    SKILL_FIELDS,
    STRUCTURED_REQUIREMENT_FIELDS,
    UPGRADE_FIELDS,
    WAVE_FIELDS,
    WEAPON_FIELDS,
)


ExpectedFieldType = type | tuple[type, ...]


class SchemaValidatorTool:
    name = "Schema Validator Tool"

    def validate(self, structured_requirement: dict, configs: dict) -> list[dict]:
        errors: list[dict] = []
        errors.extend(self._validate_object("structured_requirement", structured_requirement, STRUCTURED_REQUIREMENT_FIELDS))
        if not isinstance(configs, dict):
            errors.append(
                self._error(
                    "invalid_type",
                    "configs",
                    f"Expected object, got {type(configs).__name__}.",
                )
            )
            return errors

        for group in CONFIG_GROUPS:
            if group not in configs:
                errors.append(self._error("missing_group", group, "Config group is missing."))
            elif not isinstance(configs[group], list):
                errors.append(
                    self._error(
                        "invalid_type",
                        group,
                        f"Expected list, got {type(configs[group]).__name__}.",
                    )
                )
        for group in OPTIONAL_CONFIG_GROUPS:
            if group in configs and not isinstance(configs[group], list):
                errors.append(
                    self._error(
                        "invalid_type",
                        group,
                        f"Expected list, got {type(configs[group]).__name__}.",
                    )
                )

        for index, item in enumerate(self._iter_group(configs, "item_config")):
            errors.extend(self._validate_object(f"item_config[{index}]", item, ITEM_FIELDS))
            if isinstance(item, dict):
                errors.extend(self._validate_enums(f"item_config[{index}]", item))
        for index, weapon in enumerate(self._iter_group(configs, "weapon_config")):
            errors.extend(self._validate_object(f"weapon_config[{index}]", weapon, WEAPON_FIELDS))
            if isinstance(weapon, dict):
                errors.extend(self._validate_enums(f"weapon_config[{index}]", weapon))
        for index, upgrade in enumerate(self._iter_group(configs, "upgrade_config")):
            errors.extend(self._validate_object(f"upgrade_config[{index}]", upgrade, UPGRADE_FIELDS))
            if not isinstance(upgrade, dict):
                continue
            cost_items = upgrade.get("cost_items", [])
            if not isinstance(cost_items, list):
                errors.append(
                    self._error(
                        "invalid_type",
                        f"upgrade_config[{index}].cost_items",
                        f"Expected list, got {type(cost_items).__name__}.",
                    )
                )
                continue
            for cost_index, cost in enumerate(cost_items):
                errors.extend(
                    self._validate_object(
                        f"upgrade_config[{index}].cost_items[{cost_index}]",
                        cost,
                        {"item_id": str, "amount": int},
                    )
                )
        for index, reward in enumerate(self._iter_group(configs, "reward_config")):
            errors.extend(self._validate_object(f"reward_config[{index}]", reward, REWARD_FIELDS))
            if isinstance(reward, dict):
                errors.extend(self._validate_enums(f"reward_config[{index}]", reward))
                reward_items = reward.get("reward_items")
                if reward_items is not None:
                    if not isinstance(reward_items, list):
                        errors.append(
                            self._error(
                                "invalid_type",
                                f"reward_config[{index}].reward_items",
                                f"Expected list, got {type(reward_items).__name__}.",
                            )
                        )
                    else:
                        for reward_item_index, reward_item in enumerate(reward_items):
                            errors.extend(
                                self._validate_object(
                                    f"reward_config[{index}].reward_items[{reward_item_index}]",
                                    reward_item,
                                    REWARD_ITEM_FIELDS,
                                )
                            )
        for index, enemy in enumerate(self._iter_group(configs, "enemy_config")):
            errors.extend(self._validate_object(f"enemy_config[{index}]", enemy, ENEMY_FIELDS))
        for index, wave in enumerate(self._iter_group(configs, "wave_config")):
            errors.extend(self._validate_object(f"wave_config[{index}]", wave, WAVE_FIELDS))
        for index, skill in enumerate(self._iter_group(configs, "skill_config")):
            errors.extend(self._validate_object(f"skill_config[{index}]", skill, SKILL_FIELDS))
        for index, target in enumerate(self._iter_group(configs, "runtime_target_config")):
            errors.extend(self._validate_object(f"runtime_target_config[{index}]", target, RUNTIME_TARGET_FIELDS))
        return errors

    def _iter_group(self, configs: dict, group: str) -> list:
        value = configs.get(group, [])
        return value if isinstance(value, list) else []

    def _validate_object(self, path: str, value: dict, fields: dict[str, ExpectedFieldType]) -> list[dict]:
        errors: list[dict] = []
        if not isinstance(value, dict):
            return [
                self._error(
                    "invalid_type",
                    path,
                    f"Expected object, got {type(value).__name__}.",
                )
            ]
        for field, expected_type in fields.items():
            field_path = f"{path}.{field}"
            if field not in value:
                errors.append(self._error("missing_field", field_path, "Required field is missing."))
            elif not isinstance(value[field], expected_type):
                errors.append(
                    self._error(
                        "invalid_type",
                        field_path,
                        f"Expected {_type_name(expected_type)}, got {type(value[field]).__name__}.",
                    )
                )
        return errors

    def _validate_enums(self, path: str, value: dict) -> list[dict]:
        errors: list[dict] = []
        for field, allowed_values in ENUMS.items():
            if field in value and value[field] not in allowed_values:
                errors.append(
                    self._error(
                        "invalid_enum",
                        f"{path}.{field}",
                        f"Expected one of {sorted(allowed_values)}, got {value[field]!r}.",
                    )
                )
        return errors

    def _error(self, code: str, path: str, message: str) -> dict:
        return {"source": self.name, "code": code, "path": path, "message": message}


def _type_name(expected_type: ExpectedFieldType) -> str:
    if isinstance(expected_type, tuple):
        return " or ".join(item.__name__ for item in expected_type)
    return expected_type.__name__
