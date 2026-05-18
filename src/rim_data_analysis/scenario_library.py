from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from rim_data_analysis.combat_engine import analyze_scenario
from rim_data_analysis.combat_io import (
    apparel_from_dict,
    context_from_dict,
    modifier_from_dict,
    weapon_from_dict,
)
from rim_data_analysis.combat_models import (
    ApparelProfile,
    AttackContext,
    CombatAnalysisResult,
    CombatScenario,
    CombatStatModifier,
    PawnCapacities,
    PawnCombatProfile,
    WeaponProfile,
)
from rim_data_analysis.vanilla_models import VanillaApparelRecord, VanillaCatalog, VanillaWeaponRecord


@dataclass(slots=True)
class PawnTemplateSpec:
    template_id: str
    name: str | None = None
    extends: str | None = None
    species: str | None = None
    shooting_skill: int | None = None
    melee_skill: int | None = None
    body_size: float | None = None
    capacities: dict[str, float] = field(default_factory=dict)
    traits: list[str] | None = None
    add_traits: list[str] = field(default_factory=list)
    remove_traits: list[str] = field(default_factory=list)
    modifiers: list[CombatStatModifier] = field(default_factory=list)
    apparel_def_names: list[str] | None = None
    add_apparel_def_names: list[str] = field(default_factory=list)
    remove_apparel_def_names: list[str] = field(default_factory=list)
    manual_apparel: list[ApparelProfile] = field(default_factory=list)
    shooting_accuracy_per_tile_override: float | None = None
    melee_hit_chance_override: float | None = None
    melee_dodge_chance_override: float | None = None
    notes: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScenarioSpec:
    scenario_id: str
    name: str
    attacker_template: str
    defender_template: str
    weapon_def_name: str | None = None
    manual_weapon: WeaponProfile | None = None
    attacker_override: PawnTemplateSpec | None = None
    defender_override: PawnTemplateSpec | None = None
    context: AttackContext = field(default_factory=AttackContext)
    tags: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass(slots=True)
class ScenarioLibrary:
    name: str
    templates: dict[str, PawnTemplateSpec]
    scenarios: list[ScenarioSpec]


@dataclass(slots=True)
class ResolvedPawnBlueprint:
    name: str
    species: str = "human_baseliner"
    shooting_skill: int = 10
    melee_skill: int = 10
    body_size: float = 1.0
    capacities: PawnCapacities = field(default_factory=PawnCapacities)
    traits: list[str] = field(default_factory=list)
    modifiers: list[CombatStatModifier] = field(default_factory=list)
    apparel_def_names: list[str] = field(default_factory=list)
    manual_apparel: list[ApparelProfile] = field(default_factory=list)
    shooting_accuracy_per_tile_override: float | None = None
    melee_hit_chance_override: float | None = None
    melee_dodge_chance_override: float | None = None

    def clone(self) -> ResolvedPawnBlueprint:
        return ResolvedPawnBlueprint(
            name=self.name,
            species=self.species,
            shooting_skill=self.shooting_skill,
            melee_skill=self.melee_skill,
            body_size=self.body_size,
            capacities=PawnCapacities(
                sight=self.capacities.sight,
                manipulation=self.capacities.manipulation,
                moving=self.capacities.moving,
            ),
            traits=list(self.traits),
            modifiers=copy.deepcopy(self.modifiers),
            apparel_def_names=list(self.apparel_def_names),
            manual_apparel=copy.deepcopy(self.manual_apparel),
            shooting_accuracy_per_tile_override=self.shooting_accuracy_per_tile_override,
            melee_hit_chance_override=self.melee_hit_chance_override,
            melee_dodge_chance_override=self.melee_dodge_chance_override,
        )

    def to_pawn_profile(self, apparel_lookup: dict[str, VanillaApparelRecord]) -> PawnCombatProfile:
        apparel_items = [apparel_lookup[def_name].to_apparel_profile() for def_name in self.apparel_def_names]
        apparel_items.extend(self.manual_apparel)
        return PawnCombatProfile(
            name=self.name,
            species=self.species,
            shooting_skill=self.shooting_skill,
            melee_skill=self.melee_skill,
            body_size=self.body_size,
            capacities=PawnCapacities(
                sight=self.capacities.sight,
                manipulation=self.capacities.manipulation,
                moving=self.capacities.moving,
            ),
            traits=list(self.traits),
            modifiers=list(self.modifiers),
            apparel=apparel_items,
            shooting_accuracy_per_tile_override=self.shooting_accuracy_per_tile_override,
            melee_hit_chance_override=self.melee_hit_chance_override,
            melee_dodge_chance_override=self.melee_dodge_chance_override,
        )


@dataclass(slots=True)
class ScenarioRecord:
    library_name: str
    scenario_id: str
    scenario_name: str
    tags: list[str]
    attacker_template: str
    defender_template: str
    weapon_def_name: str | None
    attack_mode: str
    analysis: CombatAnalysisResult

    def to_flat_dict(self) -> dict[str, object]:
        return {
            "library_name": self.library_name,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "tags": "|".join(self.tags),
            "attacker_template": self.attacker_template,
            "defender_template": self.defender_template,
            "weapon_def_name": self.weapon_def_name,
            "attack_mode": self.attack_mode,
            "can_wear_outfit": self.analysis.can_wear_outfit,
            "final_hit_chance": self.analysis.accuracy.final_hit_chance,
            "expected_damage_on_hit": self.analysis.damage.expected_damage_on_hit_after_defense,
            "expected_damage_per_attack_cycle": self.analysis.damage.expected_damage_per_attack_cycle,
            "expected_dps": self.analysis.damage.expected_dps,
            "theoretical_dps": self.analysis.damage.theoretical_dps,
            "realized_dps_ratio": self.analysis.damage.realized_dps_ratio,
            "armor_reduction_rate": self.analysis.armor.reduction_rate_from_armor,
            "incoming_damage_multiplier": self.analysis.armor.total_damage_taken_multiplier,
        }

    def to_dict(self) -> dict[str, object]:
        payload = self.to_flat_dict()
        payload["analysis"] = self.analysis.to_dict()
        return payload


def _parse_template_spec(data: dict[str, object], *, default_id: str | None = None) -> PawnTemplateSpec:
    template_id = str(data.get("id") or data.get("template_id") or default_id or "anonymous")
    modifiers = [
        modifier_from_dict(item)
        for item in data.get("modifiers", [])
        if isinstance(item, dict)
    ]
    manual_apparel = [
        apparel_from_dict(item)
        for item in data.get("manual_apparel", [])
        if isinstance(item, dict)
    ]
    capacities_payload = data.get("capacities")
    capacities: dict[str, float] = {}
    if isinstance(capacities_payload, dict):
        capacities = {
            str(key): float(value)
            for key, value in capacities_payload.items()
        }
    return PawnTemplateSpec(
        template_id=template_id,
        name=str(data["name"]) if data.get("name") is not None else None,
        extends=str(data["extends"]) if data.get("extends") is not None else None,
        species=str(data["species"]) if data.get("species") is not None else None,
        shooting_skill=int(data["shooting_skill"]) if data.get("shooting_skill") is not None else None,
        melee_skill=int(data["melee_skill"]) if data.get("melee_skill") is not None else None,
        body_size=float(data["body_size"]) if data.get("body_size") is not None else None,
        capacities=capacities,
        traits=[str(item) for item in data["traits"]] if data.get("traits") is not None else None,
        add_traits=[str(item) for item in data.get("add_traits", [])],
        remove_traits=[str(item) for item in data.get("remove_traits", [])],
        modifiers=modifiers,
        apparel_def_names=(
            [str(item) for item in data["apparel_def_names"]]
            if data.get("apparel_def_names") is not None
            else None
        ),
        add_apparel_def_names=[str(item) for item in data.get("add_apparel_def_names", [])],
        remove_apparel_def_names=[str(item) for item in data.get("remove_apparel_def_names", [])],
        manual_apparel=manual_apparel,
        shooting_accuracy_per_tile_override=(
            float(data["shooting_accuracy_per_tile_override"])
            if data.get("shooting_accuracy_per_tile_override") is not None
            else None
        ),
        melee_hit_chance_override=(
            float(data["melee_hit_chance_override"])
            if data.get("melee_hit_chance_override") is not None
            else None
        ),
        melee_dodge_chance_override=(
            float(data["melee_dodge_chance_override"])
            if data.get("melee_dodge_chance_override") is not None
            else None
        ),
        notes=str(data["notes"]) if data.get("notes") is not None else None,
        tags=[str(item) for item in data.get("tags", [])],
    )


def _parse_scenario_spec(data: dict[str, object]) -> ScenarioSpec:
    manual_weapon_payload = data.get("manual_weapon")
    manual_weapon = weapon_from_dict(manual_weapon_payload) if isinstance(manual_weapon_payload, dict) else None
    attacker_override = (
        _parse_template_spec(data["attacker_override"], default_id="attacker_override")
        if isinstance(data.get("attacker_override"), dict)
        else None
    )
    defender_override = (
        _parse_template_spec(data["defender_override"], default_id="defender_override")
        if isinstance(data.get("defender_override"), dict)
        else None
    )
    return ScenarioSpec(
        scenario_id=str(data.get("id") or data.get("scenario_id") or data["name"]),
        name=str(data["name"]),
        attacker_template=str(data["attacker_template"]),
        defender_template=str(data["defender_template"]),
        weapon_def_name=str(data["weapon_def_name"]) if data.get("weapon_def_name") is not None else None,
        manual_weapon=manual_weapon,
        attacker_override=attacker_override,
        defender_override=defender_override,
        context=context_from_dict(data.get("context") if isinstance(data.get("context"), dict) else None),
        tags=[str(item) for item in data.get("tags", [])],
        notes=str(data["notes"]) if data.get("notes") is not None else None,
    )


def load_scenario_library(path: Path) -> ScenarioLibrary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Scenario library root must be an object.")

    templates_list = payload.get("templates", [])
    scenarios_list = payload.get("scenarios", [])
    templates = {
        spec.template_id: spec
        for spec in (
            _parse_template_spec(item)
            for item in templates_list
            if isinstance(item, dict)
        )
    }
    scenarios = [
        _parse_scenario_spec(item)
        for item in scenarios_list
        if isinstance(item, dict)
    ]
    return ScenarioLibrary(
        name=str(payload.get("name", path.stem)),
        templates=templates,
        scenarios=scenarios,
    )


def _merge_unique(base_items: list[str], add_items: list[str], remove_items: list[str]) -> list[str]:
    result = list(base_items)
    for item in add_items:
        if item not in result:
            result.append(item)
    if remove_items:
        result = [item for item in result if item not in set(remove_items)]
    return result


def _apply_spec(
    base: ResolvedPawnBlueprint,
    spec: PawnTemplateSpec,
) -> ResolvedPawnBlueprint:
    name = spec.name if spec.name is not None else base.name
    species = spec.species if spec.species is not None else base.species
    shooting_skill = spec.shooting_skill if spec.shooting_skill is not None else base.shooting_skill
    melee_skill = spec.melee_skill if spec.melee_skill is not None else base.melee_skill
    body_size = spec.body_size if spec.body_size is not None else base.body_size
    capacities = PawnCapacities(
        sight=spec.capacities.get("sight", base.capacities.sight),
        manipulation=spec.capacities.get("manipulation", base.capacities.manipulation),
        moving=spec.capacities.get("moving", base.capacities.moving),
    )

    traits = list(base.traits if spec.traits is None else [str(item) for item in spec.traits])
    traits = _merge_unique(traits, spec.add_traits, spec.remove_traits)

    apparel_def_names = list(base.apparel_def_names if spec.apparel_def_names is None else spec.apparel_def_names)
    apparel_def_names = _merge_unique(apparel_def_names, spec.add_apparel_def_names, spec.remove_apparel_def_names)

    manual_apparel = list(base.manual_apparel)
    manual_apparel.extend(spec.manual_apparel)

    modifiers = list(base.modifiers)
    modifiers.extend(spec.modifiers)

    return ResolvedPawnBlueprint(
        name=name,
        species=species,
        shooting_skill=shooting_skill,
        melee_skill=melee_skill,
        body_size=body_size,
        capacities=capacities,
        traits=traits,
        modifiers=modifiers,
        apparel_def_names=apparel_def_names,
        manual_apparel=manual_apparel,
        shooting_accuracy_per_tile_override=(
            spec.shooting_accuracy_per_tile_override
            if spec.shooting_accuracy_per_tile_override is not None
            else base.shooting_accuracy_per_tile_override
        ),
        melee_hit_chance_override=(
            spec.melee_hit_chance_override
            if spec.melee_hit_chance_override is not None
            else base.melee_hit_chance_override
        ),
        melee_dodge_chance_override=(
            spec.melee_dodge_chance_override
            if spec.melee_dodge_chance_override is not None
            else base.melee_dodge_chance_override
        ),
    )


class ScenarioLibraryResolver:
    def __init__(self, library: ScenarioLibrary, catalog: VanillaCatalog) -> None:
        self.library = library
        self.catalog = catalog
        self.weapon_lookup: dict[str, VanillaWeaponRecord] = {
            weapon.def_name: weapon for weapon in catalog.weapons
        }
        self.apparel_lookup: dict[str, VanillaApparelRecord] = {
            apparel.def_name: apparel for apparel in catalog.apparel
        }
        self._template_cache: dict[str, ResolvedPawnBlueprint] = {}

    def resolve_template(self, template_id: str) -> ResolvedPawnBlueprint:
        if template_id in self._template_cache:
            return self._template_cache[template_id].clone()

        spec = self.library.templates.get(template_id)
        if spec is None:
            raise KeyError(f"Unknown template: {template_id}")

        if spec.extends:
            base = self.resolve_template(spec.extends)
        else:
            base = ResolvedPawnBlueprint(name=spec.name or spec.template_id)

        resolved = _apply_spec(base, spec)
        self._template_cache[template_id] = resolved
        return resolved.clone()

    def resolve_weapon(self, scenario: ScenarioSpec) -> WeaponProfile:
        if scenario.manual_weapon is not None:
            return scenario.manual_weapon
        if scenario.weapon_def_name is None:
            raise ValueError(f"Scenario {scenario.scenario_id} has no weapon_def_name or manual_weapon.")
        if scenario.weapon_def_name not in self.weapon_lookup:
            raise KeyError(f"Unknown vanilla weapon defName: {scenario.weapon_def_name}")
        return self.weapon_lookup[scenario.weapon_def_name].to_weapon_profile()

    def resolve_pawn(
        self,
        template_id: str,
        *,
        override: PawnTemplateSpec | None = None,
    ) -> PawnCombatProfile:
        blueprint = self.resolve_template(template_id)
        if override is not None:
            blueprint = _apply_spec(blueprint, override)
        for def_name in blueprint.apparel_def_names:
            if def_name not in self.apparel_lookup:
                raise KeyError(f"Unknown vanilla apparel defName: {def_name}")
        return blueprint.to_pawn_profile(self.apparel_lookup)

    def resolve_scenario(self, spec: ScenarioSpec) -> CombatScenario:
        attacker = self.resolve_pawn(spec.attacker_template, override=spec.attacker_override)
        defender = self.resolve_pawn(spec.defender_template, override=spec.defender_override)
        weapon = self.resolve_weapon(spec)
        return CombatScenario(
            name=spec.name,
            attacker=attacker,
            defender=defender,
            weapon=weapon,
            context=spec.context,
        )


def analyze_library(
    library: ScenarioLibrary,
    catalog: VanillaCatalog,
    *,
    required_tags: list[str] | None = None,
    scenario_ids: list[str] | None = None,
    name_contains: str | None = None,
) -> list[ScenarioRecord]:
    resolver = ScenarioLibraryResolver(library, catalog)
    selected_ids = set(scenario_ids or [])
    selected_tags = {tag.lower() for tag in (required_tags or [])}
    records: list[ScenarioRecord] = []

    for spec in library.scenarios:
        if selected_ids and spec.scenario_id not in selected_ids:
            continue
        if selected_tags and not selected_tags.issubset({tag.lower() for tag in spec.tags}):
            continue
        if name_contains and name_contains.lower() not in spec.name.lower():
            continue

        scenario = resolver.resolve_scenario(spec)
        analysis = analyze_scenario(scenario)
        records.append(
            ScenarioRecord(
                library_name=library.name,
                scenario_id=spec.scenario_id,
                scenario_name=spec.name,
                tags=list(spec.tags),
                attacker_template=spec.attacker_template,
                defender_template=spec.defender_template,
                weapon_def_name=spec.weapon_def_name,
                attack_mode=scenario.weapon.attack_mode,
                analysis=analysis,
            )
        )

    return records
