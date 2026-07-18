"""Reference Checker Tool."""

from __future__ import annotations


class ReferenceCheckerTool:
    name = "Reference Checker Tool"

    def check(self, configs: dict) -> list[dict]:
        errors: list[dict] = []
        reported_missing: set[tuple[str | None, str]] = set()
        item_ids = {
            item["item_id"]
            for item in configs.get("item_config", [])
            if isinstance(item, dict) and "item_id" in item
        }
        weapon_ids = {
            weapon["weapon_id"]
            for weapon in configs.get("weapon_config", [])
            if isinstance(weapon, dict) and "weapon_id" in weapon
        }
        enemy_ids = {
            enemy["enemy_id"]
            for enemy in configs.get("enemy_config", [])
            if isinstance(enemy, dict) and "enemy_id" in enemy
        }

        for index, weapon in enumerate(configs.get("weapon_config", [])):
            if not isinstance(weapon, dict):
                continue
            self._require_item(errors, reported_missing, weapon.get("item_id"), f"weapon_config[{index}].item_id", item_ids)

        for index, upgrade in enumerate(configs.get("upgrade_config", [])):
            if not isinstance(upgrade, dict):
                continue
            if upgrade.get("weapon_id") not in weapon_ids:
                errors.append(
                    self._error(
                        "missing_reference",
                        f"upgrade_config[{index}].weapon_id",
                        upgrade.get("weapon_id"),
                        "weapon_config.weapon_id",
                    )
                )
            for cost_index, cost in enumerate(upgrade.get("cost_items", [])):
                if not isinstance(cost, dict):
                    continue
                self._require_item(
                    errors,
                    reported_missing,
                    cost.get("item_id"),
                    f"upgrade_config[{index}].cost_items[{cost_index}].item_id",
                    item_ids,
                )

        for index, reward in enumerate(configs.get("reward_config", [])):
            if not isinstance(reward, dict):
                continue
            self._require_item(
                errors,
                reported_missing,
                reward.get("reward_item_id"),
                f"reward_config[{index}].reward_item_id",
                item_ids,
            )
            if reward.get("weapon_id") not in weapon_ids:
                errors.append(
                    self._error(
                        "missing_reference",
                        f"reward_config[{index}].weapon_id",
                        reward.get("weapon_id"),
                        "weapon_config.weapon_id",
                    )
                )
            for reward_item_index, reward_item in enumerate(reward.get("reward_items", [])):
                if not isinstance(reward_item, dict):
                    continue
                self._require_item(
                    errors,
                    reported_missing,
                    reward_item.get("item_id"),
                    f"reward_config[{index}].reward_items[{reward_item_index}].item_id",
                    item_ids,
                )

        for index, wave in enumerate(configs.get("wave_config", [])):
            if not isinstance(wave, dict):
                continue
            enemy_id = wave.get("enemy_id")
            if enemy_id not in enemy_ids:
                errors.append(
                    self._error(
                        "missing_reference",
                        f"wave_config[{index}].enemy_id",
                        enemy_id,
                        "enemy_config.enemy_id",
                    )
                )
        return errors

    def _require_item(
        self,
        errors: list[dict],
        reported_missing: set[tuple[str | None, str]],
        value: str | None,
        path: str,
        item_ids: set[str],
    ) -> None:
        key = (value, "item_config.item_id")
        if value not in item_ids and key not in reported_missing:
            reported_missing.add(key)
            errors.append(self._error("missing_reference", path, value, "item_config.item_id"))

    def _error(self, code: str, path: str, value: str | None, target: str) -> dict:
        return {
            "source": self.name,
            "code": code,
            "path": path,
            "value": value,
            "target": target,
            "message": f"{value!r} does not exist in {target}.",
        }
