from __future__ import annotations

from pathlib import Path

from rim_data_analysis.app_services import (
    load_scenario_payload,
    run_inventory_workflow,
    run_library_workflow,
    run_scenario_payload_workflow,
    run_scenario_workflow,
    run_vanilla_workflow,
    save_scenario_payload,
)


def _output_dir(name: str) -> Path:
    path = Path(".tmp-test") / "app-services" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_run_inventory_workflow_writes_reports() -> None:
    result = run_inventory_workflow(
        game_data_root=Path("tests/fixtures/game_data"),
        local_mods_root=Path("tests/fixtures/local_mods"),
        workshop_root=Path("tests/fixtures/workshop_mods"),
        output_dir=_output_dir("inventory"),
    )

    assert result.workflow_name == "inventory"
    assert any(card.label == "包数量" for card in result.cards)
    assert result.outputs["inventory_json"].exists()
    assert result.outputs["packages_csv"].exists()


def test_run_vanilla_workflow_builds_catalog_outputs() -> None:
    result = run_vanilla_workflow(
        game_data_root=Path("tests/fixtures/vanilla_game_data"),
        output_dir=_output_dir("vanilla"),
    )

    assert result.workflow_name == "vanilla"
    assert any(card.value == "2" for card in result.cards)
    assert result.outputs["catalog_json"].exists()
    assert result.outputs["matchups_csv"].exists()


def test_run_scenario_workflow_writes_result_json() -> None:
    output_path = _output_dir("scenario") / "sample-result.json"
    result = run_scenario_workflow(
        scenario_path=Path("assets/scenarios/sample-ranged-vs-armor.json"),
        output_path=output_path,
    )

    assert result.workflow_name == "scenario"
    assert any(card.label == "期望 DPS" for card in result.cards)
    assert result.outputs["analysis_json"] == output_path
    assert output_path.exists()


def test_run_library_workflow_creates_html_report() -> None:
    result = run_library_workflow(
        library_path=Path("assets/scenario-libraries/sample-library.json"),
        game_data_root=Path("tests/fixtures/vanilla_game_data"),
        output_dir=_output_dir("library"),
    )

    assert result.workflow_name == "library"
    assert any(card.label == "场景" and card.value == "3" for card in result.cards)
    assert result.outputs["comparison_report_html"].exists()


def test_load_and_save_scenario_payload_round_trip() -> None:
    payload = load_scenario_payload(Path("assets/scenarios/sample-ranged-vs-armor.json"))
    output_path = _output_dir("scenario-editor") / "round-trip.json"

    written_path = save_scenario_payload(payload=payload, output_path=output_path)

    assert written_path == output_path
    assert output_path.exists()
    loaded_again = load_scenario_payload(output_path)
    assert loaded_again["name"] == payload["name"]


def test_run_scenario_payload_workflow_writes_scenario_and_analysis_json() -> None:
    payload = load_scenario_payload(Path("assets/scenarios/sample-ranged-vs-armor.json"))
    output_path = _output_dir("scenario-editor-run") / "editor-scenario.json"

    result = run_scenario_payload_workflow(payload=payload, output_path=output_path)

    assert result.workflow_name == "scenario_editor"
    assert result.outputs["scenario_json"].exists()
    assert result.outputs["analysis_json"].exists()
