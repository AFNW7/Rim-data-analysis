from __future__ import annotations

from dataclasses import dataclass


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
