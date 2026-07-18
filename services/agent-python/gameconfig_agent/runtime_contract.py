"""Export validated GameConfig artifacts for the Unity runtime demo."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


RUNTIME_CONTRACT_VERSION = "1.0"
STARTER_TRIAL_CONTRACT_VERSION = "2.0"
STARTER_TRIAL_CONFIG_GROUPS = ("enemy_config", "wave_config", "skill_config", "runtime_target_config")

DEFAULT_RUNTIME_SCENARIO = {
    "scenario_id": "scenario_beginner_trial_arena",
    "display_name": "Beginner Trial Arena",
    "player": {"max_health": 500, "move_speed": 7.0, "attack_range": 3.2, "attack_cooldown": 0.55},
    "skill": {
        "skill_id": "skill_training_slash",
        "display_name": "Training Slash",
        "damage": 100,
        "cooldown": 5.0,
        "range": 4.5,
    },
    "enemies": [
        {"enemy_id": "enemy_training_dummy", "display_name": "Training Dummy", "max_health": 180, "attack": 8, "move_speed": 2.2},
        {"enemy_id": "enemy_training_guard", "display_name": "Training Guard", "max_health": 260, "attack": 12, "move_speed": 2.5},
        {"enemy_id": "enemy_training_elite", "display_name": "Training Elite", "max_health": 700, "attack": 18, "move_speed": 2.0},
    ],
    "waves": [
        {"wave": 1, "enemy_id": "enemy_training_dummy", "count": 2},
        {"wave": 2, "enemy_id": "enemy_training_guard", "count": 2},
        {"wave": 3, "enemy_id": "enemy_training_elite", "count": 1},
    ],
    "targets": {
        "normal_enemy_hits_to_kill_min": 3,
        "normal_enemy_hits_to_kill_max": 6,
        "completion_time_seconds_min": 20.0,
        "completion_time_seconds_max": 150.0,
        "first_upgrade_affordable": True,
        "second_upgrade_affordable": False,
    },
}


def build_runtime_contract(final_configs: dict, scenario: dict | None = None) -> dict:
    required_groups = ("item_config", "weapon_config", "upgrade_config", "reward_config")
    missing = [group for group in required_groups if not isinstance(final_configs.get(group), list)]
    if missing:
        raise ValueError(f"Missing or invalid config groups: {', '.join(missing)}")
    if not final_configs["weapon_config"]:
        raise ValueError("weapon_config must contain at least one weapon.")

    scenario_from_configs = build_runtime_scenario_from_configs(final_configs)
    uses_v2 = has_starter_trial_runtime_configs(final_configs)
    return {
        "contract_version": STARTER_TRIAL_CONTRACT_VERSION if uses_v2 else RUNTIME_CONTRACT_VERSION,
        "source": "GameConfig Agent final_configs",
        "configs": deepcopy(final_configs),
        "runtime_scenario": deepcopy(scenario or scenario_from_configs),
    }


def has_starter_trial_runtime_configs(final_configs: dict) -> bool:
    return any(isinstance(final_configs.get(group), list) and bool(final_configs[group]) for group in STARTER_TRIAL_CONFIG_GROUPS)


def build_runtime_scenario_from_configs(final_configs: dict) -> dict:
    scenario = deepcopy(DEFAULT_RUNTIME_SCENARIO)
    if not has_starter_trial_runtime_configs(final_configs):
        return scenario

    skill_config = final_configs.get("skill_config")
    if isinstance(skill_config, list) and skill_config and isinstance(skill_config[0], dict):
        scenario["skill"] = _runtime_skill(skill_config[0])

    enemy_config = final_configs.get("enemy_config")
    if isinstance(enemy_config, list) and enemy_config:
        enemies = [_runtime_enemy(enemy) for enemy in enemy_config if isinstance(enemy, dict)]
        if enemies:
            scenario["enemies"] = enemies

    wave_config = final_configs.get("wave_config")
    if isinstance(wave_config, list) and wave_config:
        waves = [_runtime_wave(wave) for wave in sorted((row for row in wave_config if isinstance(row, dict)), key=lambda row: row.get("wave", 0))]
        if waves:
            scenario["waves"] = waves

    target_config = final_configs.get("runtime_target_config")
    if isinstance(target_config, list) and target_config and isinstance(target_config[0], dict):
        scenario["targets"].update(_runtime_targets(target_config[0]))

    return scenario


def _runtime_skill(row: dict) -> dict:
    return {
        "skill_id": row["skill_id"],
        "display_name": row["display_name"],
        "damage": row["damage"],
        "cooldown": float(row["cooldown"]),
        "range": float(row["range"]),
    }


def _runtime_enemy(row: dict) -> dict:
    return {
        "enemy_id": row["enemy_id"],
        "display_name": row["display_name"],
        "role": row.get("role", "normal"),
        "max_health": row["max_health"],
        "attack": row["attack"],
        "move_speed": float(row["move_speed"]),
    }


def _runtime_wave(row: dict) -> dict:
    return {"wave": row["wave"], "enemy_id": row["enemy_id"], "count": row["count"]}


def _runtime_targets(row: dict) -> dict:
    return {
        "completion_time_seconds_min": float(row["completion_time_seconds_min"]),
        "completion_time_seconds_max": float(row["completion_time_seconds_max"]),
        "enemies_defeated": row["enemies_defeated"],
        "skill_uses_min": row["skill_uses_min"],
        "first_upgrade_affordable": row["first_upgrade_affordable"],
        "second_upgrade_affordable": row["second_upgrade_affordable"],
    }


def export_runtime_contract(config_path: str | Path, output_path: str | Path) -> Path:
    source = Path(config_path)
    final_configs = json.loads(source.read_text(encoding="utf-8"))
    contract = build_runtime_contract(final_configs)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
