from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from rim_data_analysis.user_app_data import (
    EquipmentChoice,
    SavedPawnTemplate,
    SavedScenarioTemplate,
    UserAppStore,
    build_analysis_for_saved_scenario,
    load_catalog_index,
)


def _store_root(name: str) -> Path:
    path = Path(".tmp-test") / "user-app-data" / f"{name}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_store_saves_and_lists_pawns_and_scenarios() -> None:
    store = UserAppStore(_store_root("save-and-list"))
    pawn = store.save_pawn(
        SavedPawnTemplate(
            id="pawn-a",
            name="测试射手",
            species_id="human_baseliner",
            feature_ids=["trigger_happy"],
            shooting_skill=12,
        )
    )
    scenario = store.save_scenario(
        SavedScenarioTemplate(
            id="scenario-a",
            name="测试场景",
            attacker_pawn_id=pawn.id,
            defender_pawn_id=pawn.id,
            distance_cells=18,
            hit_chance_percent=100,
        )
    )

    pawns = store.list_pawns()
    scenarios = store.list_scenarios()

    assert len(pawns) == 1
    assert pawns[0].name == "测试射手"
    assert len(scenarios) == 1
    assert scenarios[0].name == "测试场景"


def test_delete_pawn_blocked_when_used_by_scenario() -> None:
    store = UserAppStore(_store_root("delete-guard"))
    pawn = store.save_pawn(
        SavedPawnTemplate(
            id="pawn-a",
            name="测试射手",
            species_id="human_baseliner",
        )
    )
    store.save_scenario(
        SavedScenarioTemplate(
            id="scenario-a",
            name="场景A",
            attacker_pawn_id=pawn.id,
            defender_pawn_id=pawn.id,
        )
    )

    try:
        store.delete_pawn(pawn.id)
    except ValueError as exc:
        assert "场景" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_build_analysis_for_saved_scenario_returns_comparison_row() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    attacker = SavedPawnTemplate(
        id="attacker",
        name="攻击方",
        species_id="human_baseliner",
        feature_ids=["shooting_specialist"],
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_MasterworkMinigun",
            label="masterwork minigun",
            quality_id="masterwork",
            material_id="steel",
        ),
    )
    defender = SavedPawnTemplate(
        id="defender",
        name="防守方",
        species_id="human_baseliner",
        apparel=[
            EquipmentChoice(
                def_name="Apparel_TestVest",
                label="test vest",
                quality_id="excellent",
                material_id="fiberglass",
            )
        ],
        shooting_skill=0,
    )
    scenario = SavedScenarioTemplate(
        id="scenario-a",
        name="场景A",
        attacker_pawn_id=attacker.id,
        defender_pawn_id=defender.id,
        distance_cells=18,
        hit_chance_percent=100,
    )

    analysis, row = build_analysis_for_saved_scenario(
        scenario,
        {attacker.id: attacker, defender.id: defender},
        catalog_index,
    )

    assert analysis.scenario_name == "场景A"
    assert row.scenario_name == "场景A"
    assert row.expected_dps > 0
    assert row.hit_chance_percent > 0
