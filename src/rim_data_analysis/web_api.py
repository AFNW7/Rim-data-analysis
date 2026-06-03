from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from rim_data_analysis.paths import discover_paths
from rim_data_analysis.user_app_analysis import (
    build_analysis_for_saved_scenario,
    build_firepower_preview_for_pawn,
    describe_equipment,
)
from rim_data_analysis.user_app_catalog import CatalogIndex, load_catalog_index
from rim_data_analysis.user_app_models import (
    ComparisonRow,
    EquipmentChoice,
    ImportSettings,
    SavedPawnTemplate,
    SavedScenarioTemplate,
)
from rim_data_analysis.user_app_options import (
    FEATURE_BY_ID,
    FEATURE_OPTIONS,
    IMPLANT_BY_ID,
    IMPLANT_OPTIONS,
    MATERIAL_OPTIONS,
    QUALITY_OPTIONS,
    SPECIES_BY_ID,
    SPECIES_OPTIONS,
    SUPPORT_GEAR_BY_ID,
    SUPPORT_GEAR_OPTIONS,
)
from rim_data_analysis.user_app_store import UserAppStore
from rim_data_analysis.vanilla_models import VanillaApparelRecord, VanillaWeaponRecord


def _normalize_game_data_root(path: str | Path | None) -> Path | None:
    if path in {None, ""}:
        return None
    candidate = Path(path).expanduser()
    if candidate.name.lower() != "data" and (candidate / "Data").exists():
        candidate = candidate / "Data"
    return candidate


def _equipment_choice_from_payload(payload: object) -> EquipmentChoice | None:
    if not isinstance(payload, dict):
        return None
    return EquipmentChoice.from_dict(payload)


def _pawn_from_payload(payload: dict[str, Any]) -> SavedPawnTemplate:
    weapon = _equipment_choice_from_payload(payload.get("weapon"))
    apparel_payload = payload.get("apparel", [])
    apparel = [
        choice
        for item in apparel_payload
        if (choice := _equipment_choice_from_payload(item)) is not None
    ] if isinstance(apparel_payload, list) else []

    return SavedPawnTemplate(
        id=str(payload.get("id", "preview-pawn")),
        name=str(payload.get("name", "未命名人物")),
        species_id=str(payload.get("speciesId", payload.get("species_id", "human_baseliner"))),
        feature_ids=[
            str(item)
            for item in payload.get("featureIds", payload.get("feature_ids", []))
        ],
        support_gear_ids=[
            str(item) for item in payload.get("supportGearIds", payload.get("support_gear_ids", []))
        ],
        implant_ids=[
            str(item)
            for item in payload.get("implantIds", payload.get("implant_ids", []))
        ],
        shooting_skill=int(payload.get("shootingSkill", payload.get("shooting_skill", 10))),
        melee_skill=int(payload.get("meleeSkill", payload.get("melee_skill", 10))),
        full_body_armor_percent=float(
            payload.get("fullBodyArmorPercent", payload.get("full_body_armor_percent", 0.0))
        ),
        weapon=weapon,
        apparel=apparel,
    )


def _weapon_option(record: VanillaWeaponRecord) -> dict[str, object]:
    return {
        "id": record.def_name,
        "name": record.display_label,
        "label": record.label,
        "defName": record.def_name,
        "source": record.source_tag,
        "attackMode": record.attack_mode,
        "supportsMaterial": record.supports_material,
        "detail": [
            ["名称", record.display_label],
            ["类型", "远程" if record.attack_mode == "ranged" else "近战"],
            ["伤害", f"{record.damage:.2f}"],
            ["护甲穿透", f"{record.armor_penetration:.2f}%"],
            [
                "射程精度",
                (
                    f"{record.accuracy_close:.0%}/{record.accuracy_short:.0%}/"
                    f"{record.accuracy_medium:.0%}/{record.accuracy_long:.0%}"
                ),
            ],
            ["defName", record.def_name],
        ],
        "choice": {
            "def_name": record.def_name,
            "label": record.label,
            "quality_id": "normal",
            "material_id": "steel" if record.supports_material else None,
        },
    }


def _apparel_option(record: VanillaApparelRecord) -> dict[str, object]:
    return {
        "id": record.def_name,
        "name": record.display_label,
        "label": record.label,
        "defName": record.def_name,
        "source": record.source_tag,
        "supportsMaterial": record.supports_material,
        "detail": [
            ["名称", record.display_label],
            ["锐器护甲", f"{record.armor_sharp:.2f}%"],
            ["钝器护甲", f"{record.armor_blunt:.2f}%"],
            ["热能护甲", f"{record.armor_heat:.2f}%"],
            ["覆盖部位", "、".join(record.body_part_groups) or "-"],
            ["defName", record.def_name],
        ],
        "choice": {
            "def_name": record.def_name,
            "label": record.label,
            "quality_id": "normal",
            "material_id": "steel" if record.supports_material else None,
        },
    }


def build_pawn_options_payload(catalog_index: CatalogIndex) -> dict[str, object]:
    return {
        "species": [
            {
                "id": item.id,
                "name": item.label,
                "label": item.label,
                "group": item.group,
                "canWearApparel": item.can_wear_apparel,
                "canUseFeatures": item.can_use_features,
                "canUseWeapons": item.can_use_weapons,
                "defaultFullBodyArmorPercent": item.default_full_body_armor_percent,
                "detail": [
                    ["名称", item.label],
                    ["分类", item.group],
                    ["说明", item.description],
                    ["默认护甲", f"{item.default_full_body_armor_percent:.0f}%"],
                ],
            }
            for item in SPECIES_OPTIONS
        ],
        "features": [
            {
                "id": item.id,
                "name": item.label,
                "label": item.label,
                "kind": item.kind,
                "detail": [["名称", item.label], ["类型", item.kind], ["说明", item.description]],
            }
            for item in FEATURE_OPTIONS
        ],
        "supportGear": [
            {
                "id": item.id,
                "name": item.label,
                "label": item.label,
                "source": item.source,
                "detail": [["名称", item.label], ["来源", item.source], ["说明", item.description]],
            }
            for item in SUPPORT_GEAR_OPTIONS
        ],
        "implants": [
            {
                "id": item.id,
                "name": item.label,
                "label": item.label,
                "source": item.source,
                "linkedImplantDefName": item.linked_implant_def_name,
                "detail": [["名称", item.label], ["来源", item.source], ["说明", item.description]],
            }
            for item in IMPLANT_OPTIONS
        ],
        "weapons": [_weapon_option(item) for item in catalog_index.catalog.weapons],
        "apparel": [_apparel_option(item) for item in catalog_index.catalog.apparel],
        "qualities": [asdict(item) for item in QUALITY_OPTIONS],
        "materials": [asdict(item) for item in MATERIAL_OPTIONS],
        "catalog": {
            "gameDataRoot": catalog_index.catalog.game_data_root,
            "weaponCount": len(catalog_index.catalog.weapons),
            "apparelCount": len(catalog_index.catalog.apparel),
            "implantCount": len(catalog_index.catalog.implants),
        },
    }


def build_firepower_preview_payload(
    payload: dict[str, Any],
    catalog_index: CatalogIndex,
) -> dict[str, object]:
    preview = build_firepower_preview_for_pawn(_pawn_from_payload(payload), catalog_index)
    return {
        "weaponName": preview.weapon_name,
        "bestDistanceLabel": preview.best_distance_label,
        "bestDistanceCells": preview.best_distance_cells,
        "finalHitPercent": preview.final_hit_percent,
        "baseWarmupSeconds": preview.base_warmup_seconds,
        "actualWarmupSeconds": preview.actual_warmup_seconds,
        "baseCooldownSeconds": preview.base_cooldown_seconds,
        "actualCooldownSeconds": preview.actual_cooldown_seconds,
        "theoreticalDps": preview.theoretical_dps,
        "targets": [
            {
                "label": target.label,
                "armorPercent": target.armor_percent,
                "expectedDps": target.expected_dps,
                "ratioToUnarmored": target.ratio_to_unarmored,
            }
            for target in preview.targets
        ],
    }


def _feature_labels(ids: list[str]) -> str:
    labels = [FEATURE_BY_ID[item].label for item in ids if item in FEATURE_BY_ID]
    return "、".join(labels) if labels else "无"


def _support_gear_labels(ids: list[str]) -> str:
    labels = [SUPPORT_GEAR_BY_ID[item].label for item in ids if item in SUPPORT_GEAR_BY_ID]
    return "、".join(labels) if labels else "无"


def _implant_labels(ids: list[str]) -> str:
    labels = [IMPLANT_BY_ID[item].label if item in IMPLANT_BY_ID else item for item in ids]
    return "、".join(labels) if labels else "无"


def _equipment_label(choice: EquipmentChoice | None, catalog_index: CatalogIndex) -> str:
    if choice is None:
        return "无"
    weapon = catalog_index.weapons_by_def_name.get(choice.def_name)
    if weapon is not None:
        return describe_equipment(choice, supports_material=weapon.supports_material)
    apparel = catalog_index.apparel_by_def_name.get(choice.def_name)
    if apparel is not None:
        return describe_equipment(choice, supports_material=apparel.supports_material)
    return choice.label


def _pawn_payload(pawn: SavedPawnTemplate, catalog_index: CatalogIndex) -> dict[str, object]:
    species = SPECIES_BY_ID.get(pawn.species_id, SPECIES_BY_ID["human_baseliner"])
    apparel_labels = [
        _equipment_label(choice, catalog_index)
        for choice in pawn.apparel
    ]
    weapon_label = _equipment_label(pawn.weapon, catalog_index)
    detail = [
        ["名称", pawn.name],
        ["基础模板", species.label],
        ["射击等级", str(pawn.shooting_skill)],
        ["全身护甲", f"{pawn.full_body_armor_percent:.0f}%"],
        ["特性", _feature_labels(pawn.feature_ids)],
        ["特殊装备", _support_gear_labels(pawn.support_gear_ids)],
        ["植入体", _implant_labels(pawn.implant_ids)],
        ["武器", weapon_label],
        ["衣着", "、".join(apparel_labels) if apparel_labels else "无"],
    ]
    return {
        "id": pawn.id,
        "name": pawn.name,
        "label": f"{pawn.name} · {pawn.id[-6:]}",
        "speciesId": pawn.species_id,
        "speciesLabel": species.label,
        "shootingSkill": pawn.shooting_skill,
        "meleeSkill": pawn.melee_skill,
        "fullBodyArmorPercent": pawn.full_body_armor_percent,
        "featureIds": list(pawn.feature_ids),
        "supportGearIds": list(pawn.support_gear_ids),
        "implantIds": list(pawn.implant_ids),
        "weaponName": weapon_label,
        "weapon": pawn.weapon.to_dict() if pawn.weapon is not None else None,
        "apparel": [item.to_dict() for item in pawn.apparel],
        "detail": detail,
    }


def _scenario_payload(
    scenario: SavedScenarioTemplate,
    pawns_by_id: dict[str, SavedPawnTemplate],
) -> dict[str, object]:
    attacker = pawns_by_id.get(scenario.attacker_pawn_id)
    defender = pawns_by_id.get(scenario.defender_pawn_id)
    attacker_name = attacker.name if attacker is not None else "未找到攻击方"
    defender_name = defender.name if defender is not None else "未找到防守方"
    detail = [
        ["场景名称", scenario.name],
        ["攻击方", attacker_name],
        ["防守方", defender_name],
        ["距离", str(scenario.distance_cells)],
        ["最终命中率修正", f"{scenario.hit_chance_percent:.0f}%"],
    ]
    return {
        "id": scenario.id,
        "name": scenario.name,
        "label": f"{scenario.name} · {scenario.id[-6:]}",
        "attackerPawnId": scenario.attacker_pawn_id,
        "defenderPawnId": scenario.defender_pawn_id,
        "attackerName": attacker_name,
        "defenderName": defender_name,
        "distanceCells": scenario.distance_cells,
        "hitChancePercent": scenario.hit_chance_percent,
        "detail": detail,
    }


def _comparison_row_payload(row: ComparisonRow) -> dict[str, object]:
    return {
        "scenarioId": row.scenario_id,
        "scenarioName": row.scenario_name,
        "attackerName": row.attacker_name,
        "defenderName": row.defender_name,
        "weaponName": row.weapon_name,
        "expectedDps": row.expected_dps,
        "theoreticalDps": row.theoretical_dps,
        "hitChancePercent": row.hit_chance_percent,
        "expectedDamageOnHit": row.expected_damage_on_hit,
        "armorReductionPercent": row.armor_reduction_percent,
        "damageTakenMultiplier": row.damage_taken_multiplier,
        "distanceCells": row.distance_cells,
        "outfitValid": row.outfit_valid,
    }


def _import_settings_payload(settings: ImportSettings) -> dict[str, object]:
    return {
        "gameDataRoot": settings.game_data_root,
        "workshopRoot": settings.workshop_root,
        "catalogWeaponCount": settings.catalog_weapon_count,
        "catalogApparelCount": settings.catalog_apparel_count,
        "catalogImplantCount": settings.catalog_implant_count,
        "lastImportedAt": settings.last_imported_at,
    }


def _scenario_from_payload(
    payload: dict[str, Any],
    *,
    scenario_id: str = "",
) -> SavedScenarioTemplate:
    return SavedScenarioTemplate(
        id=scenario_id or str(payload.get("id", "")),
        name=str(payload.get("name", "未命名场景")),
        attacker_pawn_id=str(payload.get("attackerPawnId", payload.get("attacker_pawn_id", ""))),
        defender_pawn_id=str(payload.get("defenderPawnId", payload.get("defender_pawn_id", ""))),
        distance_cells=int(payload.get("distanceCells", payload.get("distance_cells", 12))),
        hit_chance_percent=float(
            payload.get("hitChancePercent", payload.get("hit_chance_percent", 100.0))
        ),
    )


class WebApiRuntime:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.store = UserAppStore.for_repo(repo_root)
        self._catalog_cache: tuple[Path, CatalogIndex] | None = None

    def catalog_index(self, override_root: str | None = None) -> CatalogIndex:
        settings = self.store.load_import_settings()
        discovered = discover_paths()
        candidates = [
            _normalize_game_data_root(override_root),
            _normalize_game_data_root(settings.game_data_root),
            _normalize_game_data_root(discovered.game_data_root),
        ]
        game_data_root = next(
            (item for item in candidates if item is not None and item.exists()),
            None,
        )
        if game_data_root is None:
            raise ValueError("未找到 RimWorld Data 目录。请先在数据导入页设置游戏目录。")
        if self._catalog_cache is None or self._catalog_cache[0] != game_data_root:
            self._catalog_cache = (game_data_root, load_catalog_index(game_data_root))
        return self._catalog_cache[1]

    def import_catalog(self, game_data_root: str, workshop_root: str = "") -> dict[str, object]:
        normalized_root = _normalize_game_data_root(game_data_root)
        if normalized_root is None or not normalized_root.exists():
            raise ValueError("请选择有效的 RimWorld Data 目录。")
        catalog_index = self.catalog_index(str(normalized_root))
        settings = self.store.save_import_settings(
            ImportSettings(
                game_data_root=str(normalized_root),
                workshop_root=workshop_root,
                catalog_weapon_count=len(catalog_index.catalog.weapons),
                catalog_apparel_count=len(catalog_index.catalog.apparel),
                catalog_implant_count=len(catalog_index.catalog.implants),
                last_imported_at=datetime.now().isoformat(timespec="seconds"),
            )
        )
        return {
            "settings": _import_settings_payload(settings),
            "catalog": build_pawn_options_payload(catalog_index)["catalog"],
        }

    def resources_payload(self, catalog_index: CatalogIndex) -> dict[str, object]:
        pawns = self.store.list_pawns()
        scenarios = self.store.list_scenarios()
        pawns_by_id = {item.id: item for item in pawns}
        return {
            "pawns": [_pawn_payload(item, catalog_index) for item in pawns],
            "scenarios": [_scenario_payload(item, pawns_by_id) for item in scenarios],
            "settings": _import_settings_payload(self.store.load_import_settings()),
        }

    def build_scenario_preview_payload(
        self,
        payload: dict[str, Any],
        catalog_index: CatalogIndex,
    ) -> dict[str, object]:
        pawns = self.store.list_pawns()
        pawns_by_id = {item.id: item for item in pawns}
        scenario = _scenario_from_payload(payload, scenario_id="preview")
        analysis, row = build_analysis_for_saved_scenario(scenario, pawns_by_id, catalog_index)
        return {
            "row": _comparison_row_payload(row),
            "metrics": {
                "weaponName": row.weapon_name,
                "hitChancePercent": row.hit_chance_percent,
                "expectedDps": row.expected_dps,
                "theoreticalDps": row.theoretical_dps,
                "expectedDamageOnHit": row.expected_damage_on_hit,
                "armorEfficiencyPercent": max(0.0, 100.0 - row.armor_reduction_percent),
                "damageTakenMultiplier": row.damage_taken_multiplier,
                "distanceCells": row.distance_cells,
                "outfitValid": row.outfit_valid,
                "finalHitChance": analysis.accuracy.final_hit_chance,
            },
        }

    def save_scenarios_from_payload(self, payload: dict[str, Any]) -> dict[str, object]:
        attacker_ids = [
            str(item)
            for item in payload.get("attackerPawnIds", payload.get("attacker_pawn_ids", []))
        ]
        defender_ids = [
            str(item)
            for item in payload.get("defenderPawnIds", payload.get("defender_pawn_ids", []))
        ]
        if not attacker_ids:
            raise ValueError("请至少选择一个攻击方人物。")
        if not defender_ids:
            raise ValueError("请至少选择一个防守方人物。")

        pawns = self.store.list_pawns()
        pawns_by_id = {item.id: item for item in pawns}
        distance_cells = int(payload.get("distanceCells", payload.get("distance_cells", 12)))
        hit_chance_percent = float(
            payload.get("hitChancePercent", payload.get("hit_chance_percent", 100.0))
        )
        manual_name = str(payload.get("name", "未命名场景")).strip()
        saved: list[SavedScenarioTemplate] = []
        skipped: list[dict[str, object]] = []
        seen_pairs: set[tuple[str, str]] = set()

        for attacker_id in attacker_ids:
            for defender_id in defender_ids:
                if (attacker_id, defender_id) in seen_pairs:
                    continue
                seen_pairs.add((attacker_id, defender_id))
                attacker = pawns_by_id.get(attacker_id)
                defender = pawns_by_id.get(defender_id)
                if attacker is None or defender is None:
                    skipped.append(
                        {
                            "attackerPawnId": attacker_id,
                            "defenderPawnId": defender_id,
                            "reason": "人物不存在",
                        }
                    )
                    continue
                existing = self.store.find_scenario_by_signature(
                    attacker_pawn_id=attacker_id,
                    defender_pawn_id=defender_id,
                    distance_cells=distance_cells,
                    hit_chance_percent=hit_chance_percent,
                )
                if existing is not None:
                    if len(attacker_ids) == 1 and len(defender_ids) == 1 and manual_name:
                        renamed = self.store.save_scenario(
                            SavedScenarioTemplate(
                                id=existing.id,
                                name=manual_name,
                                attacker_pawn_id=existing.attacker_pawn_id,
                                defender_pawn_id=existing.defender_pawn_id,
                                distance_cells=existing.distance_cells,
                                hit_chance_percent=existing.hit_chance_percent,
                            )
                        )
                        saved.append(renamed)
                        continue
                    skipped.append(
                        {
                            "attackerPawnId": attacker_id,
                            "defenderPawnId": defender_id,
                            "scenarioId": existing.id,
                            "reason": "重复场景",
                        }
                    )
                    continue
                name = (
                    manual_name
                    if len(attacker_ids) == 1 and len(defender_ids) == 1 and manual_name
                    else f"{attacker.name} VS {defender.name}"
                )
                saved.append(
                    self.store.save_scenario(
                        SavedScenarioTemplate(
                            id="",
                            name=name,
                            attacker_pawn_id=attacker_id,
                            defender_pawn_id=defender_id,
                            distance_cells=distance_cells,
                            hit_chance_percent=hit_chance_percent,
                        )
                    )
                )

        return {
            "saved": [_scenario_payload(item, pawns_by_id) for item in saved],
            "skipped": skipped,
            "savedCount": len(saved),
            "skippedCount": len(skipped),
        }

    def compare_rows_payload(
        self,
        scenario_ids: list[str],
        catalog_index: CatalogIndex,
    ) -> dict[str, object]:
        pawns = self.store.list_pawns()
        pawns_by_id = {item.id: item for item in pawns}
        rows: list[dict[str, object]] = []
        errors: list[dict[str, str]] = []
        for scenario_id in scenario_ids:
            try:
                scenario = self.store.load_scenario(scenario_id)
                _, row = build_analysis_for_saved_scenario(scenario, pawns_by_id, catalog_index)
                rows.append(_comparison_row_payload(row))
            except Exception as exc:
                errors.append({"scenarioId": scenario_id, "error": str(exc)})
        return {"rows": rows, "errors": errors}


class _ApiHandler(BaseHTTPRequestHandler):
    server: "_ApiServer"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_ok(self, payload: dict[str, object]) -> None:
        self._send_json(HTTPStatus.OK, {"ok": True, **payload})

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"ok": False, "error": message})

    def _read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("请求 JSON 根节点必须是对象。")
        return payload

    def do_OPTIONS(self) -> None:
        self._send_json(HTTPStatus.NO_CONTENT, {})

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == "/api/health":
                self._send_ok({"status": "running"})
                return
            if parsed.path == "/api/pawn/options":
                catalog = self.server.runtime.catalog_index(query.get("gameDataRoot", [None])[0])
                self._send_ok({"options": build_pawn_options_payload(catalog)})
                return
            if parsed.path == "/api/import/settings":
                self._send_ok(
                    {
                        "settings": _import_settings_payload(
                            self.server.runtime.store.load_import_settings()
                        )
                    }
                )
                return
            if parsed.path == "/api/resources":
                catalog = self.server.runtime.catalog_index(query.get("gameDataRoot", [None])[0])
                self._send_ok(self.server.runtime.resources_payload(catalog))
                return
            if parsed.path == "/api/pawns":
                catalog = self.server.runtime.catalog_index(query.get("gameDataRoot", [None])[0])
                self._send_ok({"pawns": self.server.runtime.resources_payload(catalog)["pawns"]})
                return
            if parsed.path == "/api/scenarios":
                catalog = self.server.runtime.catalog_index(query.get("gameDataRoot", [None])[0])
                self._send_ok(
                    {"scenarios": self.server.runtime.resources_payload(catalog)["scenarios"]}
                )
                return
            self._send_error(HTTPStatus.NOT_FOUND, "未知接口。")
        except Exception as exc:  # pragma: no cover - handler safety net
            self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            payload = self._read_payload()
            if parsed.path == "/api/pawn/preview":
                catalog = self.server.runtime.catalog_index(str(payload.get("gameDataRoot", "")))
                self._send_ok({"preview": build_firepower_preview_payload(payload, catalog)})
                return
            if parsed.path == "/api/import/catalog":
                self._send_ok(
                    self.server.runtime.import_catalog(
                        str(payload.get("gameDataRoot", "")),
                        str(payload.get("workshopRoot", "")),
                    )
                )
                return
            if parsed.path == "/api/pawns/save":
                pawn = _pawn_from_payload(payload)
                catalog = self.server.runtime.catalog_index(str(payload.get("gameDataRoot", "")))
                save_as_new = bool(payload.get("saveAsNew", True) or pawn.id == "preview-pawn")
                pawn_name = pawn.name.strip()
                if not pawn_name:
                    raise ValueError("请输入小人模板名称。")
                existing = self.server.runtime.store.find_pawn_by_name(
                    pawn_name,
                    exclude_id=None if save_as_new else pawn.id,
                )
                if existing is not None:
                    self._send_ok(
                        {
                            "pawn": _pawn_payload(existing, catalog),
                            "savedCount": 0,
                            "skippedCount": 1,
                            "message": f"已存在名为“{existing.name}”的人物，未重复保存。",
                        }
                    )
                    return
                if save_as_new:
                    pawn = SavedPawnTemplate(
                        id="",
                        name=pawn_name,
                        species_id=pawn.species_id,
                        feature_ids=list(pawn.feature_ids),
                        support_gear_ids=list(pawn.support_gear_ids),
                        implant_ids=list(pawn.implant_ids),
                        shooting_skill=pawn.shooting_skill,
                        melee_skill=pawn.melee_skill,
                        full_body_armor_percent=pawn.full_body_armor_percent,
                        weapon=pawn.weapon,
                        apparel=list(pawn.apparel),
                    )
                saved = self.server.runtime.store.save_pawn(pawn)
                self._send_ok(
                    {
                        "pawn": _pawn_payload(saved, catalog),
                        "savedCount": 1,
                        "skippedCount": 0,
                        "message": f"已保存为 {saved.name}",
                    }
                )
                return
            if parsed.path == "/api/scenario/preview":
                catalog = self.server.runtime.catalog_index(str(payload.get("gameDataRoot", "")))
                self._send_ok(self.server.runtime.build_scenario_preview_payload(payload, catalog))
                return
            if parsed.path == "/api/scenarios/save":
                self._send_ok(self.server.runtime.save_scenarios_from_payload(payload))
                return
            if parsed.path == "/api/scenarios/delete":
                scenario_id = str(payload.get("id", payload.get("scenarioId", "")))
                if not scenario_id:
                    raise ValueError("缺少场景 ID。")
                self.server.runtime.store.delete_scenario(scenario_id)
                self._send_ok({"deletedId": scenario_id})
                return
            if parsed.path == "/api/scenarios/delete-duplicates":
                deleted_count = self.server.runtime.store.delete_duplicate_scenarios()
                self._send_ok({"deletedCount": deleted_count})
                return
            if parsed.path == "/api/pawns/delete":
                pawn_id = str(payload.get("id", payload.get("pawnId", "")))
                if not pawn_id:
                    raise ValueError("缺少人物 ID。")
                self.server.runtime.store.delete_pawn(pawn_id)
                self._send_ok({"deletedId": pawn_id})
                return
            if parsed.path == "/api/compare/rows":
                catalog = self.server.runtime.catalog_index(str(payload.get("gameDataRoot", "")))
                scenario_ids = [str(item) for item in payload.get("scenarioIds", [])]
                self._send_ok(self.server.runtime.compare_rows_payload(scenario_ids, catalog))
                return
            self._send_error(HTTPStatus.NOT_FOUND, "未知接口。")
        except Exception as exc:  # pragma: no cover - handler safety net
            self._send_error(HTTPStatus.BAD_REQUEST, str(exc))


class _ApiServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], runtime: WebApiRuntime) -> None:
        super().__init__(address, _ApiHandler)
        self.runtime = runtime


def run_web_api(*, host: str = "127.0.0.1", port: int = 8765, repo_root: Path | None = None) -> int:
    runtime = WebApiRuntime(repo_root or Path.cwd())
    server = _ApiServer((host, port), runtime)
    print(f"Rim 数据分析本地 API 已启动: http://{host}:{port}")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("本地 API 已停止。")
    finally:
        server.server_close()
    return 0
