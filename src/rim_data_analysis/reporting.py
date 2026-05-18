from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from rim_data_analysis.models import ScanInventory


def _package_rows(inventory: ScanInventory) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for package in inventory.packages:
        rows.append(
            {
                "source_type": package.source_type,
                "folder_name": package.folder_name,
                "name": package.metadata.name,
                "package_id": package.metadata.package_id,
                "author": package.metadata.author,
                "supported_versions": "|".join(package.metadata.supported_versions),
                "workshop_id": package.workshop_id,
                "root_path": package.root_path,
                "xml_file_count": package.xml_file_count,
                "def_xml_file_count": package.def_xml_file_count,
                "patch_xml_file_count": package.patch_xml_file_count,
                "language_file_count": package.language_file_count,
                "assembly_file_count": package.assembly_file_count,
                "texture_file_count": package.texture_file_count,
                "sound_file_count": package.sound_file_count,
                "has_about_xml": package.has_about_xml,
                "has_load_folders_xml": package.has_load_folders_xml,
                "def_type_count": len(package.def_type_counts),
            }
        )
    return rows


def _def_rows(inventory: ScanInventory) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for package in inventory.packages:
        for def_type, count in sorted(package.def_type_counts.items()):
            rows.append(
                {
                    "source_type": package.source_type,
                    "folder_name": package.folder_name,
                    "name": package.metadata.name,
                    "package_id": package.metadata.package_id,
                    "def_type": def_type,
                    "count": count,
                }
            )
    return rows


def _summary(inventory: ScanInventory) -> dict[str, object]:
    source_counter = Counter(package.source_type for package in inventory.packages)
    def_counter = Counter()
    for package in inventory.packages:
        def_counter.update(package.def_type_counts)

    top_def_types = [
        {"def_type": def_type, "count": count}
        for def_type, count in def_counter.most_common(20)
    ]

    return {
        "package_count": len(inventory.packages),
        "source_type_breakdown": dict(source_counter),
        "top_def_types": top_def_types,
        "resolved_paths": {
            "game_data_root": inventory.game_data_root,
            "local_mods_root": inventory.local_mods_root,
            "workshop_root": inventory.workshop_root,
            "save_data_root": inventory.save_data_root,
        },
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_inventory_report(output_dir: Path, inventory: ScanInventory) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory_json = output_dir / "inventory.json"
    packages_csv = output_dir / "packages.csv"
    def_counts_csv = output_dir / "def_counts.csv"
    summary_json = output_dir / "summary.json"

    inventory_json.write_text(
        json.dumps(inventory.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(packages_csv, _package_rows(inventory))
    _write_csv(def_counts_csv, _def_rows(inventory))
    summary_json.write_text(
        json.dumps(_summary(inventory), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "inventory_json": inventory_json,
        "packages_csv": packages_csv,
        "def_counts_csv": def_counts_csv,
        "summary_json": summary_json,
    }

