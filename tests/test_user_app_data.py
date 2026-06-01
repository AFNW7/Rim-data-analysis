from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

import rim_data_analysis.user_app_data as user_app_data_module

from rim_data_analysis.user_app_data import (
    EquipmentChoice,
    QUALITY_OPTIONS,
    SavedPawnTemplate,
    SavedScenarioTemplate,
    UserAppStore,
    WEAPON_QUALITY_RULES_BY_ID,
    build_analysis_for_saved_scenario,
    build_firepower_preview_for_pawn,
    build_pawn_profile,
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


def test_store_keeps_multiple_pawns_when_names_match_but_ids_differ() -> None:
    store = UserAppStore(_store_root("same-name-snapshots"))
    store.save_pawn(
        SavedPawnTemplate(
            id="pawn-a",
            name="测试射手",
            species_id="human_baseliner",
            shooting_skill=12,
        )
    )
    store.save_pawn(
        SavedPawnTemplate(
            id="pawn-b",
            name="测试射手",
            species_id="human_baseliner",
            shooting_skill=14,
        )
    )

    pawns = store.list_pawns()

    assert len(pawns) == 2
    assert [pawn.id for pawn in pawns] == ["pawn-a", "pawn-b"]
    assert all(pawn.name == "测试射手" for pawn in pawns)


def test_store_make_id_stays_unique_when_timestamp_and_slug_base_match(monkeypatch: pytest.MonkeyPatch) -> None:
    store = UserAppStore(_store_root("same-slug-batch-save"))
    suffixes = iter(["aaa11111", "bbb22222", "ccc33333", "ddd44444", "eee55555"])
    monkeypatch.setattr(user_app_data_module, "_timestamp_slug", lambda: "20260601-120000-000000")
    monkeypatch.setattr(user_app_data_module, "_nonce_slug", lambda: next(suffixes))

    for index, name in enumerate(
        [
            "攻击者甲 VS 靶70",
            "攻击者乙 VS 靶70",
            "攻击者丙 VS 靶70",
            "攻击者丁 VS 靶70",
            "攻击者戊 VS 靶70",
        ],
        start=1,
    ):
        store.save_scenario(
            SavedScenarioTemplate(
                id=store.make_id(name),
                name=name,
                attacker_pawn_id=f"attacker-{index}",
                defender_pawn_id="defender-70",
            )
        )

    scenarios = store.list_scenarios()

    assert len(scenarios) == 5
    assert len({scenario.id for scenario in scenarios}) == 5


def test_store_finds_existing_scenario_by_pawn_id_pair_and_parameters() -> None:
    store = UserAppStore(_store_root("scenario-signature"))
    existing = store.save_scenario(
        SavedScenarioTemplate(
            id="scenario-existing",
            name="攻击者甲 VS 靶70",
            attacker_pawn_id="attacker-a",
            defender_pawn_id="defender-70",
            distance_cells=24,
            hit_chance_percent=85.0,
        )
    )

    matched = store.find_scenario_by_signature(
        attacker_pawn_id="attacker-a",
        defender_pawn_id="defender-70",
        distance_cells=24,
        hit_chance_percent=85.0,
    )

    assert matched is not None
    assert matched.id == existing.id


def test_store_allows_same_pawn_pair_when_distance_or_hit_differs() -> None:
    store = UserAppStore(_store_root("scenario-signature-variants"))
    store.save_scenario(
        SavedScenarioTemplate(
            id="scenario-base",
            name="攻击者甲 VS 靶70",
            attacker_pawn_id="attacker-a",
            defender_pawn_id="defender-70",
            distance_cells=24,
            hit_chance_percent=85.0,
        )
    )

    different_distance = store.find_scenario_by_signature(
        attacker_pawn_id="attacker-a",
        defender_pawn_id="defender-70",
        distance_cells=25,
        hit_chance_percent=85.0,
    )
    different_hit = store.find_scenario_by_signature(
        attacker_pawn_id="attacker-a",
        defender_pawn_id="defender-70",
        distance_cells=24,
        hit_chance_percent=90.0,
    )

    assert different_distance is None
    assert different_hit is None


def test_store_persists_full_body_armor_percent() -> None:
    store = UserAppStore(_store_root("full-body-armor"))
    store.save_pawn(
        SavedPawnTemplate(
            id="pawn-armor",
            name="70%闈跺瓙",
            species_id="armor_dummy_heavy",
            full_body_armor_percent=70.0,
        )
    )

    loaded = store.load_pawn("pawn-armor")

    assert loaded.species_id == "armor_dummy_heavy"
    assert loaded.full_body_armor_percent == 70.0


def test_store_persists_support_gear_and_implants() -> None:
    store = UserAppStore(_store_root("enhancements"))
    store.save_pawn(
        SavedPawnTemplate(
            id="pawn-enhanced",
            name="强化射手",
            species_id="human_baseliner",
            support_gear_ids=["heavy_ammo_harness"],
            implant_ids=["archotech_eye", "bionic_arm"],
        )
    )

    loaded = store.load_pawn("pawn-enhanced")

    assert loaded.support_gear_ids == ["heavy_ammo_harness"]
    assert loaded.implant_ids == ["archotech_eye", "bionic_arm"]


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


def test_build_firepower_preview_for_pawn_returns_reference_rows() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    pawn = SavedPawnTemplate(
        id="preview-pawn",
        name="预览射手",
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

    preview = build_firepower_preview_for_pawn(pawn, catalog_index)

    assert preview.best_distance_label in {
        "贴近\n3格",
        "近\n12格",
        "中\n25格",
        "远\n40格",
    }
    assert preview.final_hit_percent > 0
    assert preview.actual_warmup_seconds > 0
    assert preview.actual_cooldown_seconds > 0
    assert len(preview.targets) == 5
    assert preview.targets[0].label == "0% 无甲参考"
    assert preview.targets[0].ratio_to_unarmored == 1.0
    assert all(row.expected_dps >= 0 for row in preview.targets)


def test_full_body_armor_target_reduces_expected_damage() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    attacker = SavedPawnTemplate(
        id="attacker",
        name="娴嬭瘯灏勬墜",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )
    unarmored = SavedPawnTemplate(
        id="defender-0",
        name="鏃犵敳闈跺瓙",
        species_id="armor_dummy_unarmored",
        full_body_armor_percent=0.0,
    )
    heavy_armor = SavedPawnTemplate(
        id="defender-70",
        name="閲嶇敳闈跺瓙",
        species_id="armor_dummy_heavy",
        full_body_armor_percent=70.0,
    )

    _, unarmored_row = build_analysis_for_saved_scenario(
        SavedScenarioTemplate(
            id="scenario-unarmored",
            name="鏃犵敳瀵规瘮",
            attacker_pawn_id=attacker.id,
            defender_pawn_id=unarmored.id,
            distance_cells=18,
            hit_chance_percent=100,
        ),
        {attacker.id: attacker, unarmored.id: unarmored},
        catalog_index,
    )
    _, heavy_row = build_analysis_for_saved_scenario(
        SavedScenarioTemplate(
            id="scenario-heavy",
            name="閲嶇敳瀵规瘮",
            attacker_pawn_id=attacker.id,
            defender_pawn_id=heavy_armor.id,
            distance_cells=18,
            hit_chance_percent=100,
        ),
        {attacker.id: attacker, heavy_armor.id: heavy_armor},
        catalog_index,
    )

    assert heavy_row.expected_dps < unarmored_row.expected_dps
    assert heavy_row.expected_damage_on_hit < unarmored_row.expected_damage_on_hit


def test_support_gear_reduces_preview_cooldown() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    baseline = SavedPawnTemplate(
        id="baseline",
        name="基础射手",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )
    enhanced = SavedPawnTemplate(
        id="enhanced",
        name="弹药带射手",
        species_id="human_baseliner",
        shooting_skill=12,
        support_gear_ids=["heavy_ammo_harness"],
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )

    baseline_preview = build_firepower_preview_for_pawn(baseline, catalog_index)
    enhanced_preview = build_firepower_preview_for_pawn(enhanced, catalog_index)

    assert enhanced_preview.actual_cooldown_seconds < baseline_preview.actual_cooldown_seconds


def test_weapon_quality_rules_match_expected_table() -> None:
    expected = {
        "awful": (0.80, 0.80, 0.80, 0.90, 0.90),
        "poor": (0.90, 0.90, 0.90, 1.00, 1.00),
        "normal": (1.00, 1.00, 1.00, 1.00, 1.00),
        "good": (1.10, 1.10, 1.10, 1.00, 1.00),
        "excellent": (1.20, 1.20, 1.20, 1.00, 1.00),
        "masterwork": (1.45, 1.45, 1.35, 1.25, 1.25),
        "legendary": (1.65, 1.65, 1.50, 1.50, 1.50),
    }

    for quality_id, values in expected.items():
        rule = WEAPON_QUALITY_RULES_BY_ID[quality_id]
        assert (
            rule.melee_damage_multiplier,
            rule.melee_armor_penetration_multiplier,
            rule.ranged_accuracy_multiplier,
            rule.ranged_damage_multiplier,
            rule.ranged_armor_penetration_multiplier,
        ) == values


def test_quality_labels_match_game_terms() -> None:
    labels_by_id = {item.id: item.label for item in QUALITY_OPTIONS}

    assert labels_by_id == {
        "awful": "极差",
        "poor": "较差",
        "normal": "一般",
        "good": "良好",
        "excellent": "极佳",
        "masterwork": "大师",
        "legendary": "传奇",
    }


def test_weapon_quality_affects_ranged_and_melee_profiles_with_correct_formula() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    ranged_pawn = SavedPawnTemplate(
        id="quality-ranged",
        name="quality ranged",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="masterwork",
            material_id="steel",
        ),
    )
    melee_pawn = SavedPawnTemplate(
        id="quality-melee",
        name="quality melee",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="MeleeWeapon_TestMace",
            label="test mace",
            quality_id="legendary",
            material_id=None,
        ),
    )

    _, ranged_weapon = build_pawn_profile(ranged_pawn, catalog_index)
    _, melee_weapon = build_pawn_profile(melee_pawn, catalog_index)

    assert ranged_weapon is not None
    assert ranged_weapon.damage == pytest.approx(12.5)
    assert ranged_weapon.armor_penetration == pytest.approx(22.5)
    assert ranged_weapon.accuracy_close == pytest.approx(1.0)
    assert ranged_weapon.accuracy_short == pytest.approx(1.0)
    assert ranged_weapon.warmup_seconds == pytest.approx(1.2)
    assert ranged_weapon.cooldown_seconds == pytest.approx(2.0)

    assert melee_weapon is not None
    assert melee_weapon.damage == pytest.approx(16 * 1.65)
    assert melee_weapon.armor_penetration == pytest.approx(24 * 1.65)
    assert melee_weapon.warmup_seconds == pytest.approx(0.0)
    assert melee_weapon.cooldown_seconds == pytest.approx(2.1)


def test_build_pawn_profile_keeps_melee_skill_independent_from_shooting_skill() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    pawn = SavedPawnTemplate(
        id="skill-split",
        name="skill split",
        species_id="human_baseliner",
        shooting_skill=18,
        melee_skill=4,
    )

    profile, _ = build_pawn_profile(pawn, catalog_index)

    assert profile.shooting_skill == 18
    assert profile.melee_skill == 4


def test_imported_implants_translate_part_efficiency_into_overall_capacities() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    pawn = SavedPawnTemplate(
        id="imported-implants",
        name="imported implants",
        species_id="human_baseliner",
        shooting_skill=12,
        implant_ids=["Implant_BionicEye", "Implant_ArchotechEye", "Implant_BionicArm"],
    )

    profile, _ = build_pawn_profile(pawn, catalog_index)

    assert profile.capacities.sight == pytest.approx(1.4375)
    assert profile.capacities.manipulation == pytest.approx(1.1)


def test_implant_improves_scenario_hit_and_expected_dps() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    baseline = SavedPawnTemplate(
        id="baseline-eye",
        name="基础视力射手",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )
    enhanced = SavedPawnTemplate(
        id="enhanced-eye",
        name="超凡仿生眼射手",
        species_id="human_baseliner",
        shooting_skill=12,
        implant_ids=["archotech_eye"],
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )
    defender = SavedPawnTemplate(
        id="defender-eye",
        name="测试靶子",
        species_id="armor_dummy_unarmored",
        full_body_armor_percent=0.0,
    )

    _, baseline_row = build_analysis_for_saved_scenario(
        SavedScenarioTemplate(
            id="baseline-scenario",
            name="基础命中对比",
            attacker_pawn_id=baseline.id,
            defender_pawn_id=defender.id,
            distance_cells=18,
            hit_chance_percent=100,
        ),
        {baseline.id: baseline, defender.id: defender},
        catalog_index,
    )
    _, enhanced_row = build_analysis_for_saved_scenario(
        SavedScenarioTemplate(
            id="enhanced-scenario",
            name="超凡仿生眼命中对比",
            attacker_pawn_id=enhanced.id,
            defender_pawn_id=defender.id,
            distance_cells=18,
            hit_chance_percent=100,
        ),
        {enhanced.id: enhanced, defender.id: defender},
        catalog_index,
    )

    assert enhanced_row.hit_chance_percent > baseline_row.hit_chance_percent
    assert enhanced_row.expected_dps > baseline_row.expected_dps


def test_apparel_ranged_modifier_improves_preview_output() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    baseline = SavedPawnTemplate(
        id="baseline-duster",
        name="基础风衣射手",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )
    enhanced = SavedPawnTemplate(
        id="enhanced-duster",
        name="带增益风衣射手",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
        apparel=[
            EquipmentChoice(
                def_name="Apparel_TestDuster",
                label="test duster",
                quality_id="normal",
                material_id=None,
            )
        ],
    )

    baseline_preview = build_firepower_preview_for_pawn(baseline, catalog_index)
    enhanced_preview = build_firepower_preview_for_pawn(enhanced, catalog_index)

    assert enhanced_preview.final_hit_percent > baseline_preview.final_hit_percent
    assert enhanced_preview.actual_warmup_seconds < baseline_preview.actual_warmup_seconds
    assert enhanced_preview.actual_cooldown_seconds < baseline_preview.actual_cooldown_seconds
    assert enhanced_preview.targets[0].expected_dps > baseline_preview.targets[0].expected_dps


def test_imported_implant_improves_preview_output() -> None:
    catalog_index = load_catalog_index(Path("tests/fixtures/vanilla_game_data"))
    baseline = SavedPawnTemplate(
        id="baseline-imported-implant",
        name="基础原版植入体射手",
        species_id="human_baseliner",
        shooting_skill=12,
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )
    enhanced = SavedPawnTemplate(
        id="enhanced-imported-implant",
        name="超凡眼原版植入体射手",
        species_id="human_baseliner",
        shooting_skill=12,
        implant_ids=["Implant_ArchotechEye"],
        weapon=EquipmentChoice(
            def_name="Gun_TestRifle",
            label="test rifle",
            quality_id="normal",
            material_id="steel",
        ),
    )

    baseline_preview = build_firepower_preview_for_pawn(baseline, catalog_index)
    enhanced_preview = build_firepower_preview_for_pawn(enhanced, catalog_index)

    assert enhanced_preview.final_hit_percent > baseline_preview.final_hit_percent
    assert enhanced_preview.actual_warmup_seconds == baseline_preview.actual_warmup_seconds
    assert enhanced_preview.targets[0].expected_dps > baseline_preview.targets[0].expected_dps
