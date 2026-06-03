from pathlib import Path

from rim_data_analysis.user_app_catalog import load_catalog_index
from rim_data_analysis.user_app_models import EquipmentChoice, SavedPawnTemplate
from rim_data_analysis.web_api import (
    WebApiRuntime,
    build_firepower_preview_payload,
    build_pawn_options_payload,
)


def test_build_pawn_options_payload_exposes_catalog_choices() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))

    payload = build_pawn_options_payload(catalog_index)

    assert payload["catalog"]["weaponCount"] == 7
    assert payload["species"][0]["id"] == "human_baseliner"
    assert any(item["id"] == "shooting_command" for item in payload["features"])
    assert any(item["defName"] == "Gun_MasterworkMinigun" for item in payload["weapons"])


def test_build_firepower_preview_payload_uses_combat_engine() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))

    payload = build_firepower_preview_payload(
        {
            "id": "preview",
            "name": "测试射手",
            "speciesId": "human_baseliner",
            "featureIds": ["shooting_command"],
            "supportGearIds": ["heavy_ammo_harness"],
            "implantIds": [],
            "shootingSkill": 12,
            "weapon": {
                "def_name": "Gun_MasterworkMinigun",
                "label": "masterwork minigun",
                "quality_id": "masterwork",
                "material_id": None,
            },
            "apparel": [],
        },
        catalog_index,
    )

    assert payload["weaponName"]
    assert payload["bestDistanceCells"] in {3, 12, 25, 40}
    assert payload["finalHitPercent"] > 0
    assert len(payload["targets"]) == 5
    assert payload["targets"][0]["ratioToUnarmored"] == 1.0


def test_runtime_saves_scenarios_and_builds_compare_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RIM_DATA_ANALYSIS_APP_STATE_DIR", str(tmp_path / "state"))
    runtime = WebApiRuntime(Path.cwd())
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))

    attacker = runtime.store.save_pawn(
        SavedPawnTemplate(
            id="attacker",
            name="测试攻击方",
            species_id="human_baseliner",
            shooting_skill=12,
            weapon=EquipmentChoice(
                def_name="Gun_MasterworkMinigun",
                label="masterwork minigun",
                quality_id="masterwork",
                material_id=None,
            ),
        )
    )
    defender = runtime.store.save_pawn(
        SavedPawnTemplate(
            id="defender",
            name="测试防守方",
            species_id="armor_dummy_heavy",
            full_body_armor_percent=70,
        )
    )

    saved_payload = runtime.save_scenarios_from_payload(
        {
            "name": "测试攻击方 VS 测试防守方",
            "attackerPawnIds": [attacker.id],
            "defenderPawnIds": [defender.id],
            "distanceCells": 25,
            "hitChancePercent": 100,
        }
    )

    assert saved_payload["savedCount"] == 1
    scenario_id = saved_payload["saved"][0]["id"]

    compare_payload = runtime.compare_rows_payload([scenario_id], catalog_index)

    assert compare_payload["errors"] == []
    assert compare_payload["rows"][0]["scenarioId"] == scenario_id
    assert compare_payload["rows"][0]["expectedDps"] > 0


def test_runtime_saves_all_attacker_defender_pairs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RIM_DATA_ANALYSIS_APP_STATE_DIR", str(tmp_path / "state"))
    runtime = WebApiRuntime(Path.cwd())

    attackers = [
        runtime.store.save_pawn(
            SavedPawnTemplate(
                id=f"attacker-{index}",
                name=f"测试攻击方{index}",
                species_id="human_baseliner",
                shooting_skill=12,
                weapon=EquipmentChoice(
                    def_name="Gun_MasterworkMinigun",
                    label="masterwork minigun",
                    quality_id="masterwork",
                    material_id=None,
                ),
            )
        )
        for index in range(2)
    ]
    defenders = [
        runtime.store.save_pawn(
            SavedPawnTemplate(
                id=f"defender-{index}",
                name=f"测试防守方{index}",
                species_id="armor_dummy_heavy",
                full_body_armor_percent=70,
            )
        )
        for index in range(2)
    ]

    first_payload = runtime.save_scenarios_from_payload(
        {
            "name": "批量测试",
            "attackerPawnIds": [pawn.id for pawn in attackers],
            "defenderPawnIds": [pawn.id for pawn in defenders],
            "distanceCells": 40,
            "hitChancePercent": 100,
        }
    )

    assert first_payload["savedCount"] == 4
    assert first_payload["skippedCount"] == 0

    duplicate_payload = runtime.save_scenarios_from_payload(
        {
            "name": "批量测试",
            "attackerPawnIds": [pawn.id for pawn in attackers],
            "defenderPawnIds": [pawn.id for pawn in defenders],
            "distanceCells": 40,
            "hitChancePercent": 100,
        }
    )

    assert duplicate_payload["savedCount"] == 0
    assert duplicate_payload["skippedCount"] == 4

    changed_hit_payload = runtime.save_scenarios_from_payload(
        {
            "name": "批量测试",
            "attackerPawnIds": [attackers[0].id],
            "defenderPawnIds": [defenders[0].id],
            "distanceCells": 40,
            "hitChancePercent": 10,
        }
    )

    assert changed_hit_payload["savedCount"] == 1
    assert changed_hit_payload["skippedCount"] == 0


def test_runtime_renames_existing_single_scenario_when_manual_name_changes(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RIM_DATA_ANALYSIS_APP_STATE_DIR", str(tmp_path / "state"))
    runtime = WebApiRuntime(Path.cwd())

    attacker = runtime.store.save_pawn(
        SavedPawnTemplate(
            id="attacker",
            name="测试攻击方",
            species_id="human_baseliner",
            shooting_skill=12,
            weapon=EquipmentChoice(
                def_name="Gun_MasterworkMinigun",
                label="masterwork minigun",
                quality_id="masterwork",
                material_id=None,
            ),
        )
    )
    defender = runtime.store.save_pawn(
        SavedPawnTemplate(
            id="defender",
            name="测试防守方",
            species_id="armor_dummy_heavy",
            full_body_armor_percent=70,
        )
    )

    first_payload = runtime.save_scenarios_from_payload(
        {
            "name": "测试攻击方 VS 测试防守方",
            "attackerPawnIds": [attacker.id],
            "defenderPawnIds": [defender.id],
            "distanceCells": 25,
            "hitChancePercent": 100,
        }
    )
    scenario_id = first_payload["saved"][0]["id"]

    renamed_payload = runtime.save_scenarios_from_payload(
        {
            "name": "场景测试1",
            "attackerPawnIds": [attacker.id],
            "defenderPawnIds": [defender.id],
            "distanceCells": 25,
            "hitChancePercent": 100,
        }
    )

    assert renamed_payload["savedCount"] == 1
    assert renamed_payload["skippedCount"] == 0
    assert renamed_payload["saved"][0]["id"] == scenario_id
    assert renamed_payload["saved"][0]["name"] == "场景测试1"
    assert runtime.store.load_scenario(scenario_id).name == "场景测试1"
