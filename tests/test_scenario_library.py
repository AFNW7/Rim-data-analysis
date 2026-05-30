from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim_data_analysis.scenario_library import (
    ScenarioLibraryValidationError,
    analyze_library,
    load_scenario_library,
)
from rim_data_analysis.scenario_library_reporting import write_scenario_library_report
from rim_data_analysis.vanilla_parser import build_vanilla_catalog


def test_analyze_library_resolves_templates_and_exports_records() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))
    library = load_scenario_library(Path("assets/scenario-libraries/sample-library.json"))

    records = analyze_library(library, catalog)

    assert len(records) == 3
    first = records[0]
    assert first.library_name == "sample-vanilla-library"
    assert library.format_version == 1
    assert first.analysis.damage.expected_dps >= 0
    assert any(record.attack_mode == "melee" for record in records)


def test_analyze_library_supports_tag_filter() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))
    library = load_scenario_library(Path("assets/scenario-libraries/sample-library.json"))

    records = analyze_library(library, catalog, required_tags=["layered"])

    assert len(records) == 2
    assert all("layered" in record.tags for record in records)


def test_shooting_test_library_loads_and_analyzes() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))
    library = load_scenario_library(Path("assets/scenario-libraries/shooting-test-library.json"))

    records = analyze_library(library, catalog)

    assert len(library.templates) == 17
    assert len(records) == 36
    assert any(record.scenario_name == "大师射击专家 vs 防弹三件套" for record in records)
    assert any(record.scenario_name == "传奇乱开枪射击指令 vs 海军动力甲" for record in records)
    assert all(record.analysis.accuracy.attack_mode == "ranged" for record in records)


def test_shooting_test_library_supports_tag_filter() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))
    library = load_scenario_library(Path("assets/scenario-libraries/shooting-test-library.json"))

    records = analyze_library(library, catalog, required_tags=["射击测试", "海军动力甲"])

    assert len(records) == 12
    assert all("海军动力甲" in record.tags for record in records)


def test_write_scenario_library_report_generates_html() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))
    library = load_scenario_library(Path("assets/scenario-libraries/sample-library.json"))
    records = analyze_library(library, catalog)

    output_dir = Path("artifacts/test-scenario-library-report")
    outputs = write_scenario_library_report(output_dir, records)

    assert outputs["comparison_report_html"].exists()
    html = outputs["comparison_report_html"].read_text(encoding="utf-8")
    assert "场景库横向对比" in html
    assert "Rifle vs Vest" in html


def _minimal_library_payload() -> dict[str, object]:
    return {
        "format_version": 1,
        "name": "validation-fixture",
        "templates": [
            {"id": "attacker", "name": "Attacker"},
            {"id": "defender", "name": "Defender"},
        ],
        "scenarios": [
            {
                "id": "duel",
                "name": "Duel",
                "attacker_template": "attacker",
                "defender_template": "defender",
                "manual_weapon": {
                    "name": "Test Knife",
                    "attack_mode": "melee",
                    "damage_type": "Sharp",
                    "damage": 8,
                    "cooldown_seconds": 1.8,
                },
            }
        ],
    }


def _write_library(filename: str, payload: dict[str, object]) -> Path:
    output_dir = Path(".tmp-test") / "scenario-library-validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_load_scenario_library_rejects_duplicate_template_ids() -> None:
    payload = _minimal_library_payload()
    payload["templates"] = [
        {"id": "attacker", "name": "Attacker"},
        {"id": "attacker", "name": "Duplicate Attacker"},
    ]

    with pytest.raises(ScenarioLibraryValidationError, match="duplicates template id 'attacker'"):
        load_scenario_library(_write_library("duplicate-template.json", payload))


def test_load_scenario_library_rejects_two_weapon_sources() -> None:
    payload = _minimal_library_payload()
    payload["scenarios"][0]["weapon_def_name"] = "Gun_TestRifle"  # type: ignore[index]

    with pytest.raises(
        ScenarioLibraryValidationError,
        match="must provide exactly one of 'weapon_def_name' or 'manual_weapon'",
    ):
        load_scenario_library(_write_library("two-weapon-sources.json", payload))


def test_load_scenario_library_rejects_override_extends() -> None:
    payload = _minimal_library_payload()
    payload["scenarios"][0]["attacker_override"] = {"extends": "attacker"}  # type: ignore[index]

    with pytest.raises(
        ScenarioLibraryValidationError,
        match="overrides already apply on top of the base template",
    ):
        load_scenario_library(_write_library("override-extends.json", payload))


def test_load_scenario_library_rejects_inheritance_cycles() -> None:
    payload = _minimal_library_payload()
    payload["templates"] = [
        {"id": "attacker", "name": "Attacker", "extends": "defender"},
        {"id": "defender", "name": "Defender", "extends": "attacker"},
    ]

    with pytest.raises(ScenarioLibraryValidationError, match="creates an inheritance cycle"):
        load_scenario_library(_write_library("inheritance-cycle.json", payload))
