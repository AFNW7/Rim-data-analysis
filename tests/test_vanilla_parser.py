from __future__ import annotations

from pathlib import Path

from rim_data_analysis.vanilla_parser import build_vanilla_catalog
from rim_data_analysis.vanilla_reporting import build_vanilla_matchup_rows


def test_build_vanilla_catalog_extracts_weapons_and_apparel() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))

    assert catalog.packages == ["Core"]
    assert len(catalog.weapons) == 2
    assert len(catalog.apparel) == 2

    ranged = next(weapon for weapon in catalog.weapons if weapon.attack_mode == "ranged")
    melee = next(weapon for weapon in catalog.weapons if weapon.attack_mode == "melee")

    assert ranged.def_name == "Gun_TestRifle"
    assert ranged.damage == 10
    assert ranged.armor_penetration == 18
    assert ranged.burst_shot_count == 3
    assert melee.def_name == "MeleeWeapon_TestMace"
    assert melee.damage_type == "Blunt"
    assert melee.armor_penetration == 24


def test_build_vanilla_matchup_rows_returns_cross_product() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))

    rows = build_vanilla_matchup_rows(catalog)

    assert len(rows) == 4
    assert all(row["expected_dps"] >= 0 for row in rows)
