from __future__ import annotations

import argparse
from pathlib import Path

from rim_data_analysis.combat_engine import analyze_scenario
from rim_data_analysis.combat_io import load_scenario, write_json
from rim_data_analysis.paths import discover_paths
from rim_data_analysis.reporting import write_inventory_report
from rim_data_analysis.scanner import build_inventory
from rim_data_analysis.scenario_library import analyze_library, load_scenario_library
from rim_data_analysis.scenario_library_reporting import write_scenario_library_report
from rim_data_analysis.vanilla_parser import build_vanilla_catalog
from rim_data_analysis.vanilla_reporting import write_vanilla_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rim-analysis")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="扫描 RimWorld 与 Mod 包元数据")
    inventory_parser.add_argument("--game-data-root", type=Path, default=None)
    inventory_parser.add_argument("--local-mods-root", type=Path, default=None)
    inventory_parser.add_argument("--workshop-root", type=Path, default=None)
    inventory_parser.add_argument("--save-data-root", type=Path, default=None)
    inventory_parser.add_argument("--output-dir", type=Path, default=Path("artifacts") / "inventory")

    scenario_parser = subparsers.add_parser("analyze-scenario", help="run combat scenario analysis")
    scenario_parser.add_argument("--scenario", type=Path, required=True)
    scenario_parser.add_argument("--output", type=Path, default=None)

    vanilla_parser = subparsers.add_parser("analyze-vanilla", help="analyze vanilla weapons and apparel")
    vanilla_parser.add_argument("--game-data-root", type=Path, default=None)
    vanilla_parser.add_argument("--output-dir", type=Path, default=Path("artifacts") / "vanilla-analysis")
    vanilla_parser.add_argument("--ranged-distance-cells", type=int, default=18)
    vanilla_parser.add_argument("--shooting-skill", type=int, default=12)
    vanilla_parser.add_argument("--melee-skill", type=int, default=12)

    library_parser = subparsers.add_parser("analyze-library", help="analyze a saved scenario library")
    library_parser.add_argument("--library", type=Path, required=True)
    library_parser.add_argument("--game-data-root", type=Path, default=None)
    library_parser.add_argument("--output-dir", type=Path, default=Path("artifacts") / "scenario-library")
    library_parser.add_argument("--tag", action="append", dest="tags", default=[])
    library_parser.add_argument("--scenario-id", action="append", dest="scenario_ids", default=[])
    library_parser.add_argument("--name-contains", type=str, default=None)

    subparsers.add_parser("app", help="launch desktop workbench")

    return parser


def run_inventory(args: argparse.Namespace) -> int:
    discovered = discover_paths()

    game_data_root = args.game_data_root or discovered.game_data_root
    local_mods_root = args.local_mods_root or discovered.local_mods_root
    workshop_root = args.workshop_root or discovered.workshop_root
    save_data_root = args.save_data_root or discovered.save_data_root

    inventory = build_inventory(
        game_data_root=game_data_root,
        local_mods_root=local_mods_root,
        workshop_root=workshop_root,
        save_data_root=save_data_root,
    )
    outputs = write_inventory_report(args.output_dir, inventory)

    print(f"Scanned packages: {len(inventory.packages)}")
    print(f"Game data root: {inventory.game_data_root}")
    print(f"Local mods root: {inventory.local_mods_root}")
    print(f"Workshop root: {inventory.workshop_root}")
    print(f"Save data root: {inventory.save_data_root}")
    for label, path in outputs.items():
        print(f"{label}: {path}")

    return 0


def run_analyze_scenario(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.scenario)
    analysis = analyze_scenario(scenario)

    if args.output:
        write_json(args.output, analysis.to_dict())
        print(f"analysis_json: {args.output}")

    print(f"Scenario: {analysis.scenario_name}")
    print(f"Attack mode: {analysis.accuracy.attack_mode}")
    print(f"Can wear outfit: {analysis.can_wear_outfit}")
    print(f"Final hit chance: {analysis.accuracy.final_hit_chance:.4f}")
    print(f"Expected damage on hit: {analysis.damage.expected_damage_on_hit_after_defense:.4f}")
    print(f"Expected DPS: {analysis.damage.expected_dps:.4f}")

    return 0


def run_analyze_vanilla(args: argparse.Namespace) -> int:
    discovered = discover_paths()
    game_data_root = args.game_data_root or discovered.game_data_root
    if game_data_root is None:
        raise ValueError("Unable to locate RimWorld game Data root. Pass --game-data-root explicitly.")

    catalog = build_vanilla_catalog(game_data_root)
    outputs = write_vanilla_analysis(
        args.output_dir,
        catalog,
        ranged_distance_cells=args.ranged_distance_cells,
        shooting_skill=args.shooting_skill,
        melee_skill=args.melee_skill,
    )

    print(f"Game data root: {catalog.game_data_root}")
    print(f"Packages: {len(catalog.packages)}")
    print(f"Weapons: {len(catalog.weapons)}")
    print(f"Apparel: {len(catalog.apparel)}")
    for label, path in outputs.items():
        print(f"{label}: {path}")

    return 0


def run_analyze_library(args: argparse.Namespace) -> int:
    discovered = discover_paths()
    game_data_root = args.game_data_root or discovered.game_data_root
    if game_data_root is None:
        raise ValueError("Unable to locate RimWorld game Data root. Pass --game-data-root explicitly.")

    catalog = build_vanilla_catalog(game_data_root)
    library = load_scenario_library(args.library)
    records = analyze_library(
        library,
        catalog,
        required_tags=args.tags,
        scenario_ids=args.scenario_ids,
        name_contains=args.name_contains,
    )
    outputs = write_scenario_library_report(args.output_dir, records)

    print(f"Library: {library.name}")
    print(f"Resolved scenarios: {len(records)}")
    for label, path in outputs.items():
        print(f"{label}: {path}")

    return 0


def run_app(_args: argparse.Namespace) -> int:
    from rim_data_analysis.desktop_user_app import main as desktop_main

    return desktop_main()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "inventory":
        return run_inventory(args)
    if args.command == "analyze-scenario":
        return run_analyze_scenario(args)
    if args.command == "analyze-vanilla":
        return run_analyze_vanilla(args)
    if args.command == "analyze-library":
        return run_analyze_library(args)
    if args.command == "app":
        return run_app(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2
