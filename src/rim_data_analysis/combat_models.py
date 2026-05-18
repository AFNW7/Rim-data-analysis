from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class CombatStatModifier:
    name: str
    shooting_accuracy_per_tile_offset: float = 0.0
    shooting_accuracy_multiplier: float = 1.0
    aiming_time_multiplier: float = 1.0
    ranged_cooldown_multiplier: float = 1.0
    melee_hit_score_offset: float = 0.0
    melee_hit_chance_offset: float = 0.0
    melee_hit_chance_multiplier: float = 1.0
    melee_dodge_score_offset: float = 0.0
    melee_dodge_chance_offset: float = 0.0
    melee_dodge_chance_multiplier: float = 1.0
    melee_damage_multiplier: float = 1.0
    armor_penetration_multiplier: float = 1.0
    incoming_damage_multiplier: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class PawnCapacities:
    sight: float = 1.0
    manipulation: float = 1.0
    moving: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ApparelProfile:
    name: str
    source: str = "manual"
    layers: list[str] = field(default_factory=list)
    covers: list[str] = field(default_factory=list)
    armor_sharp: float = 0.0
    armor_blunt: float = 0.0
    armor_heat: float = 0.0
    layer_priority_override: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class PawnCombatProfile:
    name: str
    species: str = "human_baseliner"
    shooting_skill: int = 10
    melee_skill: int = 10
    body_size: float = 1.0
    capacities: PawnCapacities = field(default_factory=PawnCapacities)
    traits: list[str] = field(default_factory=list)
    modifiers: list[CombatStatModifier] = field(default_factory=list)
    apparel: list[ApparelProfile] = field(default_factory=list)
    shooting_accuracy_per_tile_override: float | None = None
    melee_hit_chance_override: float | None = None
    melee_dodge_chance_override: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "species": self.species,
            "shooting_skill": self.shooting_skill,
            "melee_skill": self.melee_skill,
            "body_size": self.body_size,
            "capacities": self.capacities.to_dict(),
            "traits": self.traits,
            "modifiers": [modifier.to_dict() for modifier in self.modifiers],
            "apparel": [apparel.to_dict() for apparel in self.apparel],
            "shooting_accuracy_per_tile_override": self.shooting_accuracy_per_tile_override,
            "melee_hit_chance_override": self.melee_hit_chance_override,
            "melee_dodge_chance_override": self.melee_dodge_chance_override,
        }


@dataclass(slots=True)
class WeaponProfile:
    name: str
    attack_mode: str
    damage_type: str
    damage: float
    armor_penetration: float
    warmup_seconds: float = 0.0
    cooldown_seconds: float = 0.0
    burst_shot_count: int = 1
    burst_shot_interval_seconds: float = 0.0
    accuracy_close: float = 1.0
    accuracy_short: float = 1.0
    accuracy_medium: float = 1.0
    accuracy_long: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class AttackContext:
    distance_cells: int = 12
    target_body_region: str = "Torso"
    target_is_aiming_or_firing: bool = False
    hit_chance_multiplier: float = 1.0
    cover_block_chance: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class CombatScenario:
    name: str
    attacker: PawnCombatProfile
    defender: PawnCombatProfile
    weapon: WeaponProfile
    context: AttackContext = field(default_factory=AttackContext)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "attacker": self.attacker.to_dict(),
            "defender": self.defender.to_dict(),
            "weapon": self.weapon.to_dict(),
            "context": self.context.to_dict(),
        }


@dataclass(slots=True)
class ApparelConflict:
    first_item: str
    second_item: str
    shared_layers: list[str]
    shared_regions: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ArmorLayerSnapshot:
    apparel_name: str
    source: str
    applicable_layers: list[str]
    applicable_regions: list[str]
    armor_value: float
    effective_armor: float
    local_deflect_chance: float
    local_half_chance: float
    local_full_damage_chance: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ArmorResolutionResult:
    original_damage_type: str
    final_damage_distribution: dict[str, float]
    expected_damage_after_armor: float
    expected_damage_after_final_multiplier: float
    reduction_rate_from_armor: float
    total_damage_taken_multiplier: float
    layers: list[ArmorLayerSnapshot]

    def to_dict(self) -> dict[str, object]:
        return {
            "original_damage_type": self.original_damage_type,
            "final_damage_distribution": self.final_damage_distribution,
            "expected_damage_after_armor": self.expected_damage_after_armor,
            "expected_damage_after_final_multiplier": self.expected_damage_after_final_multiplier,
            "reduction_rate_from_armor": self.reduction_rate_from_armor,
            "total_damage_taken_multiplier": self.total_damage_taken_multiplier,
            "layers": [layer.to_dict() for layer in self.layers],
        }


@dataclass(slots=True)
class AccuracyResult:
    attack_mode: str
    raw_hit_chance_before_cover: float
    cover_block_chance: float
    final_hit_chance: float
    accuracy_band: str | None
    attacker_shooting_accuracy_per_tile: float | None
    attacker_melee_hit_chance: float | None
    defender_melee_dodge_chance: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class DamageSummary:
    raw_damage_on_hit: float
    expected_damage_on_hit_after_defense: float
    expected_damage_per_attack_cycle: float
    theoretical_dps: float
    expected_dps: float
    realized_dps_ratio: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class CombatAnalysisResult:
    scenario_name: str
    attacker: dict[str, object]
    defender: dict[str, object]
    weapon: dict[str, object]
    context: dict[str, object]
    can_wear_outfit: bool
    apparel_conflicts: list[ApparelConflict]
    accuracy: AccuracyResult
    armor: ArmorResolutionResult
    damage: DamageSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_name": self.scenario_name,
            "attacker": self.attacker,
            "defender": self.defender,
            "weapon": self.weapon,
            "context": self.context,
            "can_wear_outfit": self.can_wear_outfit,
            "apparel_conflicts": [conflict.to_dict() for conflict in self.apparel_conflicts],
            "accuracy": self.accuracy.to_dict(),
            "armor": self.armor.to_dict(),
            "damage": self.damage.to_dict(),
        }

