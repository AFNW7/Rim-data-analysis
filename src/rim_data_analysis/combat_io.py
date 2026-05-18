from __future__ import annotations

import json
from pathlib import Path

from rim_data_analysis.combat_models import (
    ApparelProfile,
    AttackContext,
    CombatScenario,
    CombatStatModifier,
    PawnCapacities,
    PawnCombatProfile,
    WeaponProfile,
)


def _modifier_from_dict(data: dict[str, object]) -> CombatStatModifier:
    return CombatStatModifier(
        name=str(data.get("name", "custom_modifier")),
        shooting_accuracy_per_tile_offset=float(data.get("shooting_accuracy_per_tile_offset", 0.0)),
        shooting_accuracy_multiplier=float(data.get("shooting_accuracy_multiplier", 1.0)),
        aiming_time_multiplier=float(data.get("aiming_time_multiplier", 1.0)),
        ranged_cooldown_multiplier=float(data.get("ranged_cooldown_multiplier", 1.0)),
        melee_hit_score_offset=float(data.get("melee_hit_score_offset", 0.0)),
        melee_hit_chance_offset=float(data.get("melee_hit_chance_offset", 0.0)),
        melee_hit_chance_multiplier=float(data.get("melee_hit_chance_multiplier", 1.0)),
        melee_dodge_score_offset=float(data.get("melee_dodge_score_offset", 0.0)),
        melee_dodge_chance_offset=float(data.get("melee_dodge_chance_offset", 0.0)),
        melee_dodge_chance_multiplier=float(data.get("melee_dodge_chance_multiplier", 1.0)),
        melee_damage_multiplier=float(data.get("melee_damage_multiplier", 1.0)),
        armor_penetration_multiplier=float(data.get("armor_penetration_multiplier", 1.0)),
        incoming_damage_multiplier=float(data.get("incoming_damage_multiplier", 1.0)),
    )


def _apparel_from_dict(data: dict[str, object]) -> ApparelProfile:
    return ApparelProfile(
        name=str(data["name"]),
        source=str(data.get("source", "manual")),
        layers=[str(layer) for layer in data.get("layers", [])],
        covers=[str(region) for region in data.get("covers", [])],
        armor_sharp=float(data.get("armor_sharp", 0.0)),
        armor_blunt=float(data.get("armor_blunt", 0.0)),
        armor_heat=float(data.get("armor_heat", 0.0)),
        layer_priority_override=(
            int(data["layer_priority_override"]) if data.get("layer_priority_override") is not None else None
        ),
    )


def _capacities_from_dict(data: dict[str, object] | None) -> PawnCapacities:
    payload = data or {}
    return PawnCapacities(
        sight=float(payload.get("sight", 1.0)),
        manipulation=float(payload.get("manipulation", 1.0)),
        moving=float(payload.get("moving", 1.0)),
    )


def _pawn_from_dict(data: dict[str, object]) -> PawnCombatProfile:
    capacities_payload = data.get("capacities")
    return PawnCombatProfile(
        name=str(data["name"]),
        species=str(data.get("species", "human_baseliner")),
        shooting_skill=int(data.get("shooting_skill", 10)),
        melee_skill=int(data.get("melee_skill", 10)),
        body_size=float(data.get("body_size", 1.0)),
        capacities=_capacities_from_dict(capacities_payload if isinstance(capacities_payload, dict) else None),
        traits=[str(trait) for trait in data.get("traits", [])],
        modifiers=[
            _modifier_from_dict(modifier)
            for modifier in data.get("modifiers", [])
            if isinstance(modifier, dict)
        ],
        apparel=[
            _apparel_from_dict(apparel)
            for apparel in data.get("apparel", [])
            if isinstance(apparel, dict)
        ],
        shooting_accuracy_per_tile_override=(
            float(data["shooting_accuracy_per_tile_override"])
            if data.get("shooting_accuracy_per_tile_override") is not None
            else None
        ),
        melee_hit_chance_override=(
            float(data["melee_hit_chance_override"])
            if data.get("melee_hit_chance_override") is not None
            else None
        ),
        melee_dodge_chance_override=(
            float(data["melee_dodge_chance_override"])
            if data.get("melee_dodge_chance_override") is not None
            else None
        ),
    )


def _weapon_from_dict(data: dict[str, object]) -> WeaponProfile:
    return WeaponProfile(
        name=str(data["name"]),
        attack_mode=str(data["attack_mode"]),
        damage_type=str(data["damage_type"]),
        damage=float(data["damage"]),
        armor_penetration=float(data.get("armor_penetration", 0.0)),
        warmup_seconds=float(data.get("warmup_seconds", 0.0)),
        cooldown_seconds=float(data.get("cooldown_seconds", 0.0)),
        burst_shot_count=int(data.get("burst_shot_count", 1)),
        burst_shot_interval_seconds=float(data.get("burst_shot_interval_seconds", 0.0)),
        accuracy_close=float(data.get("accuracy_close", 1.0)),
        accuracy_short=float(data.get("accuracy_short", 1.0)),
        accuracy_medium=float(data.get("accuracy_medium", 1.0)),
        accuracy_long=float(data.get("accuracy_long", 1.0)),
    )


def _context_from_dict(data: dict[str, object] | None) -> AttackContext:
    payload = data or {}
    return AttackContext(
        distance_cells=int(payload.get("distance_cells", 12)),
        target_body_region=str(payload.get("target_body_region", "Torso")),
        target_is_aiming_or_firing=bool(payload.get("target_is_aiming_or_firing", False)),
        hit_chance_multiplier=float(payload.get("hit_chance_multiplier", 1.0)),
        cover_block_chance=float(payload.get("cover_block_chance", 0.0)),
    )


def scenario_from_dict(data: dict[str, object]) -> CombatScenario:
    return CombatScenario(
        name=str(data.get("name", "unnamed-scenario")),
        attacker=_pawn_from_dict(data["attacker"]),
        defender=_pawn_from_dict(data["defender"]),
        weapon=_weapon_from_dict(data["weapon"]),
        context=_context_from_dict(data.get("context") if isinstance(data.get("context"), dict) else None),
    )


def load_scenario(path: Path) -> CombatScenario:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Scenario JSON root must be an object.")
    return scenario_from_dict(data)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def modifier_from_dict(data: dict[str, object]) -> CombatStatModifier:
    return _modifier_from_dict(data)


def apparel_from_dict(data: dict[str, object]) -> ApparelProfile:
    return _apparel_from_dict(data)


def capacities_from_dict(data: dict[str, object] | None) -> PawnCapacities:
    return _capacities_from_dict(data)


def pawn_from_dict(data: dict[str, object]) -> PawnCombatProfile:
    return _pawn_from_dict(data)


def weapon_from_dict(data: dict[str, object]) -> WeaponProfile:
    return _weapon_from_dict(data)


def context_from_dict(data: dict[str, object] | None) -> AttackContext:
    return _context_from_dict(data)
