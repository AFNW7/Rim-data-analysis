from __future__ import annotations

from dataclasses import asdict, dataclass, field

from rim_data_analysis.combat_models import ApparelProfile, CombatStatModifier, MeleeAttackOption, WeaponProfile


@dataclass(slots=True)
class VanillaWeaponRecord:
    def_name: str
    label: str
    source_package: str
    root_path: str
    attack_mode: str
    damage_type: str
    damage: float
    armor_penetration: float
    cooldown_seconds: float
    warmup_seconds: float
    burst_shot_count: int
    burst_shot_interval_seconds: float
    accuracy_close: float
    accuracy_short: float
    accuracy_medium: float
    accuracy_long: float
    projectile_def: str | None = None
    primary_tool_label: str | None = None
    primary_tool_capacities: list[str] = field(default_factory=list)
    melee_attack_options: list[MeleeAttackOption] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    supports_material: bool = False
    source_tag: str = "vanilla"

    @property
    def display_label(self) -> str:
        return f"{self.label}/{self.source_tag}" if self.source_tag else self.label

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_weapon_profile(self) -> WeaponProfile:
        return WeaponProfile(
            name=self.display_label,
            attack_mode=self.attack_mode,
            damage_type=self.damage_type,
            damage=self.damage,
            armor_penetration=self.armor_penetration,
            warmup_seconds=self.warmup_seconds,
            cooldown_seconds=self.cooldown_seconds,
            burst_shot_count=self.burst_shot_count,
            burst_shot_interval_seconds=self.burst_shot_interval_seconds,
            accuracy_close=self.accuracy_close,
            accuracy_short=self.accuracy_short,
            accuracy_medium=self.accuracy_medium,
            accuracy_long=self.accuracy_long,
            melee_attack_options=[MeleeAttackOption(**option.to_dict()) for option in self.melee_attack_options],
        )


@dataclass(slots=True)
class VanillaApparelRecord:
    def_name: str
    label: str
    source_package: str
    root_path: str
    layers: list[str]
    body_part_groups: list[str]
    armor_sharp: float
    armor_blunt: float
    armor_heat: float
    stuff_armor_multiplier: float = 0.0
    modifier: CombatStatModifier | None = None
    supports_material: bool = False
    source_tag: str = "vanilla"

    @property
    def display_label(self) -> str:
        return f"{self.label}/{self.source_tag}" if self.source_tag else self.label

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["modifier"] = self.modifier.to_dict() if self.modifier is not None else None
        return payload

    def to_apparel_profile(self) -> ApparelProfile:
        return ApparelProfile(
            name=self.display_label,
            source=self.source_package,
            layers=self.layers,
            covers=self.body_part_groups,
            armor_sharp=self.armor_sharp,
            armor_blunt=self.armor_blunt,
            armor_heat=self.armor_heat,
        )

    def to_modifier(self) -> CombatStatModifier | None:
        return self.modifier


@dataclass(slots=True)
class VanillaImplantRecord:
    def_name: str
    label: str
    source_package: str
    root_path: str
    body_part_hint: str
    part_efficiency: float
    modifier: CombatStatModifier | None = None
    source_tag: str = "vanilla"

    @property
    def display_label(self) -> str:
        return f"{self.label}/{self.source_tag}" if self.source_tag else self.label

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["modifier"] = self.modifier.to_dict() if self.modifier is not None else None
        return payload

    def to_modifier(self) -> CombatStatModifier | None:
        return self.modifier


@dataclass(slots=True)
class VanillaCatalog:
    game_data_root: str
    packages: list[str]
    weapons: list[VanillaWeaponRecord]
    apparel: list[VanillaApparelRecord]
    implants: list[VanillaImplantRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "game_data_root": self.game_data_root,
            "packages": self.packages,
            "weapons": [weapon.to_dict() for weapon in self.weapons],
            "apparel": [item.to_dict() for item in self.apparel],
            "implants": [item.to_dict() for item in self.implants],
        }
