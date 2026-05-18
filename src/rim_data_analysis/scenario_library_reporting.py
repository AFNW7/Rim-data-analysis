from __future__ import annotations

import csv
import json
from pathlib import Path

from rim_data_analysis.scenario_library import ScenarioRecord


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _comparison_matrix(records: list[ScenarioRecord]) -> list[dict[str, object]]:
    if not records:
        return []

    matrix_rows: list[dict[str, object]] = []
    scenario_columns = [record.scenario_id for record in records]
    metric_extractors = [
        ("scenario_name", lambda record: record.scenario_name),
        ("tags", lambda record: "|".join(record.tags)),
        ("attacker_template", lambda record: record.attacker_template),
        ("defender_template", lambda record: record.defender_template),
        ("weapon_def_name", lambda record: record.weapon_def_name or ""),
        ("attack_mode", lambda record: record.attack_mode),
        ("can_wear_outfit", lambda record: str(record.analysis.can_wear_outfit)),
        ("final_hit_chance", lambda record: record.analysis.accuracy.final_hit_chance),
        ("expected_damage_on_hit", lambda record: record.analysis.damage.expected_damage_on_hit_after_defense),
        ("expected_damage_per_attack_cycle", lambda record: record.analysis.damage.expected_damage_per_attack_cycle),
        ("expected_dps", lambda record: record.analysis.damage.expected_dps),
        ("theoretical_dps", lambda record: record.analysis.damage.theoretical_dps),
        ("realized_dps_ratio", lambda record: record.analysis.damage.realized_dps_ratio),
        ("armor_reduction_rate", lambda record: record.analysis.armor.reduction_rate_from_armor),
        ("incoming_damage_multiplier", lambda record: record.analysis.armor.total_damage_taken_multiplier),
    ]

    for metric_name, extractor in metric_extractors:
        row: dict[str, object] = {"metric": metric_name}
        for scenario_id, record in zip(scenario_columns, records):
            row[scenario_id] = extractor(record)
        matrix_rows.append(row)
    return matrix_rows


def write_scenario_library_report(output_dir: Path, records: list[ScenarioRecord]) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    records_json = output_dir / "scenario_results.json"
    records_csv = output_dir / "scenario_results.csv"
    comparison_csv = output_dir / "comparison_matrix.csv"

    records_json.write_text(
        json.dumps([record.to_dict() for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(records_csv, [record.to_flat_dict() for record in records] or [{"empty": ""}])
    comparison_rows = _comparison_matrix(records)
    _write_csv(comparison_csv, comparison_rows or [{"metric": "no_data"}])

    return {
        "scenario_results_json": records_json,
        "scenario_results_csv": records_csv,
        "comparison_matrix_csv": comparison_csv,
    }
