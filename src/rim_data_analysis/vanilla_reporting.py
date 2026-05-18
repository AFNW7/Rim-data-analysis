from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from rim_data_analysis.combat_engine import analyze_scenario
from rim_data_analysis.combat_models import AttackContext, CombatScenario, PawnCombatProfile
from rim_data_analysis.vanilla_models import VanillaCatalog


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_vanilla_catalog(output_dir: Path, catalog: VanillaCatalog) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog_json = output_dir / "catalog.json"
    weapons_csv = output_dir / "weapons.csv"
    apparel_csv = output_dir / "apparel.csv"
    summary_json = output_dir / "summary.json"

    catalog_json.write_text(json.dumps(catalog.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(weapons_csv, [weapon.to_dict() for weapon in catalog.weapons])
    _write_csv(apparel_csv, [item.to_dict() for item in catalog.apparel])

    attack_mode_counter = Counter(weapon.attack_mode for weapon in catalog.weapons)
    package_counter = Counter([weapon.source_package for weapon in catalog.weapons] + [item.source_package for item in catalog.apparel])
    summary = {
        "game_data_root": catalog.game_data_root,
        "package_count": len(catalog.packages),
        "weapon_count": len(catalog.weapons),
        "apparel_count": len(catalog.apparel),
        "attack_mode_breakdown": dict(attack_mode_counter),
        "package_breakdown": dict(package_counter),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "catalog_json": catalog_json,
        "weapons_csv": weapons_csv,
        "apparel_csv": apparel_csv,
        "summary_json": summary_json,
    }


def build_vanilla_matchup_rows(
    catalog: VanillaCatalog,
    *,
    ranged_distance_cells: int = 18,
    shooting_skill: int = 12,
    melee_skill: int = 12,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for weapon in catalog.weapons:
        for apparel in catalog.apparel:
            attacker = PawnCombatProfile(
                name="baseline-attacker",
                shooting_skill=shooting_skill,
                melee_skill=melee_skill,
            )
            defender = PawnCombatProfile(
                name="baseline-defender",
                shooting_skill=10,
                melee_skill=10,
                apparel=[apparel.to_apparel_profile()],
            )
            scenario = CombatScenario(
                name=f"{weapon.def_name}-vs-{apparel.def_name}",
                attacker=attacker,
                defender=defender,
                weapon=weapon.to_weapon_profile(),
                context=AttackContext(
                    distance_cells=ranged_distance_cells if weapon.attack_mode == "ranged" else 1,
                    target_body_region="Torso",
                ),
            )
            result = analyze_scenario(scenario)
            rows.append(
                {
                    "weapon_def_name": weapon.def_name,
                    "weapon_label": weapon.label,
                    "weapon_source_package": weapon.source_package,
                    "attack_mode": weapon.attack_mode,
                    "apparel_def_name": apparel.def_name,
                    "apparel_label": apparel.label,
                    "apparel_source_package": apparel.source_package,
                    "covers_torso": "Torso" in apparel.body_part_groups,
                    "final_hit_chance": result.accuracy.final_hit_chance,
                    "expected_damage_on_hit": result.damage.expected_damage_on_hit_after_defense,
                    "expected_dps": result.damage.expected_dps,
                    "reduction_rate_from_armor": result.armor.reduction_rate_from_armor,
                }
            )
    return rows


def write_vanilla_analysis(
    output_dir: Path,
    catalog: VanillaCatalog,
    *,
    ranged_distance_cells: int = 18,
    shooting_skill: int = 12,
    melee_skill: int = 12,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog_outputs = write_vanilla_catalog(output_dir, catalog)
    matchup_rows = build_vanilla_matchup_rows(
        catalog,
        ranged_distance_cells=ranged_distance_cells,
        shooting_skill=shooting_skill,
        melee_skill=melee_skill,
    )
    matchups_csv = output_dir / "weapon_apparel_matchups.csv"
    _write_csv(matchups_csv, matchup_rows)
    return {**catalog_outputs, "matchups_csv": matchups_csv}

