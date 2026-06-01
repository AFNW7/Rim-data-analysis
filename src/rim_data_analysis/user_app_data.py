from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from math import prod
from pathlib import Path
from uuid import uuid4

from rim_data_analysis.combat_engine import (
    analyze_scenario,
    compute_aiming_time_multiplier,
    compute_ranged_cooldown_multiplier,
)
from rim_data_analysis.combat_io import modifier_from_dict
from rim_data_analysis.combat_models import (
    ApparelProfile,
    AttackContext,
    CombatAnalysisResult,
    CombatStatModifier,
    CombatScenario,
    MeleeAttackOption,
    PawnCapacities,
    PawnCombatProfile,
    WeaponProfile,
)
from rim_data_analysis.vanilla_models import (
    VanillaApparelRecord,
    VanillaCatalog,
    VanillaImplantRecord,
    VanillaWeaponRecord,
)
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
    default_full_body_armor_percent: float = 0.0


@dataclass(frozen=True, slots=True)
class FeatureOption:
    id: str
    label: str
    kind: str
    description: str
    trait_id: str | None = None
    modifier_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class EnhancementOption:
    id: str
    label: str
    description: str
    modifier_payload: dict[str, object]
    source: str = "custom"
    linked_implant_def_name: str | None = None


@dataclass(frozen=True, slots=True)
class QualityOption:
    id: str
    label: str
    weapon_damage_multiplier: float
    weapon_accuracy_multiplier: float
    weapon_cycle_multiplier: float
    apparel_sharp_multiplier: float
    apparel_blunt_multiplier: float
    apparel_heat_multiplier: float


@dataclass(frozen=True, slots=True)
class MaterialOption:
    id: str
    label: str
    weapon_damage_multiplier: float
    weapon_armor_penetration_multiplier: float
    apparel_sharp_power: float
    apparel_blunt_power: float
    apparel_heat_power: float


@dataclass(frozen=True, slots=True)
class WeaponQualityRule:
    melee_damage_multiplier: float
    melee_armor_penetration_multiplier: float
    ranged_accuracy_multiplier: float
    ranged_damage_multiplier: float
    ranged_armor_penetration_multiplier: float


@dataclass(slots=True)
class EquipmentChoice:
    def_name: str
    label: str
    quality_id: str = "normal"
    material_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EquipmentChoice":
        return cls(
            def_name=str(data["def_name"]),
            label=str(data.get("label", data["def_name"])),
            quality_id=str(data.get("quality_id", "normal")),
            material_id=(
                str(data["material_id"])
                if data.get("material_id") not in {None, "", "none"}
                else None
            ),
        )


@dataclass(slots=True)
class SavedPawnTemplate:
    id: str
    name: str
    species_id: str
    feature_ids: list[str] = field(default_factory=list)
    support_gear_ids: list[str] = field(default_factory=list)
    implant_ids: list[str] = field(default_factory=list)
    shooting_skill: int = 10
    melee_skill: int = 10
    full_body_armor_percent: float = 0.0
    weapon: EquipmentChoice | None = None
    apparel: list[EquipmentChoice] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "species_id": self.species_id,
            "feature_ids": list(self.feature_ids),
            "support_gear_ids": list(self.support_gear_ids),
            "implant_ids": list(self.implant_ids),
            "shooting_skill": self.shooting_skill,
            "melee_skill": self.melee_skill,
            "full_body_armor_percent": self.full_body_armor_percent,
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
            support_gear_ids=[str(item) for item in data.get("support_gear_ids", [])],
            implant_ids=[str(item) for item in data.get("implant_ids", [])],
            shooting_skill=int(data.get("shooting_skill", 10)),
            melee_skill=int(data.get("melee_skill", 10)),
            full_body_armor_percent=float(data.get("full_body_armor_percent", 0.0)),
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
    catalog_implant_count: int = 0
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
            catalog_implant_count=int(data.get("catalog_implant_count", 0)),
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


@dataclass(frozen=True, slots=True)
class FirepowerPreviewTarget:
    label: str
    armor_percent: float
    expected_dps: float
    ratio_to_unarmored: float


@dataclass(frozen=True, slots=True)
class FirepowerPreview:
    weapon_name: str
    best_distance_label: str
    best_distance_cells: int
    final_hit_percent: float
    base_warmup_seconds: float
    actual_warmup_seconds: float
    base_cooldown_seconds: float
    actual_cooldown_seconds: float
    theoretical_dps: float
    targets: list[FirepowerPreviewTarget]


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
        id="armor_dummy_unarmored",
        label="无甲模板",
        group="护甲模板",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        description="快速生成 0% 全身护甲测试靶子。",
        default_full_body_armor_percent=0.0,
    ),
    SpeciesOption(
        id="armor_dummy_light",
        label="轻甲模板",
        group="护甲模板",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        description="快速生成 20% 全身护甲测试靶子。",
        default_full_body_armor_percent=20.0,
    ),
    SpeciesOption(
        id="armor_dummy_medium",
        label="中甲模板",
        group="护甲模板",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        description="快速生成 40% 全身护甲测试靶子。",
        default_full_body_armor_percent=40.0,
    ),
    SpeciesOption(
        id="armor_dummy_heavy",
        label="重甲模板",
        group="护甲模板",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        description="快速生成 70% 全身护甲测试靶子。",
        default_full_body_armor_percent=70.0,
    ),
    SpeciesOption(
        id="armor_dummy_ultra",
        label="超重甲模板",
        group="护甲模板",
        can_wear_apparel=False,
        can_use_features=False,
        can_use_weapons=False,
        description="快速生成 100% 全身护甲测试靶子。",
        default_full_body_armor_percent=100.0,
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
            "shooting_accuracy_stat_offset": 7,
            "aiming_time_stat_offset": -0.5,
        },
    ),
    FeatureOption(
        id="shooting_command",
        label="射击指令",
        kind="modifier",
        description="加入射击指令增益。",
        modifier_payload={
            "name": "射击指令增益",
            "shooting_accuracy_stat_offset": 4,
            "aiming_time_stat_offset": -0.4,
        },
    ),
]

SUPPORT_GEAR_OPTIONS: list[EnhancementOption] = [
    EnhancementOption(
        id="heavy_ammo_harness",
        label="重型弹药带挎包",
        description="原版 heavy bandolier，减少 20% 远程冷却。",
        modifier_payload={
            "name": "重型弹药带挎包",
            "ranged_cooldown_stat_offset": -0.2,
        },
        source="vanilla",
    ),
]

IMPLANT_OPTIONS: list[EnhancementOption] = [
    EnhancementOption(
        id="bionic_eye",
        label="仿生眼",
        description="原版仿生眼。导入游戏数据后按眼部部件效率参与整体视觉能力计算。",
        modifier_payload={
            "name": "仿生眼",
            "sight_multiplier": 1.1875,
        },
        source="vanilla",
        linked_implant_def_name="Implant_BionicEye",
    ),
    EnhancementOption(
        id="archotech_eye",
        label="超凡仿生眼",
        description="原版超凡仿生眼。导入游戏数据后按眼部部件效率参与整体视觉能力计算，并保留原始额外射击修正。",
        modifier_payload={
            "name": "超凡仿生眼",
            "sight_multiplier": 1.375,
            "shooting_accuracy_multiplier": 1.04,
        },
        source="vanilla",
        linked_implant_def_name="Implant_ArchotechEye",
    ),
    EnhancementOption(
        id="bionic_arm",
        label="仿生臂",
        description="原版仿生臂。导入游戏数据后按手臂部件效率参与整体操作能力计算。",
        modifier_payload={
            "name": "仿生臂",
            "manipulation_multiplier": 1.1,
        },
        source="vanilla",
        linked_implant_def_name="Implant_BionicArm",
    ),
]

QUALITY_OPTIONS: list[QualityOption] = [
    QualityOption("awful", "极差", 0.9, 0.9, 1.08, 0.60, 0.60, 0.60),
    QualityOption("poor", "较差", 0.95, 0.95, 1.04, 0.80, 0.80, 0.80),
    QualityOption("normal", "一般", 1.0, 1.0, 1.0, 1.00, 1.00, 1.00),
    QualityOption("good", "良好", 1.02, 1.02, 0.99, 1.15, 1.15, 1.15),
    QualityOption("excellent", "极佳", 1.04, 1.04, 0.98, 1.30, 1.30, 1.30),
    QualityOption("masterwork", "大师", 1.08, 1.08, 0.96, 1.45, 1.45, 1.45),
    QualityOption("legendary", "传奇", 1.12, 1.12, 0.94, 1.80, 1.80, 1.80),
]

MATERIAL_OPTIONS: list[MaterialOption] = [
    MaterialOption("wood", "木材", 0.86, 0.9, 0.54, 0.54, 0.40),
    MaterialOption("steel", "钢铁", 1.0, 1.0, 0.90, 0.45, 0.60),
    MaterialOption("fiberglass", "玻璃钢", 1.04, 1.02, 1.00, 0.50, 0.75),
    MaterialOption("plasteel", "塑钢", 1.08, 1.08, 1.14, 0.55, 0.65),
    MaterialOption("uranium", "铀", 1.1, 1.1, 1.08, 0.54, 0.65),
    MaterialOption("devilstrand", "恶魔丝", 0.98, 1.0, 1.40, 0.36, 3.00),
    MaterialOption("cloth", "布料", 0.92, 0.96, 0.36, 0.00, 0.18),
]

SPECIES_BY_ID = {item.id: item for item in SPECIES_OPTIONS}
FEATURE_BY_ID = {item.id: item for item in FEATURE_OPTIONS}
SUPPORT_GEAR_BY_ID = {item.id: item for item in SUPPORT_GEAR_OPTIONS}
IMPLANT_BY_ID = {item.id: item for item in IMPLANT_OPTIONS}
QUALITY_BY_ID = {item.id: item for item in QUALITY_OPTIONS}
MATERIAL_BY_ID = {item.id: item for item in MATERIAL_OPTIONS}
WEAPON_QUALITY_RULES_BY_ID = {
    "awful": WeaponQualityRule(0.80, 0.80, 0.80, 0.90, 0.90),
    "poor": WeaponQualityRule(0.90, 0.90, 0.90, 1.00, 1.00),
    "normal": WeaponQualityRule(1.00, 1.00, 1.00, 1.00, 1.00),
    "good": WeaponQualityRule(1.10, 1.10, 1.10, 1.00, 1.00),
    "excellent": WeaponQualityRule(1.20, 1.20, 1.20, 1.00, 1.00),
    "masterwork": WeaponQualityRule(1.45, 1.45, 1.35, 1.25, 1.25),
    "legendary": WeaponQualityRule(1.65, 1.65, 1.50, 1.50, 1.50),
}
FULL_BODY_ARMOR_COVERS = ["Torso", "Arms", "Legs", "Head", "Neck", "Hands", "Feet"]

REFERENCE_ARMOR_TARGETS: list[tuple[str, float]] = [
    ("0% 无甲参考", 0.0),
    ("20% 轻甲参考", 20.0),
    ("40% 中甲参考", 40.0),
    ("70% 重甲参考", 70.0),
    ("100% 极重甲参考", 100.0),
]

RANGED_PREVIEW_DISTANCE_CHOICES: list[tuple[int, str]] = [
    (3, "贴近"),
    (12, "近"),
    (25, "中"),
    (40, "远"),
]


def humanlike_species_ids() -> set[str]:
    return {item.id for item in SPECIES_OPTIONS if item.can_use_weapons}


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    ascii_only = lowered.encode("ascii", errors="ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return normalized or "preset"


def _timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _nonce_slug() -> str:
    return uuid4().hex[:8]


def _normalize_distance_cells(value: int | float) -> int:
    return max(1, int(value))


def _normalize_hit_chance_percent(value: int | float) -> float:
    return round(max(0.0, min(float(value), 200.0)), 6)


def _scenario_signature(
    attacker_pawn_id: str,
    defender_pawn_id: str,
    distance_cells: int | float,
    hit_chance_percent: int | float,
) -> tuple[str, str, int, float]:
    return (
        str(attacker_pawn_id),
        str(defender_pawn_id),
        _normalize_distance_cells(distance_cells),
        _normalize_hit_chance_percent(hit_chance_percent),
    )


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
            support_gear_ids=list(pawn.support_gear_ids),
            implant_ids=list(pawn.implant_ids),
            shooting_skill=max(0, min(int(pawn.shooting_skill), 20)),
            melee_skill=max(0, min(int(pawn.melee_skill), 20)),
            full_body_armor_percent=max(0.0, min(float(pawn.full_body_armor_percent), 200.0)),
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

    def scenario_signature(self, scenario: SavedScenarioTemplate) -> tuple[str, str, int, float]:
        return _scenario_signature(
            scenario.attacker_pawn_id,
            scenario.defender_pawn_id,
            scenario.distance_cells,
            scenario.hit_chance_percent,
        )

    def find_scenario_by_signature(
        self,
        *,
        attacker_pawn_id: str,
        defender_pawn_id: str,
        distance_cells: int | float,
        hit_chance_percent: int | float,
        exclude_id: str | None = None,
    ) -> SavedScenarioTemplate | None:
        expected = _scenario_signature(
            attacker_pawn_id,
            defender_pawn_id,
            distance_cells,
            hit_chance_percent,
        )
        for item in self.list_scenarios():
            if exclude_id is not None and item.id == exclude_id:
                continue
            if self.scenario_signature(item) == expected:
                return item
        return None

    def save_scenario(self, scenario: SavedScenarioTemplate) -> SavedScenarioTemplate:
        normalized = SavedScenarioTemplate(
            id=scenario.id or self.make_id(scenario.name),
            name=scenario.name.strip() or "未命名场景",
            attacker_pawn_id=scenario.attacker_pawn_id,
            defender_pawn_id=scenario.defender_pawn_id,
            distance_cells=_normalize_distance_cells(scenario.distance_cells),
            hit_chance_percent=_normalize_hit_chance_percent(scenario.hit_chance_percent),
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
            catalog_implant_count=max(0, int(settings.catalog_implant_count)),
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
        output_path = self.results_dir / f"{_timestamp_slug()}-{_slugify(label)}-{_nonce_slug()}.json"
        _write_json(output_path, payload)
        return output_path

    def make_id(self, name: str) -> str:
        base = _slugify(name)
        candidate = f"{base}-{_timestamp_slug()}-{_nonce_slug()}"
        return candidate


@dataclass(slots=True)
class CatalogIndex:
    catalog: VanillaCatalog
    weapons_by_def_name: dict[str, VanillaWeaponRecord]
    apparel_by_def_name: dict[str, VanillaApparelRecord]
    implants_by_def_name: dict[str, VanillaImplantRecord]

    @classmethod
    def from_catalog(cls, catalog: VanillaCatalog) -> "CatalogIndex":
        return cls(
            catalog=catalog,
            weapons_by_def_name={item.def_name: item for item in catalog.weapons},
            apparel_by_def_name={item.def_name: item for item in catalog.apparel},
            implants_by_def_name={item.def_name: item for item in catalog.implants},
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
            if normalized in item.label.lower()
            or normalized in item.display_label.lower()
            or normalized in item.def_name.lower()
        ]

    def search_apparel(self, query: str) -> list[VanillaApparelRecord]:
        normalized = query.strip().lower()
        if not normalized:
            return self.catalog.apparel
        return [
            item
            for item in self.catalog.apparel
            if normalized in item.label.lower()
            or normalized in item.display_label.lower()
            or normalized in item.def_name.lower()
        ]

    def search_implants(self, query: str) -> list[VanillaImplantRecord]:
        normalized = query.strip().lower()
        if not normalized:
            return self.catalog.implants
        return [
            item
            for item in self.catalog.implants
            if normalized in item.label.lower()
            or normalized in item.display_label.lower()
            or normalized in item.def_name.lower()
        ]


def load_catalog_index(game_data_root: Path) -> CatalogIndex:
    return CatalogIndex.from_catalog(build_vanilla_catalog(game_data_root))


def describe_equipment(choice: EquipmentChoice, *, supports_material: bool = True) -> str:
    quality = QUALITY_BY_ID.get(choice.quality_id, QUALITY_BY_ID["normal"])
    if not supports_material or not choice.material_id:
        return f"{quality.label} {choice.label}"
    material = MATERIAL_BY_ID.get(choice.material_id, MATERIAL_BY_ID["steel"])
    return f"{quality.label} {material.label} {choice.label}"


def describe_modifier_payload(modifier_payload: dict[str, object] | None) -> list[str]:
    if modifier_payload is None:
        return []

    lines: list[str] = []

    def _float(key: str, default: float = 0.0) -> float:
        value = modifier_payload.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    skill_offset = _float("shooting_skill_offset")
    if skill_offset:
        lines.append(f"射击等级 {'+' if skill_offset > 0 else ''}{skill_offset:.0f}")

    accuracy_stat = _float("shooting_accuracy_stat_offset")
    if accuracy_stat:
        lines.append(f"射击精度 {'+' if accuracy_stat > 0 else ''}{accuracy_stat:.0f}")

    accuracy_mult = _float("shooting_accuracy_multiplier", 1.0)
    if abs(accuracy_mult - 1.0) > 1e-9:
        lines.append(f"射击精度倍率 {accuracy_mult:.2f}x")

    accuracy_per_tile = _float("shooting_accuracy_per_tile_offset")
    if accuracy_per_tile:
        lines.append(f"每格精度 {'+' if accuracy_per_tile > 0 else ''}{accuracy_per_tile:.4f}")

    aiming_stat = _float("aiming_time_stat_offset")
    if aiming_stat:
        lines.append(f"瞄准时间 {'-' if aiming_stat < 0 else '+'}{abs(aiming_stat) * 100:.0f}%")

    aiming_mult = _float("aiming_time_multiplier", 1.0)
    if abs(aiming_mult - 1.0) > 1e-9:
        lines.append(f"瞄准时间倍率 {aiming_mult:.2f}x")

    cooldown_stat = _float("ranged_cooldown_stat_offset")
    if cooldown_stat:
        lines.append(f"远程冷却 {'-' if cooldown_stat < 0 else '+'}{abs(cooldown_stat) * 100:.0f}%")

    cooldown_mult = _float("ranged_cooldown_multiplier", 1.0)
    if abs(cooldown_mult - 1.0) > 1e-9:
        lines.append(f"远程冷却倍率 {cooldown_mult:.2f}x")

    sight_offset = _float("sight_offset")
    if sight_offset:
        lines.append(f"视觉能力 {'+' if sight_offset > 0 else ''}{sight_offset * 100:.0f}%")

    sight_mult = _float("sight_multiplier", 1.0)
    if abs(sight_mult - 1.0) > 1e-9:
        lines.append(f"视觉能力倍率 {sight_mult:.2f}x")

    manipulation_offset = _float("manipulation_offset")
    if manipulation_offset:
        lines.append(f"操作能力 {'+' if manipulation_offset > 0 else ''}{manipulation_offset * 100:.0f}%")

    manipulation_mult = _float("manipulation_multiplier", 1.0)
    if abs(manipulation_mult - 1.0) > 1e-9:
        lines.append(f"操作能力倍率 {manipulation_mult:.2f}x")

    moving_offset = _float("moving_offset")
    if moving_offset:
        lines.append(f"移动能力 {'+' if moving_offset > 0 else ''}{moving_offset * 100:.0f}%")

    moving_mult = _float("moving_multiplier", 1.0)
    if abs(moving_mult - 1.0) > 1e-9:
        lines.append(f"移动能力倍率 {moving_mult:.2f}x")

    return lines


def _weapon_profile_from_choice(choice: EquipmentChoice, record: VanillaWeaponRecord) -> WeaponProfile:
    rule = WEAPON_QUALITY_RULES_BY_ID.get(choice.quality_id, WEAPON_QUALITY_RULES_BY_ID["normal"])
    material = (
        MATERIAL_BY_ID.get(choice.material_id, MATERIAL_BY_ID["steel"])
        if record.supports_material and choice.material_id
        else MATERIAL_BY_ID["steel"]
    )
    base = record.to_weapon_profile()
    if base.attack_mode == "melee":
        damage = base.damage * rule.melee_damage_multiplier * material.weapon_damage_multiplier
        armor_penetration = (
            base.armor_penetration
            * rule.melee_armor_penetration_multiplier
            * material.weapon_armor_penetration_multiplier
        )
        melee_attack_options = [
            MeleeAttackOption(
                label=option.label,
                damage_type=option.damage_type,
                damage=option.damage * rule.melee_damage_multiplier * material.weapon_damage_multiplier,
                armor_penetration=(
                    option.armor_penetration
                    * rule.melee_armor_penetration_multiplier
                    * material.weapon_armor_penetration_multiplier
                ),
                cooldown_seconds=option.cooldown_seconds,
                chance_factor=option.chance_factor,
                capacities=list(option.capacities),
            )
            for option in base.melee_attack_options
        ]
        accuracy_close = base.accuracy_close
        accuracy_short = base.accuracy_short
        accuracy_medium = base.accuracy_medium
        accuracy_long = base.accuracy_long
    else:
        damage = base.damage * rule.ranged_damage_multiplier * material.weapon_damage_multiplier
        armor_penetration = (
            base.armor_penetration
            * rule.ranged_armor_penetration_multiplier
            * material.weapon_armor_penetration_multiplier
        )
        accuracy_close = min(base.accuracy_close * rule.ranged_accuracy_multiplier, 1.0)
        accuracy_short = min(base.accuracy_short * rule.ranged_accuracy_multiplier, 1.0)
        accuracy_medium = min(base.accuracy_medium * rule.ranged_accuracy_multiplier, 1.0)
        accuracy_long = min(base.accuracy_long * rule.ranged_accuracy_multiplier, 1.0)
        melee_attack_options = []
    return WeaponProfile(
        name=describe_equipment(choice, supports_material=record.supports_material),
        attack_mode=base.attack_mode,
        damage_type=base.damage_type,
        damage=damage,
        armor_penetration=armor_penetration,
        warmup_seconds=base.warmup_seconds,
        cooldown_seconds=base.cooldown_seconds,
        burst_shot_count=base.burst_shot_count,
        burst_shot_interval_seconds=base.burst_shot_interval_seconds,
        accuracy_close=accuracy_close,
        accuracy_short=accuracy_short,
        accuracy_medium=accuracy_medium,
        accuracy_long=accuracy_long,
        melee_attack_options=melee_attack_options,
    )


def _apparel_profile_from_choice(choice: EquipmentChoice, record: VanillaApparelRecord) -> ApparelProfile:
    quality = QUALITY_BY_ID.get(choice.quality_id, QUALITY_BY_ID["normal"])
    material = (
        MATERIAL_BY_ID.get(choice.material_id, MATERIAL_BY_ID["steel"])
        if record.supports_material and choice.material_id
        else MATERIAL_BY_ID["steel"]
    )
    base = record.to_apparel_profile()
    if record.supports_material:
        sharp_base = base.armor_sharp + record.stuff_armor_multiplier * material.apparel_sharp_power
        blunt_base = base.armor_blunt + record.stuff_armor_multiplier * material.apparel_blunt_power
        heat_base = base.armor_heat + record.stuff_armor_multiplier * material.apparel_heat_power
    else:
        sharp_base = base.armor_sharp
        blunt_base = base.armor_blunt
        heat_base = base.armor_heat
    return ApparelProfile(
        name=describe_equipment(choice, supports_material=record.supports_material),
        source=base.source,
        layers=list(base.layers),
        covers=list(base.covers),
        armor_sharp=sharp_base * quality.apparel_sharp_multiplier,
        armor_blunt=blunt_base * quality.apparel_blunt_multiplier,
        armor_heat=heat_base * quality.apparel_heat_multiplier,
        layer_priority_override=base.layer_priority_override,
    )


def _apparel_modifier_from_choice(choice: EquipmentChoice, record: VanillaApparelRecord):
    modifier = record.to_modifier()
    if modifier is None:
        return None
    return modifier


def _implant_modifier_from_record(record: VanillaImplantRecord) -> CombatStatModifier | None:
    return record.to_modifier()


def _capacity_value(
    base_value: float,
    modifiers: list[object],
    *,
    offset_attr: str,
    multiplier_attr: str,
) -> float:
    offset = sum(float(getattr(modifier, offset_attr, 0.0)) for modifier in modifiers)
    multiplier = prod(float(getattr(modifier, multiplier_attr, 1.0)) for modifier in modifiers) if modifiers else 1.0
    return max((base_value + offset) * multiplier, 0.01)


def _body_part_capacity_base(implant_records: list[VanillaImplantRecord], body_part_hint: str) -> float:
    part_efficiencies = sorted(
        (record.part_efficiency for record in implant_records if record.body_part_hint == body_part_hint and record.part_efficiency > 0),
        reverse=True,
    )
    if not part_efficiencies:
        return 1.0
    if body_part_hint == "Eye":
        left, right = (part_efficiencies + [1.0, 1.0])[:2]
        better = max(left, right)
        worse = min(left, right)
        return max(better * 0.75 + worse * 0.25, 0.01)
    primary, secondary = (part_efficiencies + [1.0, 1.0])[:2]
    return max((primary + secondary) / 2.0, 0.01)


def _build_capacities_from_sources(
    modifiers: list[object],
    implant_records: list[VanillaImplantRecord],
) -> PawnCapacities:
    return PawnCapacities(
        sight=_capacity_value(
            _body_part_capacity_base(implant_records, "Eye"),
            modifiers,
            offset_attr="sight_offset",
            multiplier_attr="sight_multiplier",
        ),
        manipulation=_capacity_value(
            _body_part_capacity_base(implant_records, "Arm"),
            modifiers,
            offset_attr="manipulation_offset",
            multiplier_attr="manipulation_multiplier",
        ),
        moving=_capacity_value(
            _body_part_capacity_base(implant_records, "Leg"),
            modifiers,
            offset_attr="moving_offset",
            multiplier_attr="moving_multiplier",
        ),
    )


def build_pawn_profile(
    pawn: SavedPawnTemplate,
    catalog_index: CatalogIndex,
) -> tuple[PawnCombatProfile, WeaponProfile | None]:
    species = SPECIES_BY_ID.get(pawn.species_id, SPECIES_BY_ID["human_baseliner"])
    traits: list[str] = []
    modifiers = []
    implant_records: list[VanillaImplantRecord] = []
    for feature_id in pawn.feature_ids:
        feature = FEATURE_BY_ID.get(feature_id)
        if feature is None:
            continue
        if feature.kind == "trait" and feature.trait_id:
            traits.append(feature.trait_id)
            continue
        if feature.kind == "modifier" and feature.modifier_payload is not None:
            modifiers.append(modifier_from_dict(feature.modifier_payload))
    if species.can_use_weapons:
        for support_gear_id in pawn.support_gear_ids:
            option = SUPPORT_GEAR_BY_ID.get(support_gear_id)
            if option is not None:
                modifiers.append(modifier_from_dict(option.modifier_payload))
        for implant_id in pawn.implant_ids:
            option = IMPLANT_BY_ID.get(implant_id)
            implant_record = None
            if option is not None and option.linked_implant_def_name:
                implant_record = catalog_index.implants_by_def_name.get(option.linked_implant_def_name)
            if implant_record is None and option is None:
                implant_record = catalog_index.implants_by_def_name.get(implant_id)
            if implant_record is not None:
                implant_records.append(implant_record)
                implant_modifier = _implant_modifier_from_record(implant_record)
                if implant_modifier is not None:
                    modifiers.append(implant_modifier)
                continue
            if option is not None:
                modifiers.append(modifier_from_dict(option.modifier_payload))

    apparel_profiles: list[ApparelProfile] = []
    weapon_profile: WeaponProfile | None = None
    if pawn.full_body_armor_percent > 0:
        apparel_profiles.append(
            ApparelProfile(
                name=f"全身护甲 {pawn.full_body_armor_percent:.0f}%",
                source="quick-armor",
                layers=["QuickArmor"],
                covers=list(FULL_BODY_ARMOR_COVERS),
                armor_sharp=pawn.full_body_armor_percent,
                armor_blunt=pawn.full_body_armor_percent,
                armor_heat=pawn.full_body_armor_percent,
                layer_priority_override=100,
            )
        )
    if species.can_wear_apparel:
        for choice in pawn.apparel:
            record = catalog_index.apparel_by_def_name.get(choice.def_name)
            if record is None:
                continue
            apparel_profiles.append(_apparel_profile_from_choice(choice, record))
            apparel_modifier = _apparel_modifier_from_choice(choice, record)
            if apparel_modifier is not None and species.can_use_weapons:
                modifiers.append(apparel_modifier)

    if species.can_use_weapons and pawn.weapon is not None:
        record = catalog_index.weapons_by_def_name.get(pawn.weapon.def_name)
        if record is not None:
            weapon_profile = _weapon_profile_from_choice(pawn.weapon, record)

    profile = PawnCombatProfile(
        name=pawn.name,
        species=species.id,
        shooting_skill=max(0, min(int(pawn.shooting_skill), 20)),
        melee_skill=max(0, min(int(pawn.melee_skill), 20)),
        body_size=species.body_size,
        capacities=_build_capacities_from_sources(modifiers, implant_records) if species.can_use_weapons else PawnCapacities(),
        traits=traits if species.can_use_features else [],
        modifiers=modifiers if species.can_use_weapons else [],
        apparel=apparel_profiles,
    )
    return profile, weapon_profile


def _reference_defender(label: str, armor_percent: float) -> PawnCombatProfile:
    apparel: list[ApparelProfile] = []
    if armor_percent > 0:
        apparel.append(
            ApparelProfile(
                name=f"{label} 护甲层",
                source="preview",
                layers=["QuickArmor"],
                covers=list(FULL_BODY_ARMOR_COVERS),
                armor_sharp=armor_percent,
                armor_blunt=armor_percent,
                armor_heat=armor_percent,
                layer_priority_override=100,
            )
        )
    return PawnCombatProfile(
        name=label,
        species="human_baseliner",
        shooting_skill=0,
        melee_skill=0,
        body_size=1.0,
        capacities=PawnCapacities(),
        apparel=apparel,
    )


def _preview_scenario(
    pawn_name: str,
    attacker: PawnCombatProfile,
    defender: PawnCombatProfile,
    weapon: WeaponProfile,
    distance_cells: int,
) -> CombatScenario:
    return CombatScenario(
        name=pawn_name,
        attacker=attacker,
        defender=defender,
        weapon=weapon,
        context=AttackContext(
            distance_cells=max(1, distance_cells),
            target_body_region="Torso",
            target_is_aiming_or_firing=False,
            hit_chance_multiplier=1.0,
            cover_block_chance=0.0,
        ),
    )


def _format_preview_distance_label(distance_name: str, distance_cells: int) -> str:
    return f"{distance_name}\n{distance_cells}格"


def build_firepower_preview_for_pawn(
    pawn: SavedPawnTemplate,
    catalog_index: CatalogIndex,
) -> FirepowerPreview:
    attacker_profile, weapon_profile = build_pawn_profile(pawn, catalog_index)
    if weapon_profile is None:
        raise ValueError("请先为当前人物选择武器，才能查看实时输出能力。")

    distance_choices = (
        [(1, "近战")]
        if weapon_profile.attack_mode != "ranged"
        else RANGED_PREVIEW_DISTANCE_CHOICES
    )
    unarmored_target = _reference_defender("0% 无甲参考", 0.0)
    best_distance_cells = distance_choices[0][0]
    best_distance_name = distance_choices[0][1]
    best_hit = -1.0
    best_expected_dps = -1.0
    best_analysis: CombatAnalysisResult | None = None

    for distance_cells, distance_name in distance_choices:
        analysis = analyze_scenario(
            _preview_scenario(
                pawn_name=f"{pawn.name} 预览",
                attacker=attacker_profile,
                defender=unarmored_target,
                weapon=weapon_profile,
                distance_cells=distance_cells,
            )
        )
        current_hit = analysis.accuracy.final_hit_chance
        current_expected_dps = analysis.damage.expected_dps
        if (
            current_hit > best_hit
            or (abs(current_hit - best_hit) <= 1e-9 and current_expected_dps > best_expected_dps)
        ):
            best_distance_cells = distance_cells
            best_distance_name = distance_name
            best_hit = current_hit
            best_expected_dps = current_expected_dps
            best_analysis = analysis

    if best_analysis is None:
        raise ValueError("无法根据当前人物配置生成实时预览。")

    targets: list[FirepowerPreviewTarget] = []
    baseline_dps = 0.0
    for index, (label, armor_percent) in enumerate(REFERENCE_ARMOR_TARGETS):
        defender = _reference_defender(label, armor_percent)
        analysis = analyze_scenario(
            _preview_scenario(
                pawn_name=f"{pawn.name} VS {label}",
                attacker=attacker_profile,
                defender=defender,
                weapon=weapon_profile,
                distance_cells=best_distance_cells,
            )
        )
        expected_dps = analysis.damage.expected_dps
        if index == 0:
            baseline_dps = expected_dps
        ratio = 0.0 if baseline_dps <= 0 else expected_dps / baseline_dps
        targets.append(
            FirepowerPreviewTarget(
                label=label,
                armor_percent=armor_percent,
                expected_dps=expected_dps,
                ratio_to_unarmored=ratio,
            )
        )

    base_warmup = weapon_profile.warmup_seconds
    base_cooldown = weapon_profile.cooldown_seconds
    actual_warmup = (
        base_warmup * compute_aiming_time_multiplier(attacker_profile)
        if weapon_profile.attack_mode == "ranged"
        else base_warmup
    )
    actual_cooldown = (
        base_cooldown * compute_ranged_cooldown_multiplier(attacker_profile)
        if weapon_profile.attack_mode == "ranged"
        else base_cooldown
    )
    return FirepowerPreview(
        weapon_name=weapon_profile.name,
        best_distance_label=_format_preview_distance_label(best_distance_name, best_distance_cells),
        best_distance_cells=best_distance_cells,
        final_hit_percent=best_analysis.accuracy.final_hit_chance * 100.0,
        base_warmup_seconds=base_warmup,
        actual_warmup_seconds=actual_warmup,
        base_cooldown_seconds=base_cooldown,
        actual_cooldown_seconds=actual_cooldown,
        theoretical_dps=best_analysis.damage.theoretical_dps,
        targets=targets,
    )


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
