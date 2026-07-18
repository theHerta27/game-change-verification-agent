"""Deterministic requirement intake for the starter trial workspace."""

from __future__ import annotations

import re
from dataclasses import dataclass


SUPPORTED_SIGNALS = {
    "training sword",
    "beginner",
    "trial",
    "weapon",
    "upgrade",
    "reward",
    "enemy",
    "wave",
    "skill",
    "新手",
    "试炼",
    "关卡",
    "武器",
    "升级",
    "奖励",
    "敌人",
    "波次",
    "技能",
    "通关",
    "战斗",
}

UNSUPPORTED_SIGNALS = {
    "笑话": "当前工作台只处理游戏配置需求，不处理闲聊或娱乐问答。",
    "讲个笑话": "当前工作台只处理游戏配置需求，不处理闲聊或娱乐问答。",
    "精美角色": "角色美术生成不属于当前 Starter Trial 配置包。",
    "角色立绘": "角色美术生成不属于当前 Starter Trial 配置包。",
    "美术资产": "美术资产生成不属于当前 Starter Trial 配置包。",
    "抽卡": "抽卡和付费经济不属于当前 Starter Trial 配置包。",
    "商店": "商店和活动系统不属于当前 Starter Trial 配置包。",
    "剧情": "互动叙事和剧情系统不属于当前 Starter Trial 配置包。",
    "多人": "多人玩法不属于当前 Starter Trial 配置包。",
    "joke": "The workspace handles game configuration requirements, not casual chat.",
    "character art": "Character art generation is outside the starter trial config scope.",
    "gacha": "Gacha economy is outside the starter trial config scope.",
    "shop": "Shop systems are outside the starter trial config scope.",
    "multiplayer": "Multiplayer gameplay is outside the starter trial config scope.",
}


@dataclass(frozen=True)
class RequirementIntakeService:
    capability: str = "starter_trial_config"

    def analyze(self, requirement_text: str) -> dict:
        text = requirement_text.strip()
        normalized = _normalize_text(text)
        if not text:
            return _decision("needs_clarification", self.capability, "需求为空，请补充要生成或修改的新手试炼配置。", ["requirement_text"], [], [], "")

        unsupported = _unsupported_reason(normalized)
        if unsupported:
            return _decision("rejected", "unsupported", unsupported, [], [], [], text)

        signal_count = sum(1 for signal in SUPPORTED_SIGNALS if signal in normalized)
        constraints = _extract_constraints(text)
        if signal_count == 0:
            return _decision(
                "rejected",
                "unsupported",
                "未识别到新手试炼、武器、升级、奖励、敌人、技能或运行目标等配置需求。",
                [],
                [],
                [],
                text,
            )

        missing = _missing_information(signal_count, constraints, normalized)
        if missing:
            return _decision(
                "needs_clarification",
                self.capability,
                "需求属于新手试炼配置范围，但缺少可落到配置字段的关键信息。",
                missing,
                [],
                constraints,
                text,
            )

        return _decision(
            "accepted",
            self.capability,
            "需求可进入 Starter Trial 配置生成或修改流程。",
            [],
            [],
            constraints,
            text,
        )


def analyze_requirement(requirement_text: str) -> dict:
    return RequirementIntakeService().analyze(requirement_text)


def _decision(
    decision: str,
    capability: str,
    reason: str,
    missing_information: list[str],
    conflicts: list[dict],
    constraints: list[dict],
    normalized_requirement: str,
) -> dict:
    return {
        "decision": decision,
        "capability": capability,
        "reason": reason,
        "missing_information": missing_information,
        "conflicts": conflicts,
        "constraints": constraints,
        "normalized_requirement": normalized_requirement,
    }


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _unsupported_reason(normalized: str) -> str | None:
    for signal, reason in UNSUPPORTED_SIGNALS.items():
        if signal in normalized:
            return reason
    return None


def _missing_information(signal_count: int, constraints: list[dict], normalized: str) -> list[str]:
    if signal_count >= 2 or constraints:
        return []
    if "关卡" in normalized or "trial" in normalized or "试炼" in normalized:
        return ["target_completion_time", "enemy_or_wave_goal", "reward_or_upgrade_goal"]
    return ["config_target_field"]


def _extract_constraints(text: str) -> list[dict]:
    constraints: list[dict] = []
    constraints.extend(_extract_time_range(text))
    constraints.extend(_extract_integer_constraint(text, r"(?:基础)?攻击力\s*(?:为|=|:)?\s*(\d+)", "weapon_config.base_attack", "eq"))
    constraints.extend(_extract_integer_constraint(text, r"升级\s*(\d+)\s*次", "structured_requirement.upgrade_times", "eq"))
    constraints.extend(_extract_integer_constraint(text, r"击败\s*(\d+)\s*(?:个)?敌人", "runtime_target_config.enemies_defeated", "eq"))
    constraints.extend(_extract_integer_constraint(text, r"技能(?:至少)?使用\s*(\d+)\s*次", "runtime_target_config.skill_uses_min", "gte"))
    constraints.extend(_extract_integer_constraint(text, r"金币\s*(?:为|=|:)?\s*(\d+)", "reward_config.reward_items[item_gold].amount", "eq"))
    return constraints


def _extract_time_range(text: str) -> list[dict]:
    pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|~|到|至|–)\s*(\d+(?:\.\d+)?)\s*(?:秒|s|sec|seconds)?", re.IGNORECASE)
    constraints = []
    for match in pattern.finditer(text):
        minimum = float(match.group(1))
        maximum = float(match.group(2))
        constraints.append(
            {
                "source_text": match.group(0),
                "target_field": "runtime_target_config.completion_time_seconds",
                "operator": "between",
                "value": [minimum, maximum],
            }
        )
    return constraints


def _extract_integer_constraint(text: str, pattern: str, target_field: str, operator: str) -> list[dict]:
    constraints = []
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        constraints.append(
            {
                "source_text": match.group(0),
                "target_field": target_field,
                "operator": operator,
                "value": int(match.group(1)),
            }
        )
    return constraints
