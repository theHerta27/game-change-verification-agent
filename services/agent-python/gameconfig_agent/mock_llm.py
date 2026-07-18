"""Deterministic MockLLM used by Phase 0 agents."""

from __future__ import annotations


class MockLLM:
    """A stable stand-in for LLM behavior used in tests and the CLI demo."""

    def infer_training_sword_requirement(self, requirement_text: str) -> tuple[dict, list[dict]]:
        structured_requirement = {
            "request_id": "req_training_sword_beginner_weapon",
            "item_name": "Training Sword",
            "category": "beginner_weapon",
            "base_attack": 50,
            "upgrade_times": 3,
            "upgrade_attack_bonus": 5,
            "cost_item_tags": ["gold", "refine_stone"],
            "reward_channel": "beginner_quest",
            "once_only": True,
        }
        assumptions = [
            {
                "field": "rarity",
                "value": "common",
                "reason": "Beginner quest weapons default to common rarity unless specified.",
            },
            {
                "field": "once_only",
                "value": True,
                "reason": "Beginner quest rewards are assumed to be one-time unless specified.",
            },
        ]
        return structured_requirement, assumptions

    def create_intentionally_flawed_draft(self, structured_requirement: dict) -> dict:
        return {
            "item_config": [
                {
                    "item_id": "item_training_sword",
                    "display_name": "Training Sword",
                    "item_type": "weapon",
                    "rarity": "common",
                },
                {
                    "item_id": "item_gold",
                    "display_name": "Gold",
                    "item_type": "currency",
                    "rarity": "common",
                },
            ],
            "weapon_config": [
                {
                    "weapon_id": "weapon_training_sword",
                    "item_id": "item_training_sword",
                    "weapon_type": "sword",
                    "base_attack": 80,
                    "strength_tier": "common",
                }
            ],
            "upgrade_config": [
                {
                    "weapon_id": "weapon_training_sword",
                    "level": 1,
                    "attack_bonus": structured_requirement["upgrade_attack_bonus"],
                    "cost_items": [
                        {"item_id": "item_gold", "amount": 0},
                        {"item_id": "item_refine_stone", "amount": 1},
                    ],
                },
                {
                    "weapon_id": "weapon_training_sword",
                    "level": 3,
                    "attack_bonus": structured_requirement["upgrade_attack_bonus"],
                    "cost_items": [
                        {"item_id": "item_gold", "amount": 0},
                        {"item_id": "item_refine_stone", "amount": 3},
                    ],
                },
            ],
            "reward_config": [
                {
                    "reward_id": "reward_beginner_training_sword",
                    "quest_id": "quest_beginner_first_weapon",
                    "reward_item_id": "item_training_sword",
                    "weapon_id": "weapon_training_sword",
                    "once_only": False,
                    "source": "beginner_quest",
                }
            ],
        }
