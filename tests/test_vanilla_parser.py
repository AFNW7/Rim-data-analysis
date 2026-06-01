from __future__ import annotations

from pathlib import Path

import pytest

from rim_data_analysis.vanilla_parser import build_vanilla_catalog
from rim_data_analysis.vanilla_reporting import build_vanilla_matchup_rows


def test_build_vanilla_catalog_extracts_weapons_and_apparel() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))

    assert catalog.packages == ["Core"]
    assert len(catalog.weapons) == 7
    assert len(catalog.apparel) == 2
    assert len(catalog.implants) == 3

    ranged = next(weapon for weapon in catalog.weapons if weapon.def_name == "Gun_TestRifle")
    autocalc = next(weapon for weapon in catalog.weapons if weapon.def_name == "Gun_AutocalcRifle")
    melee = next(weapon for weapon in catalog.weapons if weapon.def_name == "MeleeWeapon_TestMace")
    melee_autocalc = next(weapon for weapon in catalog.weapons if weapon.def_name == "MeleeWeapon_AutocalcKnife")
    melee_multi = next(weapon for weapon in catalog.weapons if weapon.def_name == "MeleeWeapon_TestLongsword")
    legendary = next(weapon for weapon in catalog.weapons if weapon.def_name == "Gun_LegendaryMinigun")
    masterwork = next(weapon for weapon in catalog.weapons if weapon.def_name == "Gun_MasterworkMinigun")
    bionic_eye = next(implant for implant in catalog.implants if implant.def_name == "Implant_BionicEye")

    assert ranged.def_name == "Gun_TestRifle"
    assert ranged.damage == 10
    assert ranged.armor_penetration == 18
    assert ranged.damage_type == "Sharp"
    assert autocalc.damage == 12
    assert autocalc.damage_type == "Sharp"
    assert autocalc.armor_penetration == 18
    assert ranged.burst_shot_count == 3
    assert melee.def_name == "MeleeWeapon_TestMace"
    assert melee.damage_type == "Blunt"
    assert melee.armor_penetration == 24
    assert melee_autocalc.damage == 20
    assert melee_autocalc.damage_type == "Sharp"
    assert melee_autocalc.armor_penetration == 30
    assert [option.label for option in melee_multi.melee_attack_options] == ["handle", "point", "edge"]
    assert melee_multi.primary_tool_label == "point"
    assert melee_multi.melee_attack_options[0].damage_type == "Blunt"
    assert melee_multi.melee_attack_options[1].armor_penetration == pytest.approx(34.5)
    assert masterwork.damage == 11
    assert masterwork.armor_penetration == 16
    assert legendary.damage == 12
    assert legendary.cooldown_seconds == 1.95
    assert ranged.label == "测试步枪"
    assert ranged.display_label == "测试步枪/vanilla"
    assert melee.label == "测试钉锤"
    assert bionic_eye.body_part_hint == "Eye"
    assert bionic_eye.part_efficiency == 1.25
    assert bionic_eye.label == "仿生眼"
    assert bionic_eye.display_label == "仿生眼/vanilla"


def test_build_vanilla_catalog_marks_material_support() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))

    rifle = next(weapon for weapon in catalog.weapons if weapon.def_name == "Gun_TestRifle")
    minigun = next(weapon for weapon in catalog.weapons if weapon.def_name == "Gun_MasterworkMinigun")
    vest = next(apparel for apparel in catalog.apparel if apparel.def_name == "Apparel_TestVest")
    duster = next(apparel for apparel in catalog.apparel if apparel.def_name == "Apparel_TestDuster")

    assert rifle.supports_material is True
    assert minigun.supports_material is False
    assert vest.supports_material is True
    assert duster.supports_material is False


def test_build_vanilla_catalog_extracts_apparel_ranged_modifiers() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))

    duster = next(apparel for apparel in catalog.apparel if apparel.def_name == "Apparel_TestDuster")

    assert duster.modifier is not None
    assert duster.modifier.shooting_accuracy_multiplier == 1.06
    assert duster.modifier.aiming_time_multiplier == 0.92
    assert duster.modifier.ranged_cooldown_multiplier == 0.95
    assert duster.modifier.sight_multiplier == 1.08


def test_build_vanilla_catalog_extracts_implant_modifiers() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))

    bionic_eye = next(implant for implant in catalog.implants if implant.def_name == "Implant_BionicEye")
    archotech_eye = next(implant for implant in catalog.implants if implant.def_name == "Implant_ArchotechEye")
    bionic_arm = next(implant for implant in catalog.implants if implant.def_name == "Implant_BionicArm")

    assert bionic_eye.modifier is None
    assert archotech_eye.modifier is not None
    assert archotech_eye.modifier.shooting_accuracy_multiplier == 1.04
    assert bionic_arm.modifier is None


def test_build_vanilla_matchup_rows_returns_cross_product() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))

    rows = build_vanilla_matchup_rows(catalog)

    assert len(rows) == 14
    assert all(row["expected_dps"] >= 0 for row in rows)
