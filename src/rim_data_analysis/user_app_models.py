from __future__ import annotations

from dataclasses import asdict, dataclass, field


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
