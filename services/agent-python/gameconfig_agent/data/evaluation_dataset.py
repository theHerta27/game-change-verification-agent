"""Small deterministic evaluation dataset for Phase 1."""

EVALUATION_DATASET = {
    "dataset_id": "phase1_training_sword_coverage_v1",
    "description": "Expected coverage items for Training Sword final config test scenarios.",
    "expected_coverage_tags": [
        "base_attack_exact",
        "weapon_item_reference",
        "upgrade_levels_continuous",
        "upgrade_bonus_per_level",
        "gold_cost_curve",
        "material_cost_curve",
        "reward_once_only",
        "reward_item_reference",
    ],
    "minimum_coverage": 1.0,
}
