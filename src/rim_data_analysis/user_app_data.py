from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from rim_data_analysis.combat_engine import analyze_scenario
from rim_data_analysis.combat_io import modifier_from_dict
from rim_data_analysis.combat_models import (
    ApparelProfile,
    AttackContext,
    CombatAnalysisResult,
    CombatScenario,
    PawnCapacities,
    PawnCombatProfile,
    WeaponProfile,
)
from rim_data_analysis.vanilla_models import VanillaApparelRecord, VanillaCatalog, VanillaWeaponRecord
from rim_data_analysis.vanilla_parser import build_vanilla_catalog


@dataclass(frozen=True, slots=True)
class SpeciesOption:
    id: str
    label: str
    group: str
    can_wear_apparel: bool
    can_use_features: bool
    can_use_weapons: bool
    body_size: float = 1.0
    description: str = ""


@dataclass(frozen=True, slots=True)
class FeatureOption:
    id: str
    label: str
    kind: str
    description: str
    trait_id: str | None = None
    modifier_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class QualityOption:
    id: str
    label: str
    weapon_damage_multiplier: float
    weapon_accuracy_multiplier: float
    weapon_cycle_multiplier: float
    apparel_armor_multiplier: float


@dataclass(frozen=True, slots=True)
class MaterialOption:
    id: str
    label: str
    weapon_damage_multiplier: float
    weapon_armor_penetration_multiplier: float
    apparel_armor_multiplier: float


@dataclass(slots=True)
class EquipmentChoice:
    def_name: str
    label: str
    quality_id: str = "normal"
    material_id: str = "steel"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EquipmentChoice":
        return cls(
            def_name=str(data["def_name"]),
            label=str(data.get("label", data["def_name"])),
            quality_id=str(data.get("quality_id", "normal")),
            material_id=str(data.get("material_id", "steel")),
        )


@dataclass(slots=True)
class SavedPawnTemplate:
    id: str
    name: str
    species_id: str
    feature_ids: list[str] = field(default_factory=list)
    shooting_skill: int = 10
    weapon: EquipmentChoice | None = None
    apparel: list[EquipmentChoice] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "species_id": self.species_id,
            "feature_ids": list(self.feature_ids),
            "shooting_skill": self.shooting_skill,
            "weapon": self.weapon.to_dict() if self.weapon is not None else None,
            "apparel": [item.to_dict() for item in self.apparel],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SavedPawnTemplate":
        weapon_payload = data.get("weapon")
        apparel_payload = data.get("apparel", [])
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            species_id=str(data.get("species_id", "human_baseliner")),
            feature_ids=[str(item) for item in data.get("feature_ids", [])],
            shooting_skill=int(data.get("shooting_skill", 10)),
            weapon=EquipmentChoice.from_dict(weapon_payload) if isinstance(weapon_payload, dict) else None,
            apparel=[
                EquipmentChoice.from_dict(item)
                for item in apparel_payload
                if isinstance(item, dict)
            ],
        )


@dataclass(slots=True)
class SavedScenarioTemplate:
    id: str
    name: str
    attacker_pawn_id: str
    defender_pawn_id: str
    distance_cells: int = 12
    hit_chance_percent: float = 100.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SavedScenarioTemplate":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            attacker_pawn_id=str(data["attacker_pawn_id"]),
            defender_pawn_id=str(data["defender_pawn_id"]),
            distance_cells=int(data.get("distance_cells", 12)),
            hit_chance_percent=float(data.get("hit_chance_percent", 100.0)),
        )


@dataclass(slots=True)
class ImportSettings:
    game_data_root: str = ""
    workshop_root: str = ""
    catalog_weapon_count: int = 0
    catalog_apparel_count: int = 0
    last_imported_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ImportSettings":
        return cls(
            game_data_root=str(data.get("game_data_root", "")),
            workshop_root=str(data.get("workshop_root", "")),
            catalog_weapon_count=int(data.get("catalog_weapon_count", 0)),
            catalog_apparel_count=int(data.get("catalog_apparel_count", 0)),
            last_imported_at=str(data.get("last_imported_at", "")),
        )


@dataclass(slots=True)
class ComparisonRow:
    scenario_id: str
    scenario_name: str
    attacker_name: str
    defender_name: str
    weapon_name: str
    expected_dps: float
    theoretical_dps: float
    hit_chance_percent: float
    expected_damage_on_hit: float
    armor_reduction_percent: float
    damage_taken_multiplier: float
    distance_cells: int
    outfit_valid: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


SPECIES_OPTIONS: list[SpeciesOption] = [
    SpeciesOption(
        id="human_baseliner",
        label="人类",
        group="人种",
        can_wear_apparel=True,
        can_use_features=True,
        can_use_weapons=True,
        description="标准人类模板，支持特性、武器和衣着。",
    ),
    SpeciesOption(
        id="humanlike_xenotype",
        label="类人异种族",
        group="异种族",
        can_wear_apparel=True,
        can_use_features=True,
        can_use_weapons=True,
        description="用于鼠族等基于人类的异种族，当前按类人种处理。",
    ),
    SpeciesOption(
        id="animal_generic",
        label="动物",
        group="动物",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        body_size=1.2,
        description="第一版不开放动物穿戴和复杂特性配置。",
    ),
    SpeciesOption(
        id="mechanoid_generic",
        label="机械族",
        group="机械族",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        body_size=1.15,
        description="第一版按不可着装单位处理。",
    ),
    SpeciesOption(
        id="insectoid_generic",
        label="虫族",
        group="虫族",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        body_size=1.1,
        description="第一版按不可着装单位处理。",
    ),
]

FEATURE_OPTIONS: list[FeatureOption] = [
    FeatureOption(
        id="tough",
        label="坚韧",
        kind="trait",
        trait_id="tough",
        description="降低承受伤害。",
    ),
    FeatureOption(
        id="careful_shooter",
        label="谨慎射手",
        kind="trait",
        trait_id="careful_shooter",
        description="更稳但瞄准更慢。",
    ),
    FeatureOption(
        id="trigger_happy",
        label="乱开枪",
        kind="trait",
        trait_id="trigger_happy",
        description="射速更快，但精度更低。",
    ),
    FeatureOption(
        id="brawler",
        label="斗士",
        kind="trait",
        trait_id="brawler",
        description="提升近战命中。",
    ),
    FeatureOption(
        id="nimble",
        label="灵活",
        kind="trait",
        trait_id="nimble",
        description="提升近战闪避。",
    ),
    FeatureOption(
        id="shooting_specialist",
        label="射击专家",
        kind="modifier",
        description="加入射击专家自身增益。",
        modifier_payload={
            "name": "射击专家自身增益",
            "shooting_skill_offset": 4,
            "shooting_accuracy_multiplier": 1.05,
            "aiming_time_multiplier": 0.9,
        },
    ),
    FeatureOption(
        id="shooting_command",
        label="射击指令",
        kind="modifier",
        description="加入射击指令增益。",
        modifier_payload={
            "name": "射击指令增益",
            "shooting_skill_offset": 6,
            "shooting_accuracy_multiplier": 1.08,
            "aiming_time_multiplier": 0.85,
        },
    ),
]

QUALITY_OPTIONS: list[QualityOption] = [
    QualityOption("awful", "劣质", 0.9, 0.9, 1.08, 0.82),
    QualityOption("poor", "差", 0.95, 0.95, 1.04, 0.9),
    QualityOption("normal", "普通", 1.0, 1.0, 1.0, 1.0),
    QualityOption("good", "良好", 1.02, 1.02, 0.99, 1.06),
    QualityOption("excellent", "优秀", 1.04, 1.04, 0.98, 1.12),
    QualityOption("masterwork", "大师级", 1.08, 1.08, 0.96, 1.24),
    QualityOption("legendary", "传奇", 1.12, 1.12, 0.94, 1.38),
]

MATERIAL_OPTIONS: list[MaterialOption] = [
    MaterialOption("wood", "木材", 0.86, 0.9, 0.6),
    MaterialOption("steel", "钢铁", 1.0, 1.0, 1.0),
    MaterialOption("fiberglass", "玻璃钢", 1.04, 1.02, 1.1),
    MaterialOption("plasteel", "塑钢", 1.08, 1.08, 1.16),
    MaterialOption("uranium", "铀", 1.1, 1.1, 1.04),
    MaterialOption("devilstrand", "恶魔丝", 0.98, 1.0, 1.14),
    MaterialOption("cloth", "布料", 0.92, 0.96, 0.78),
]

SPECIES_BY_ID = {item.id: item for item in SPECIES_OPTIONS}
FEATURE_BY_ID = {item.id: item for item in FEATURE_OPTIONS}
QUALITY_BY_ID = {item.id: item for item in QUALITY_OPTIONS}
MATERIAL_BY_ID = {item.id: item for item in MATERIAL_OPTIONS}


def humanlike_species_ids() -> set[str]:
    return {item.id for item in SPECIES_OPTIONS if item.can_use_weapons}


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    ascii_only = lowered.encode("ascii", errors="ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return normalized or "preset"


def _timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 根节点必须是对象: {path}")
    return payload


class UserAppStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.pawns_dir = self.root / "pawns"
        self.scenarios_dir = self.root / "scenarios"
        self.results_dir = self.root / "results"
        self.settings_dir = self.root / "settings"
        for path in (
            self.root,
            self.pawns_dir,
            self.scenarios_dir,
            self.results_dir,
            self.settings_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def for_repo(cls, repo_root: Path) -> "UserAppStore":
        return cls(repo_root / "artifacts" / "app-state")

    def _pawn_path(self, template_id: str) -> Path:
        return self.pawns_dir / f"{template_id}.json"

    def _scenario_path(self, template_id: str) -> Path:
        return self.scenarios_dir / f"{template_id}.json"

    def _settings_path(self) -> Path:
        return self.settings_dir / "import-settings.json"

    def list_pawns(self) -> list[SavedPawnTemplate]:
        return sorted(
            [SavedPawnTemplate.from_dict(_read_json(path)) for path in self.pawns_dir.glob("*.json")],
            key=lambda item: item.name.lower(),
        )

    def load_pawn(self, template_id: str) -> SavedPawnTemplate:
        return SavedPawnTemplate.from_dict(_read_json(self._pawn_path(template_id)))

    def save_pawn(self, pawn: SavedPawnTemplate) -> SavedPawnTemplate:
        normalized = SavedPawnTemplate(
            id=pawn.id or self.make_id(pawn.name),
            name=pawn.name.strip() or "未命名人物",
            species_id=pawn.species_id,
            feature_ids=list(pawn.feature_ids),
            shooting_skill=max(0, min(int(pawn.shooting_skill), 20)),
            weapon=pawn.weapon,
            apparel=list(pawn.apparel),
        )
        _write_json(self._pawn_path(normalized.id), normalized.to_dict())
        return normalized

    def delete_pawn(self, template_id: str) -> None:
        dependencies = [item for item in self.list_scenarios() if template_id in {item.attacker_pawn_id, item.defender_pawn_id}]
        if dependencies:
            names = "、".join(item.name for item in dependencies[:3])
            raise ValueError(f"该人物已被场景使用：{names}")
        self._pawn_path(template_id).unlink(missing_ok=True)

    def list_scenarios(self) -> list[SavedScenarioTemplate]:
        return sorted(
            [SavedScenarioTemplate.from_dict(_read_json(path)) for path in self.scenarios_dir.glob("*.json")],
            key=lambda item: item.name.lower(),
        )

    def load_scenario(self, template_id: str) -> SavedScenarioTemplate:
        return SavedScenarioTemplate.from_dict(_read_json(self._scenario_path(template_id)))

    def save_scenario(self, scenario: SavedScenarioTemplate) -> SavedScenarioTemplate:
        normalized = SavedScenarioTemplate(
            id=scenario.id or self.make_id(scenario.name),
            name=scenario.name.strip() or "未命名场景",
            attacker_pawn_id=scenario.attacker_pawn_id,
            defender_pawn_id=scenario.defender_pawn_id,
            distance_cells=max(1, int(scenario.distance_cells)),
            hit_chance_percent=max(0.0, min(float(scenario.hit_chance_percent), 200.0)),
        )
        _write_json(self._scenario_path(normalized.id), normalized.to_dict())
        return normalized

    def delete_scenario(self, template_id: str) -> None:
        self._scenario_path(template_id).unlink(missing_ok=True)

    def load_import_settings(self) -> ImportSettings:
        path = self._settings_path()
        if not path.exists():
            return ImportSettings()
        return ImportSettings.from_dict(_read_json(path))

    def save_import_settings(self, settings: ImportSettings) -> ImportSettings:
        normalized = ImportSettings(
            game_data_root=settings.game_data_root.strip(),
            workshop_root=settings.workshop_root.strip(),
            catalog_weapon_count=max(0, int(settings.catalog_weapon_count)),
            catalog_apparel_count=max(0, int(settings.catalog_apparel_count)),
            last_imported_at=settings.last_imported_at.strip(),
        )
        _write_json(self._settings_path(), normalized.to_dict())
        return normalized

    def save_result_rows(self, rows: list[ComparisonRow], *, label: str) -> Path:
        payload = {
            "label": label,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "rows": [row.to_dict() for row in rows],
        }
        output_path = self.results_dir / f"{_timestamp_slug()}-{_slugify(label)}.json"
        _write_json(output_path, payload)
        return output_path

    def make_id(self, name: str) -> str:
        base = _slugify(name)
        candidate = f"{base}-{_timestamp_slug()}"
        return candidate


@dataclass(slots=True)
class CatalogIndex:
    catalog: VanillaCatalog
    weapons_by_def_name: dict[str, VanillaWeaponRecord]
    apparel_by_def_name: dict[str, VanillaApparelRecord]

    @classmethod
    def from_catalog(cls, catalog: VanillaCatalog) -> "CatalogIndex":
        return cls(
            catalog=catalog,
            weapons_by_def_name={item.def_name: item for item in catalog.weapons},
            apparel_by_def_name={item.def_name: item for item in catalog.apparel},
        )

    def search_weapons(self, query: str, *, attack_mode: str | None = None) -> list[VanillaWeaponRecord]:
        normalized = query.strip().lower()
        records = self.catalog.weapons
        if attack_mode and attack_mode != "all":
            records = [item for item in records if item.attack_mode == attack_mode]
        if not normalized:
            return records
        return [
            item
            for item in records
            if normalized in item.label.lower() or normalized in item.def_name.lower()
        ]

    def search_apparel(self, query: str) -> list[VanillaApparelRecord]:
        normalized = query.strip().lower()
        if not normalized:
            return self.catalog.apparel
        return [
            item
            for item in self.catalog.apparel
            if normalized in item.label.lower() or normalized in item.def_name.lower()
        ]


def load_catalog_index(game_data_root: Path) -> CatalogIndex:
    return CatalogIndex.from_catalog(build_vanilla_catalog(game_data_root))


def describe_equipment(choice: EquipmentChoice) -> str:
    quality = QUALITY_BY_ID.get(choice.quality_id, QUALITY_BY_ID["normal"])
    material = MATERIAL_BY_ID.get(choice.material_id, MATERIAL_BY_ID["steel"])
    return f"{quality.label} {material.label} {choice.label}"


def _weapon_profile_from_choice(choice: EquipmentChoice, record: VanillaWeaponRecord) -> WeaponProfile:
    quality = QUALITY_BY_ID.get(choice.quality_id, QUALITY_BY_ID["normal"])
    material = MATERIAL_BY_ID.get(choice.material_id, MATERIAL_BY_ID["steel"])
    base = record.to_weapon_profile()
    return WeaponProfile(
        name=describe_equipment(choice),
        attack_mode=base.attack_mode,
        damage_type=base.damage_type,
        damage=base.damage * quality.weapon_damage_multiplier * material.weapon_damage_multiplier,
        armor_penetration=(
            base.armor_penetration
            * quality.weapon_damage_multiplier
            * material.weapon_armor_penetration_multiplier
        ),
        warmup_seconds=base.warmup_seconds * quality.weapon_cycle_multiplier,
        cooldown_seconds=base.cooldown_seconds * quality.weapon_cycle_multiplier,
        burst_shot_count=base.burst_shot_count,
        burst_shot_interval_seconds=base.burst_shot_interval_seconds,
        accuracy_close=base.accuracy_close * quality.weapon_accuracy_multiplier,
        accuracy_short=base.accuracy_short * quality.weapon_accuracy_multiplier,
        accuracy_medium=base.accuracy_medium * quality.weapon_accuracy_multiplier,
        accuracy_long=base.accuracy_long * quality.weapon_accuracy_multiplier,
    )


def _apparel_profile_from_choice(choice: EquipmentChoice, record: VanillaApparelRecord) -> ApparelProfile:
    quality = QUALITY_BY_ID.get(choice.quality_id, QUALITY_BY_ID["normal"])
    material = MATERIAL_BY_ID.get(choice.material_id, MATERIAL_BY_ID["steel"])
    armor_multiplier = quality.apparel_armor_multiplier * material.apparel_armor_multiplier
    base = record.to_apparel_profile()
    return ApparelProfile(
        name=describe_equipment(choice),
        source=base.source,
        layers=list(base.layers),
        covers=list(base.covers),
        armor_sharp=base.armor_sharp * armor_multiplier,
        armor_blunt=base.armor_blunt * armor_multiplier,
        armor_heat=base.armor_heat * armor_multiplier,
        layer_priority_override=base.layer_priority_override,
    )


def build_pawn_profile(
    pawn: SavedPawnTemplate,
    catalog_index: CatalogIndex,
) -> tuple[PawnCombatProfile, WeaponProfile | None]:
    species = SPECIES_BY_ID.get(pawn.species_id, SPECIES_BY_ID["human_baseliner"])
    traits: list[str] = []
    modifiers = []
    for feature_id in pawn.feature_ids:
        feature = FEATURE_BY_ID.get(feature_id)
        if feature is None:
            continue
        if feature.kind == "trait" and feature.trait_id:
            traits.append(feature.trait_id)
            continue
        if feature.kind == "modifier" and feature.modifier_payload is not None:
            modifiers.append(modifier_from_dict(feature.modifier_payload))

    apparel_profiles: list[ApparelProfile] = []
    weapon_profile: WeaponProfile | None = None
    if species.can_wear_apparel:
        for choice in pawn.apparel:
            record = catalog_index.apparel_by_def_name.get(choice.def_name)
            if record is None:
                continue
            apparel_profiles.append(_apparel_profile_from_choice(choice, record))

    if species.can_use_weapons and pawn.weapon is not None:
        record = catalog_index.weapons_by_def_name.get(pawn.weapon.def_name)
        if record is not None:
            weapon_profile = _weapon_profile_from_choice(pawn.weapon, record)

    profile = PawnCombatProfile(
        name=pawn.name,
        species=species.id,
        shooting_skill=max(0, min(int(pawn.shooting_skill), 20)),
        melee_skill=max(0, min(int(pawn.shooting_skill), 20)),
        body_size=species.body_size,
        capacities=PawnCapacities(),
        traits=traits if species.can_use_features else [],
        modifiers=modifiers if species.can_use_features else [],
        apparel=apparel_profiles,
    )
    return profile, weapon_profile


def build_analysis_for_saved_scenario(
    scenario: SavedScenarioTemplate,
    pawns_by_id: dict[str, SavedPawnTemplate],
    catalog_index: CatalogIndex,
) -> tuple[CombatAnalysisResult, ComparisonRow]:
    attacker_template = pawns_by_id.get(scenario.attacker_pawn_id)
    defender_template = pawns_by_id.get(scenario.defender_pawn_id)
    if attacker_template is None:
        raise ValueError("未找到攻击方人物模板。")
    if defender_template is None:
        raise ValueError("未找到防守方人物模板。")

    attacker_profile, weapon_profile = build_pawn_profile(attacker_template, catalog_index)
    defender_profile, _ = build_pawn_profile(defender_template, catalog_index)
    if weapon_profile is None:
        raise ValueError("攻击方还没有选择武器，无法计算场景。")

    combat_scenario = CombatScenario(
        name=scenario.name,
        attacker=attacker_profile,
        defender=defender_profile,
        weapon=weapon_profile,
        context=AttackContext(
            distance_cells=max(1, int(scenario.distance_cells)),
            target_body_region="Torso",
            target_is_aiming_or_firing=False,
            hit_chance_multiplier=max(0.0, min(float(scenario.hit_chance_percent) / 100.0, 2.0)),
            cover_block_chance=0.0,
        ),
    )
    analysis = analyze_scenario(combat_scenario)
    row = ComparisonRow(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        attacker_name=attacker_template.name,
        defender_name=defender_template.name,
        weapon_name=weapon_profile.name,
        expected_dps=analysis.damage.expected_dps,
        theoretical_dps=analysis.damage.theoretical_dps,
        hit_chance_percent=analysis.accuracy.final_hit_chance * 100.0,
        expected_damage_on_hit=analysis.damage.expected_damage_on_hit_after_defense,
        armor_reduction_percent=analysis.armor.reduction_rate_from_armor * 100.0,
        damage_taken_multiplier=analysis.armor.total_damage_taken_multiplier,
        distance_cells=scenario.distance_cells,
        outfit_valid=analysis.can_wear_outfit,
    )
    return analysis, row
