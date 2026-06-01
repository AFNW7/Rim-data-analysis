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


class ScenarioLibraryValidationError(ValueError):
    """Raised when a scenario library JSON file does not follow the V1 format."""


_LIBRARY_ROOT_FIELDS = {"format_version", "name", "templates", "scenarios"}
_TEMPLATE_FIELDS = {
    "id",
    "template_id",
    "name",
    "extends",
    "species",
    "shooting_skill",
    "melee_skill",
    "body_size",
    "capacities",
    "traits",
    "add_traits",
    "remove_traits",
    "modifiers",
    "apparel_def_names",
    "add_apparel_def_names",
    "remove_apparel_def_names",
    "manual_apparel",
    "shooting_accuracy_per_tile_override",
    "melee_hit_chance_override",
    "melee_dodge_chance_override",
    "notes",
}
_SCENARIO_FIELDS = {
    "id",
    "scenario_id",
    "name",
    "attacker_template",
    "defender_template",
    "weapon_def_name",
    "manual_weapon",
    "attacker_override",
    "defender_override",
    "context",
    "tags",
    "notes",
}
_CAPACITY_FIELDS = {"sight", "manipulation", "moving"}
_MODIFIER_FIELDS = {
    "name",
    "shooting_skill_offset",
    "shooting_accuracy_stat_offset",
    "shooting_accuracy_per_tile_offset",
    "shooting_accuracy_multiplier",
    "aiming_time_stat_offset",
    "aiming_time_multiplier",
    "ranged_cooldown_stat_offset",
    "ranged_cooldown_multiplier",
    "melee_hit_score_offset",
    "melee_hit_chance_offset",
    "melee_hit_chance_multiplier",
    "melee_dodge_score_offset",
    "melee_dodge_chance_offset",
    "melee_dodge_chance_multiplier",
    "melee_damage_multiplier",
    "armor_penetration_multiplier",
    "incoming_damage_multiplier",
}
_APPAREL_FIELDS = {
    "name",
    "source",
    "layers",
    "covers",
    "armor_sharp",
    "armor_blunt",
    "armor_heat",
    "layer_priority_override",
}
_WEAPON_FIELDS = {
    "name",
    "attack_mode",
    "damage_type",
    "damage",
    "armor_penetration",
    "warmup_seconds",
    "cooldown_seconds",
    "burst_shot_count",
    "burst_shot_interval_seconds",
    "accuracy_close",
    "accuracy_short",
    "accuracy_medium",
    "accuracy_long",
    "melee_attack_options",
}
_MELEE_ATTACK_FIELDS = {
    "label",
    "damage_type",
    "damage",
    "armor_penetration",
    "cooldown_seconds",
    "chance_factor",
    "capacities",
}
_CONTEXT_FIELDS = {
    "distance_cells",
    "target_body_region",
    "target_is_aiming_or_firing",
    "hit_chance_multiplier",
    "cover_block_chance",
    "weather_accuracy_multiplier",
    "smoke_accuracy_multiplier",
    "combat_in_darkness_accuracy_offset",
}


def _raise_validation_error(path: str, message: str) -> None:
    raise ScenarioLibraryValidationError(f"{path}: {message}")


def _ensure_object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _raise_validation_error(path, "must be an object.")
    return value


def _ensure_list(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        _raise_validation_error(path, "must be an array.")
    return value


def _ensure_known_fields(data: dict[str, object], allowed: set[str], path: str) -> None:
    unknown_fields = sorted(set(data) - allowed)
    if unknown_fields:
        joined = ", ".join(unknown_fields)
        _raise_validation_error(path, f"contains unknown field(s): {joined}.")


def _ensure_string(
    value: object,
    path: str,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        _raise_validation_error(path, "must be a string.")
    if not allow_empty and not value.strip():
        _raise_validation_error(path, "must not be empty.")
    return value


def _ensure_number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        _raise_validation_error(path, "must be a number.")
    return float(value)


def _ensure_int(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise_validation_error(path, "must be an integer.")
    return value


def _ensure_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        _raise_validation_error(path, "must be a boolean.")
    return value


def _resolve_alias_string(
    data: dict[str, object],
    *,
    primary_key: str,
    alias_key: str,
    path: str,
    required: bool,
) -> str | None:
    primary_present = primary_key in data and data[primary_key] is not None
    alias_present = alias_key in data and data[alias_key] is not None

    primary_value = None
    alias_value = None
    if primary_present:
        primary_value = _ensure_string(data[primary_key], f"{path}.{primary_key}")
    if alias_present:
        alias_value = _ensure_string(data[alias_key], f"{path}.{alias_key}")

    if primary_present and alias_present and primary_value != alias_value:
        _raise_validation_error(
            path,
            f"'{primary_key}' and '{alias_key}' must match when both are provided.",
        )

    if primary_value is not None:
        return primary_value
    if alias_value is not None:
        return alias_value
    if required:
        _raise_validation_error(path, f"requires '{primary_key}' or '{alias_key}'.")
    return None


def _validate_string_list(value: object, path: str) -> None:
    items = _ensure_list(value, path)
    for index, item in enumerate(items):
        _ensure_string(item, f"{path}[{index}]")


def _validate_numeric_fields(data: dict[str, object], path: str, field_names: set[str]) -> None:
    for field_name in field_names:
        if field_name in data and data[field_name] is not None:
            _ensure_number(data[field_name], f"{path}.{field_name}")


def _validate_capacities(value: object, path: str) -> None:
    capacities = _ensure_object(value, path)
    _ensure_known_fields(capacities, _CAPACITY_FIELDS, path)
    for field_name in _CAPACITY_FIELDS:
        if field_name in capacities and capacities[field_name] is not None:
            _ensure_number(capacities[field_name], f"{path}.{field_name}")


def _validate_modifier(value: object, path: str) -> None:
    modifier = _ensure_object(value, path)
    _ensure_known_fields(modifier, _MODIFIER_FIELDS, path)
    if "name" in modifier and modifier["name"] is not None:
        _ensure_string(modifier["name"], f"{path}.name")
    _validate_numeric_fields(modifier, path, _MODIFIER_FIELDS - {"name"})


def _validate_manual_apparel(value: object, path: str) -> None:
    apparel = _ensure_object(value, path)
    _ensure_known_fields(apparel, _APPAREL_FIELDS, path)
    if "name" not in apparel or apparel["name"] is None:
        _raise_validation_error(path, "requires 'name'.")
    _ensure_string(apparel["name"], f"{path}.name")
    if "source" in apparel and apparel["source"] is not None:
        _ensure_string(apparel["source"], f"{path}.source")
    if "layers" in apparel and apparel["layers"] is not None:
        _validate_string_list(apparel["layers"], f"{path}.layers")
    if "covers" in apparel and apparel["covers"] is not None:
        _validate_string_list(apparel["covers"], f"{path}.covers")
    _validate_numeric_fields(
        apparel,
        path,
        {"armor_sharp", "armor_blunt", "armor_heat"},
    )
    if "layer_priority_override" in apparel and apparel["layer_priority_override"] is not None:
        _ensure_int(apparel["layer_priority_override"], f"{path}.layer_priority_override")


def _validate_manual_weapon(value: object, path: str) -> None:
    weapon = _ensure_object(value, path)
    _ensure_known_fields(weapon, _WEAPON_FIELDS, path)
    for required_field in ("name", "attack_mode", "damage_type", "damage"):
        if required_field not in weapon or weapon[required_field] is None:
            _raise_validation_error(path, f"requires '{required_field}'.")

    _ensure_string(weapon["name"], f"{path}.name")
    attack_mode = _ensure_string(weapon["attack_mode"], f"{path}.attack_mode")
    if attack_mode not in {"ranged", "melee"}:
        _raise_validation_error(f"{path}.attack_mode", "must be 'ranged' or 'melee'.")
    _ensure_string(weapon["damage_type"], f"{path}.damage_type")
    _validate_numeric_fields(
        weapon,
        path,
        {
            "damage",
            "armor_penetration",
            "warmup_seconds",
            "cooldown_seconds",
            "burst_shot_interval_seconds",
            "accuracy_close",
            "accuracy_short",
            "accuracy_medium",
            "accuracy_long",
        },
    )
    if "burst_shot_count" in weapon and weapon["burst_shot_count"] is not None:
        _ensure_int(weapon["burst_shot_count"], f"{path}.burst_shot_count")
    if "melee_attack_options" in weapon and weapon["melee_attack_options"] is not None:
        options = _ensure_list(weapon["melee_attack_options"], f"{path}.melee_attack_options")
        for index, option in enumerate(options):
            option_path = f"{path}.melee_attack_options[{index}]"
            option_payload = _ensure_object(option, option_path)
            _ensure_known_fields(option_payload, _MELEE_ATTACK_FIELDS, option_path)
            for required_field in ("label", "damage_type", "damage", "armor_penetration", "cooldown_seconds"):
                if required_field not in option_payload or option_payload[required_field] is None:
                    _raise_validation_error(option_path, f"requires '{required_field}'.")
            _ensure_string(option_payload["label"], f"{option_path}.label")
            _ensure_string(option_payload["damage_type"], f"{option_path}.damage_type")
            _validate_numeric_fields(
                option_payload,
                option_path,
                {"damage", "armor_penetration", "cooldown_seconds", "chance_factor"},
            )
            if "capacities" in option_payload and option_payload["capacities"] is not None:
                _validate_string_list(option_payload["capacities"], f"{option_path}.capacities")


def _validate_context(value: object, path: str) -> None:
    context = _ensure_object(value, path)
    _ensure_known_fields(context, _CONTEXT_FIELDS, path)
    if "distance_cells" in context and context["distance_cells"] is not None:
        _ensure_int(context["distance_cells"], f"{path}.distance_cells")
    if "target_body_region" in context and context["target_body_region"] is not None:
        _ensure_string(context["target_body_region"], f"{path}.target_body_region")
    if "target_is_aiming_or_firing" in context and context["target_is_aiming_or_firing"] is not None:
        _ensure_bool(context["target_is_aiming_or_firing"], f"{path}.target_is_aiming_or_firing")
    _validate_numeric_fields(
        context,
        path,
        {
            "hit_chance_multiplier",
            "cover_block_chance",
            "weather_accuracy_multiplier",
            "smoke_accuracy_multiplier",
            "combat_in_darkness_accuracy_offset",
        },
    )


def _validate_template_payload(
    value: object,
    path: str,
    *,
    allow_missing_id: bool,
    allow_extends: bool,
) -> str | None:
    template = _ensure_object(value, path)
    _ensure_known_fields(template, _TEMPLATE_FIELDS, path)
    template_id = _resolve_alias_string(
        template,
        primary_key="id",
        alias_key="template_id",
        path=path,
        required=not allow_missing_id,
    )

    if not allow_extends and "extends" in template and template["extends"] is not None:
        _raise_validation_error(
            f"{path}.extends",
            "is not supported inside scenario overrides; overrides already apply on top of the base template.",
        )
    if "name" in template and template["name"] is not None:
        _ensure_string(template["name"], f"{path}.name")
    if "extends" in template and template["extends"] is not None:
        _ensure_string(template["extends"], f"{path}.extends")
    if "species" in template and template["species"] is not None:
        _ensure_string(template["species"], f"{path}.species")
    for field_name in ("shooting_skill", "melee_skill"):
        if field_name in template and template[field_name] is not None:
            _ensure_int(template[field_name], f"{path}.{field_name}")
    _validate_numeric_fields(
        template,
        path,
        {
            "body_size",
            "shooting_accuracy_per_tile_override",
            "melee_hit_chance_override",
            "melee_dodge_chance_override",
        },
    )
    if "capacities" in template and template["capacities"] is not None:
        _validate_capacities(template["capacities"], f"{path}.capacities")
    for field_name in (
        "traits",
        "add_traits",
        "remove_traits",
        "apparel_def_names",
        "add_apparel_def_names",
        "remove_apparel_def_names",
    ):
        if field_name in template and template[field_name] is not None:
            _validate_string_list(template[field_name], f"{path}.{field_name}")
    if "modifiers" in template and template["modifiers"] is not None:
        modifiers = _ensure_list(template["modifiers"], f"{path}.modifiers")
        for index, modifier in enumerate(modifiers):
            _validate_modifier(modifier, f"{path}.modifiers[{index}]")
    if "manual_apparel" in template and template["manual_apparel"] is not None:
        manual_apparel = _ensure_list(template["manual_apparel"], f"{path}.manual_apparel")
        for index, apparel in enumerate(manual_apparel):
            _validate_manual_apparel(apparel, f"{path}.manual_apparel[{index}]")
    if "notes" in template and template["notes"] is not None:
        _ensure_string(template["notes"], f"{path}.notes", allow_empty=True)

    return template_id


def _validate_scenario_payload(value: object, path: str) -> str:
    scenario = _ensure_object(value, path)
    _ensure_known_fields(scenario, _SCENARIO_FIELDS, path)
    scenario_id = _resolve_alias_string(
        scenario,
        primary_key="id",
        alias_key="scenario_id",
        path=path,
        required=True,
    )
    if scenario_id is None:
        _raise_validation_error(path, "could not resolve scenario id.")

    if "name" not in scenario or scenario["name"] is None:
        _raise_validation_error(path, "requires 'name'.")
    _ensure_string(scenario["name"], f"{path}.name")

    for field_name in ("attacker_template", "defender_template"):
        if field_name not in scenario or scenario[field_name] is None:
            _raise_validation_error(path, f"requires '{field_name}'.")
        _ensure_string(scenario[field_name], f"{path}.{field_name}")

    has_weapon_def_name = "weapon_def_name" in scenario and scenario["weapon_def_name"] is not None
    has_manual_weapon = "manual_weapon" in scenario and scenario["manual_weapon"] is not None
    if has_weapon_def_name == has_manual_weapon:
        _raise_validation_error(
            path,
            "must provide exactly one of 'weapon_def_name' or 'manual_weapon'.",
        )
    if has_weapon_def_name:
        _ensure_string(scenario["weapon_def_name"], f"{path}.weapon_def_name")
    if has_manual_weapon:
        _validate_manual_weapon(scenario["manual_weapon"], f"{path}.manual_weapon")

    if "attacker_override" in scenario and scenario["attacker_override"] is not None:
        _validate_template_payload(
            scenario["attacker_override"],
            f"{path}.attacker_override",
            allow_missing_id=True,
            allow_extends=False,
        )
    if "defender_override" in scenario and scenario["defender_override"] is not None:
        _validate_template_payload(
            scenario["defender_override"],
            f"{path}.defender_override",
            allow_missing_id=True,
            allow_extends=False,
        )
    if "context" in scenario and scenario["context"] is not None:
        _validate_context(scenario["context"], f"{path}.context")
    if "tags" in scenario and scenario["tags"] is not None:
        _validate_string_list(scenario["tags"], f"{path}.tags")
    if "notes" in scenario and scenario["notes"] is not None:
        _ensure_string(scenario["notes"], f"{path}.notes", allow_empty=True)

    return scenario_id


def _validate_library_relationships(
    templates: dict[str, PawnTemplateSpec],
    template_paths: dict[str, str],
    scenarios: list[tuple[ScenarioSpec, str]],
) -> None:
    resolved_templates: set[str] = set()
    visiting_templates: set[str] = set()
    stack: list[str] = []

    def visit(template_id: str) -> None:
        if template_id in resolved_templates:
            return

        visiting_templates.add(template_id)
        stack.append(template_id)
        parent_id = templates[template_id].extends
        if parent_id is not None:
            if parent_id not in templates:
                _raise_validation_error(
                    f"{template_paths[template_id]}.extends",
                    f"references unknown template '{parent_id}'.",
                )
            if parent_id in visiting_templates:
                cycle = " -> ".join(stack + [parent_id])
                _raise_validation_error(
                    f"{template_paths[template_id]}.extends",
                    f"creates an inheritance cycle: {cycle}.",
                )
            visit(parent_id)
        stack.pop()
        visiting_templates.remove(template_id)
        resolved_templates.add(template_id)

    for template_id in templates:
        visit(template_id)

    for scenario_spec, scenario_path in scenarios:
        if scenario_spec.attacker_template not in templates:
            _raise_validation_error(
                f"{scenario_path}.attacker_template",
                f"references unknown template '{scenario_spec.attacker_template}'.",
            )
        if scenario_spec.defender_template not in templates:
            _raise_validation_error(
                f"{scenario_path}.defender_template",
                f"references unknown template '{scenario_spec.defender_template}'.",
            )


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
    format_version: int = 1


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

    _ensure_known_fields(payload, _LIBRARY_ROOT_FIELDS, "root")

    format_version_value = payload.get("format_version", 1)
    format_version = _ensure_int(format_version_value, "root.format_version")
    if format_version != 1:
        _raise_validation_error("root.format_version", "only format_version 1 is supported.")
    if "name" in payload and payload["name"] is not None:
        _ensure_string(payload["name"], "root.name")

    if "templates" not in payload:
        _raise_validation_error("root", "requires 'templates'.")
    if "scenarios" not in payload:
        _raise_validation_error("root", "requires 'scenarios'.")

    templates_list = _ensure_list(payload["templates"], "root.templates")
    scenarios_list = _ensure_list(payload["scenarios"], "root.scenarios")

    templates: dict[str, PawnTemplateSpec] = {}
    template_paths: dict[str, str] = {}
    for index, item in enumerate(templates_list):
        item_path = f"root.templates[{index}]"
        template_id = _validate_template_payload(
            item,
            item_path,
            allow_missing_id=False,
            allow_extends=True,
        )
        if template_id is None:
            _raise_validation_error(item_path, "could not resolve template id.")
        if template_id in templates:
            _raise_validation_error(
                item_path,
                f"duplicates template id '{template_id}' from {template_paths[template_id]}.",
            )
        template_spec = _parse_template_spec(_ensure_object(item, item_path))
        templates[template_id] = template_spec
        template_paths[template_id] = item_path

    scenarios: list[ScenarioSpec] = []
    scenarios_with_paths: list[tuple[ScenarioSpec, str]] = []
    scenario_paths: dict[str, str] = {}
    for index, item in enumerate(scenarios_list):
        item_path = f"root.scenarios[{index}]"
        scenario_id = _validate_scenario_payload(item, item_path)
        if scenario_id in scenario_paths:
            _raise_validation_error(
                item_path,
                f"duplicates scenario id '{scenario_id}' from {scenario_paths[scenario_id]}.",
            )
        scenario_spec = _parse_scenario_spec(_ensure_object(item, item_path))
        scenarios.append(scenario_spec)
        scenarios_with_paths.append((scenario_spec, item_path))
        scenario_paths[scenario_id] = item_path

    _validate_library_relationships(templates, template_paths, scenarios_with_paths)

    return ScenarioLibrary(
        name=str(payload.get("name", path.stem)),
        templates=templates,
        scenarios=scenarios,
        format_version=format_version,
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
        self._template_stack: list[str] = []

    def resolve_template(self, template_id: str) -> ResolvedPawnBlueprint:
        if template_id in self._template_cache:
            return self._template_cache[template_id].clone()

        spec = self.library.templates.get(template_id)
        if spec is None:
            raise KeyError(f"Unknown template: {template_id}")
        if template_id in self._template_stack:
            cycle = " -> ".join(self._template_stack + [template_id])
            raise ScenarioLibraryValidationError(f"Template inheritance cycle detected at runtime: {cycle}")

        self._template_stack.append(template_id)
        try:
            if spec.extends:
                base = self.resolve_template(spec.extends)
            else:
                base = ResolvedPawnBlueprint(name=spec.name or spec.template_id)

            resolved = _apply_spec(base, spec)
            self._template_cache[template_id] = resolved
            return resolved.clone()
        finally:
            self._template_stack.pop()

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
