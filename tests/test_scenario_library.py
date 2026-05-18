from __future__ import annotations

from pathlib import Path

from rim_data_analysis.scenario_library import analyze_library, load_scenario_library
from rim_data_analysis.scenario_library_reporting import write_scenario_library_report
from rim_data_analysis.vanilla_parser import build_vanilla_catalog


def test_analyze_library_resolves_templates_and_exports_records() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))
    library = load_scenario_library(Path("assets/scenario-libraries/sample-library.json"))

    records = analyze_library(library, catalog)

    assert len(records) == 3
    first = records[0]
    assert first.library_name == "sample-vanilla-library"
    assert first.analysis.damage.expected_dps >= 0
    assert any(record.attack_mode == "melee" for record in records)


def test_analyze_library_supports_tag_filter() -> None:
    catalog = build_vanilla_catalog(Path("tests/fixtures/vanilla_game_data"))
    library = load_scenario_library(Path("assets/scenario-libraries/sample-library.json"))

    records = analyze_library(library, catalog, required_tags=["layered"])

    assert len(records) == 2
    assert all("layered" in record.tags for record in records)


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
