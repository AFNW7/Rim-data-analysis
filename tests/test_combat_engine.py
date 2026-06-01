from __future__ import annotations

from pathlib import Path

import pytest

from rim_data_analysis.combat_engine import (
    _weapon_accuracy_value,
    analyze_scenario,
    compute_melee_dodge_chance,
    compute_melee_hit_chance,
    compute_shooting_accuracy_per_tile,
    find_apparel_conflicts,
    resolve_armor,
)
from rim_data_analysis.combat_io import load_scenario
from rim_data_analysis.combat_models import ApparelProfile, AttackContext, CombatScenario, MeleeAttackOption, PawnCombatProfile, WeaponProfile


def test_careful_shooter_uses_expected_accuracy_curve() -> None:
    pawn = PawnCombatProfile(name="tester", shooting_skill=12, traits=["careful_shooter"])

    accuracy = compute_shooting_accuracy_per_tile(pawn)

    assert accuracy == pytest.approx(0.984995)


def test_melee_curves_match_known_baselines() -> None:
    standard = PawnCombatProfile(name="standard", melee_skill=0)
    brawler = PawnCombatProfile(name="brawler", melee_skill=0, traits=["brawler"])
    defender = PawnCombatProfile(name="defender", melee_skill=20)

    assert compute_melee_hit_chance(standard) == 0.5
    assert compute_melee_hit_chance(brawler) == 0.62
    assert compute_melee_dodge_chance(defender) == 0.3


def test_conflict_detection_uses_layer_and_region_overlap() -> None:
    apparel = [
        ApparelProfile(name="vest", layers=["Middle"], covers=["Torso"]),
        ApparelProfile(name="another-vest", layers=["Middle"], covers=["Torso", "Arms"]),
        ApparelProfile(name="duster", layers=["Shell"], covers=["Torso", "Arms"]),
    ]

    conflicts = find_apparel_conflicts(apparel)

    assert len(conflicts) == 1
    assert conflicts[0].first_item == "vest"
    assert conflicts[0].second_item == "another-vest"


def test_armor_resolution_handles_multilayer_sharp_and_tough() -> None:
    defender = PawnCombatProfile(
        name="target",
        traits=["tough"],
        apparel=[
            ApparelProfile(
                name="outer",
                layers=["Shell"],
                covers=["Torso"],
                armor_sharp=40,
                armor_blunt=10,
            ),
            ApparelProfile(
                name="inner",
                layers=["Middle"],
                covers=["Torso"],
                armor_sharp=80,
                armor_blunt=20,
            ),
        ],
    )
    weapon = WeaponProfile(
        name="rifle",
        attack_mode="ranged",
        damage_type="Sharp",
        damage=10,
        armor_penetration=20,
    )

    result = resolve_armor(defender, weapon, body_region="Torso")

    assert round(result.expected_damage_after_armor, 4) == 4.675
    assert round(result.expected_damage_after_final_multiplier, 4) == 2.3375
    assert round(result.final_damage_distribution["Blunt"], 4) == 1.475
    assert round(result.final_damage_distribution["Sharp"], 4) == 3.2


def test_analyze_scenario_generates_positive_expected_dps() -> None:
    scenario = load_scenario(Path("assets/scenarios/sample-ranged-vs-armor.json"))

    result = analyze_scenario(scenario)

    assert result.can_wear_outfit is True
    assert result.accuracy.attack_mode == "ranged"
    assert result.accuracy.final_hit_chance > 0
    assert result.damage.expected_dps > 0
    assert result.armor.layers[0].apparel_name == "devilstrand-duster-like"


def test_weapon_accuracy_uses_anchor_points_and_linear_interpolation() -> None:
    weapon = WeaponProfile(
        name="test-rifle",
        attack_mode="ranged",
        damage_type="Sharp",
        damage=10,
        armor_penetration=18,
        accuracy_close=0.95,
        accuracy_short=0.87,
        accuracy_medium=0.77,
        accuracy_long=0.60,
    )

    assert _weapon_accuracy_value(weapon, 3)[1] == 0.95
    assert _weapon_accuracy_value(weapon, 12)[1] == 0.87
    assert _weapon_accuracy_value(weapon, 25)[1] == 0.77
    assert _weapon_accuracy_value(weapon, 40)[1] == 0.60
    assert _weapon_accuracy_value(weapon, 14)[1] == 0.87 + (0.77 - 0.87) * (2 / 13)


def test_melee_multi_tool_weapon_uses_weighted_attack_selection() -> None:
    attacker = PawnCombatProfile(
        name="melee-attacker",
        melee_hit_chance_override=1.0,
    )
    defender = PawnCombatProfile(
        name="melee-defender",
        melee_dodge_chance_override=0.0,
    )
    weapon = WeaponProfile(
        name="test-longsword",
        attack_mode="melee",
        damage_type="Sharp",
        damage=23,
        armor_penetration=34.5,
        cooldown_seconds=2.6,
        melee_attack_options=[
            MeleeAttackOption(
                label="handle",
                damage_type="Blunt",
                damage=9,
                armor_penetration=13.5,
                cooldown_seconds=2.0,
            ),
            MeleeAttackOption(
                label="point",
                damage_type="Sharp",
                damage=23,
                armor_penetration=34.5,
                cooldown_seconds=2.6,
            ),
            MeleeAttackOption(
                label="edge",
                damage_type="Sharp",
                damage=23,
                armor_penetration=34.5,
                cooldown_seconds=2.6,
            ),
        ],
    )
    scenario = CombatScenario(
        name="weighted-melee",
        attacker=attacker,
        defender=defender,
        weapon=weapon,
        context=AttackContext(target_body_region="Torso"),
    )

    result = analyze_scenario(scenario)

    assert result.accuracy.final_hit_chance == 1.0
    assert result.damage.raw_damage_on_hit == pytest.approx(22.125)
    assert result.damage.expected_damage_on_hit_after_defense == pytest.approx(22.125)
    assert result.damage.theoretical_dps == pytest.approx(22.125 / 2.5625)
