from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tarfile
from xml.etree import ElementTree

from rim_data_analysis.combat_models import CombatStatModifier, MeleeAttackOption
from rim_data_analysis.vanilla_models import (
    VanillaApparelRecord,
    VanillaCatalog,
    VanillaImplantRecord,
    VanillaWeaponRecord,
)


@dataclass(slots=True)
class RawThingDef:
    def_name: str | None
    template_name: str | None
    parent_name: str | None
    abstract: bool
    source_package: str
    root_path: str
    element: ElementTree.Element


@dataclass(slots=True)
class RawHediffDef:
    def_name: str | None
    template_name: str | None
    parent_name: str | None
    abstract: bool
    source_package: str
    root_path: str
    element: ElementTree.Element


@dataclass(slots=True)
class RawRecipeDef:
    def_name: str | None
    template_name: str | None
    parent_name: str | None
    abstract: bool
    source_package: str
    root_path: str
    element: ElementTree.Element


@dataclass(slots=True)
class RawDamageDef:
    def_name: str | None
    template_name: str | None
    parent_name: str | None
    abstract: bool
    source_package: str
    root_path: str
    element: ElementTree.Element


class ThingDefResolver:
    def __init__(self, thing_defs: list[RawThingDef]) -> None:
        self.thing_defs = thing_defs
        self.by_def_name = {
            thing_def.def_name: thing_def for thing_def in thing_defs if thing_def.def_name
        }
        self.by_template_name = {
            thing_def.template_name: thing_def for thing_def in thing_defs if thing_def.template_name
        }

    def ancestors(self, thing_def: RawThingDef) -> list[RawThingDef]:
        chain: list[RawThingDef] = []
        current = thing_def
        seen: set[str] = set()
        while current is not None:
            chain.append(current)
            if not current.parent_name or current.parent_name in seen:
                break
            seen.add(current.parent_name)
            current = self.by_template_name.get(current.parent_name)
        return chain

    def text_at(self, thing_def: RawThingDef, path: tuple[str, ...]) -> str | None:
        for current in self.ancestors(thing_def):
            node = self._find_path(current.element, path)
            if node is not None and node.text and node.text.strip():
                return node.text.strip()
        return None

    def list_at(self, thing_def: RawThingDef, path: tuple[str, ...]) -> list[str]:
        for current in self.ancestors(thing_def):
            node = self._find_path(current.element, path)
            if node is None:
                continue
            values = [
                child.text.strip()
                for child in list(node)
                if child.text and child.text.strip()
            ]
            if values:
                return values
        return []

    def node_at(self, thing_def: RawThingDef, path: tuple[str, ...]) -> ElementTree.Element | None:
        for current in self.ancestors(thing_def):
            node = self._find_path(current.element, path)
            if node is not None:
                return node
        return None

    @staticmethod
    def _find_path(root: ElementTree.Element, path: tuple[str, ...]) -> ElementTree.Element | None:
        current = root
        for segment in path:
            current = current.find(segment)
            if current is None:
                return None
        return current


class HediffDefResolver:
    def __init__(self, hediff_defs: list[RawHediffDef]) -> None:
        self.hediff_defs = hediff_defs
        self.by_def_name = {
            hediff_def.def_name: hediff_def for hediff_def in hediff_defs if hediff_def.def_name
        }
        self.by_template_name = {
            hediff_def.template_name: hediff_def
            for hediff_def in hediff_defs
            if hediff_def.template_name
        }

    def ancestors(self, hediff_def: RawHediffDef) -> list[RawHediffDef]:
        chain: list[RawHediffDef] = []
        current = hediff_def
        seen: set[str] = set()
        while current is not None:
            chain.append(current)
            if not current.parent_name or current.parent_name in seen:
                break
            seen.add(current.parent_name)
            current = self.by_template_name.get(current.parent_name)
        return chain

    def text_at(self, hediff_def: RawHediffDef, path: tuple[str, ...]) -> str | None:
        for current in self.ancestors(hediff_def):
            node = ThingDefResolver._find_path(current.element, path)
            if node is not None and node.text and node.text.strip():
                return node.text.strip()
        return None

    def list_at(self, hediff_def: RawHediffDef, path: tuple[str, ...]) -> list[str]:
        for current in self.ancestors(hediff_def):
            node = ThingDefResolver._find_path(current.element, path)
            if node is None:
                continue
            values = [
                child.text.strip()
                for child in list(node)
                if child.text and child.text.strip()
            ]
            if values:
                return values
        return []

    def node_at(self, hediff_def: RawHediffDef, path: tuple[str, ...]) -> ElementTree.Element | None:
        for current in self.ancestors(hediff_def):
            node = ThingDefResolver._find_path(current.element, path)
            if node is not None:
                return node
        return None


class RecipeDefResolver:
    def __init__(self, recipe_defs: list[RawRecipeDef]) -> None:
        self.recipe_defs = recipe_defs
        self.by_template_name = {
            recipe_def.template_name: recipe_def
            for recipe_def in recipe_defs
            if recipe_def.template_name
        }

    def ancestors(self, recipe_def: RawRecipeDef) -> list[RawRecipeDef]:
        chain: list[RawRecipeDef] = []
        current = recipe_def
        seen: set[str] = set()
        while current is not None:
            chain.append(current)
            if not current.parent_name or current.parent_name in seen:
                break
            seen.add(current.parent_name)
            current = self.by_template_name.get(current.parent_name)
        return chain

    def text_at(self, recipe_def: RawRecipeDef, path: tuple[str, ...]) -> str | None:
        for current in self.ancestors(recipe_def):
            node = ThingDefResolver._find_path(current.element, path)
            if node is not None and node.text and node.text.strip():
                return node.text.strip()
        return None

    def list_at(self, recipe_def: RawRecipeDef, path: tuple[str, ...]) -> list[str]:
        for current in self.ancestors(recipe_def):
            node = ThingDefResolver._find_path(current.element, path)
            if node is None:
                continue
            values = [
                child.text.strip()
                for child in list(node)
                if child.text and child.text.strip()
            ]
            if values:
                return values
        return []


class DamageDefResolver:
    def __init__(self, damage_defs: list[RawDamageDef]) -> None:
        self.damage_defs = damage_defs
        self.by_def_name = {
            damage_def.def_name: damage_def for damage_def in damage_defs if damage_def.def_name
        }
        self.by_template_name = {
            damage_def.template_name: damage_def
            for damage_def in damage_defs
            if damage_def.template_name
        }

    def ancestors(self, damage_def: RawDamageDef) -> list[RawDamageDef]:
        chain: list[RawDamageDef] = []
        current = damage_def
        seen: set[str] = set()
        while current is not None:
            chain.append(current)
            if not current.parent_name or current.parent_name in seen:
                break
            seen.add(current.parent_name)
            current = self.by_template_name.get(current.parent_name)
        return chain

    def text_at(self, damage_def: RawDamageDef, path: tuple[str, ...]) -> str | None:
        for current in self.ancestors(damage_def):
            node = ThingDefResolver._find_path(current.element, path)
            if node is not None and node.text and node.text.strip():
                return node.text.strip()
        return None


def _package_dirs(game_data_root: Path) -> list[Path]:
    def sort_key(path: Path) -> tuple[int, str]:
        return (0 if path.name.lower() == "core" else 1, path.name.lower())

    return sorted([path for path in game_data_root.iterdir() if path.is_dir()], key=sort_key)


def _iter_defs_files(package_root: Path):
    defs_root = package_root / "Defs"
    if not defs_root.exists():
        return
    for xml_path in defs_root.rglob("*.xml"):
        if xml_path.is_file():
            yield xml_path


def _source_tag(root_path: str) -> str:
    normalized = root_path.replace("/", "\\").lower()
    base_name = Path(root_path).name.lower()
    if "\\data\\" in normalized or base_name in {
        "core",
        "royalty",
        "ideology",
        "biotech",
        "anomaly",
        "odyssey",
    }:
        return "vanilla"
    return Path(root_path).name


def _is_simplified_chinese_name(name: str) -> bool:
    lowered = name.lower()
    return "chinesesimplified" in lowered or "简体" in name


def _iter_language_sources(package_root: Path):
    languages_root = package_root / "Languages"
    if not languages_root.exists():
        return
    for path in sorted(languages_root.iterdir(), key=lambda item: item.name.lower()):
        if not _is_simplified_chinese_name(path.name):
            continue
        if path.is_dir():
            yield path
        elif path.is_file() and path.suffix.lower() == ".tar":
            yield path


def _parse_raw_thing_defs(game_data_root: Path) -> list[RawThingDef]:
    records: list[RawThingDef] = []
    for package_root in _package_dirs(game_data_root):
        for xml_path in _iter_defs_files(package_root):
            try:
                root = ElementTree.parse(xml_path).getroot()
            except ElementTree.ParseError:
                continue

            for child in list(root):
                if not isinstance(child.tag, str):
                    continue
                if child.tag.rsplit("}", 1)[-1] != "ThingDef":
                    continue

                def_name = _child_text(child, "defName")
                records.append(
                    RawThingDef(
                        def_name=def_name,
                        template_name=child.attrib.get("Name"),
                        parent_name=child.attrib.get("ParentName"),
                        abstract=child.attrib.get("Abstract", "").lower() == "true",
                        source_package=package_root.name,
                        root_path=str(package_root),
                        element=child,
                    )
                )
    return records


def _parse_raw_hediff_defs(game_data_root: Path) -> list[RawHediffDef]:
    records: list[RawHediffDef] = []
    for package_root in _package_dirs(game_data_root):
        for xml_path in _iter_defs_files(package_root):
            try:
                root = ElementTree.parse(xml_path).getroot()
            except ElementTree.ParseError:
                continue

            for child in list(root):
                if not isinstance(child.tag, str):
                    continue
                if child.tag.rsplit("}", 1)[-1] != "HediffDef":
                    continue

                def_name = _child_text(child, "defName")
                records.append(
                    RawHediffDef(
                        def_name=def_name,
                        template_name=child.attrib.get("Name"),
                        parent_name=child.attrib.get("ParentName"),
                        abstract=child.attrib.get("Abstract", "").lower() == "true",
                        source_package=package_root.name,
                        root_path=str(package_root),
                        element=child,
                    )
                )
    return records


def _parse_raw_recipe_defs(game_data_root: Path) -> list[RawRecipeDef]:
    records: list[RawRecipeDef] = []
    for package_root in _package_dirs(game_data_root):
        for xml_path in _iter_defs_files(package_root):
            try:
                root = ElementTree.parse(xml_path).getroot()
            except ElementTree.ParseError:
                continue

            for child in list(root):
                if not isinstance(child.tag, str):
                    continue
                if child.tag.rsplit("}", 1)[-1] != "RecipeDef":
                    continue

                def_name = _child_text(child, "defName")
                records.append(
                    RawRecipeDef(
                        def_name=def_name,
                        template_name=child.attrib.get("Name"),
                        parent_name=child.attrib.get("ParentName"),
                        abstract=child.attrib.get("Abstract", "").lower() == "true",
                        source_package=package_root.name,
                        root_path=str(package_root),
                        element=child,
                    )
                )
    return records


def _parse_raw_damage_defs(game_data_root: Path) -> list[RawDamageDef]:
    records: list[RawDamageDef] = []
    for package_root in _package_dirs(game_data_root):
        for xml_path in _iter_defs_files(package_root):
            try:
                root = ElementTree.parse(xml_path).getroot()
            except ElementTree.ParseError:
                continue

            for child in list(root):
                if not isinstance(child.tag, str):
                    continue
                if child.tag.rsplit("}", 1)[-1] != "DamageDef":
                    continue

                def_name = _child_text(child, "defName")
                records.append(
                    RawDamageDef(
                        def_name=def_name,
                        template_name=child.attrib.get("Name"),
                        parent_name=child.attrib.get("ParentName"),
                        abstract=child.attrib.get("Abstract", "").lower() == "true",
                        source_package=package_root.name,
                        root_path=str(package_root),
                        element=child,
                    )
                )
    return records


def _child_text(root: ElementTree.Element, tag: str) -> str | None:
    node = root.find(tag)
    if node is None or node.text is None:
        return None
    text = node.text.strip()
    return text or None


def _text_or_default(value: str | None, default: str) -> str:
    return value if value else default


def _float_or_default(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _percent_scale(value: float) -> float:
    if 0.0 <= value <= 2.5:
        return value * 100.0
    return value


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "1", "yes"}


def _weapon_tags(resolver: ThingDefResolver, thing_def: RawThingDef) -> list[str]:
    return resolver.list_at(thing_def, ("weaponTags",))


def _supports_material(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    made_from_stuff = (
        resolver.text_at(thing_def, ("MadeFromStuff",))
        or resolver.text_at(thing_def, ("madeFromStuff",))
        or ""
    ).strip().lower()
    if made_from_stuff in {"true", "1", "yes"}:
        return True
    if resolver.node_at(thing_def, ("stuffCategories",)) is not None:
        return True
    if _float_or_default(resolver.text_at(thing_def, ("costStuffCount",)), 0.0) > 0:
        return True
    return False


_APPAREL_FACTOR_TO_MODIFIER_FIELD: dict[str, str] = {
    "ShootingAccuracyPawn": "shooting_accuracy_multiplier",
    "AimingDelayFactor": "aiming_time_multiplier",
    "RangedWeapon_Cooldown": "ranged_cooldown_multiplier",
    "Sight": "sight_multiplier",
    "Manipulation": "manipulation_multiplier",
    "Moving": "moving_multiplier",
}

_APPAREL_OFFSET_TO_MODIFIER_FIELD: dict[str, str] = {
    "ShootingAccuracyPawn": "shooting_accuracy_stat_offset",
    "AimingDelayFactor": "aiming_time_stat_offset",
    "RangedCooldownFactor": "ranged_cooldown_stat_offset",
    "Sight": "sight_offset",
    "Manipulation": "manipulation_offset",
    "Moving": "moving_offset",
}

_CAPACITY_FACTOR_TO_MODIFIER_FIELD: dict[str, str] = {
    "Sight": "sight_multiplier",
    "Manipulation": "manipulation_multiplier",
    "Moving": "moving_multiplier",
}

_CAPACITY_OFFSET_TO_MODIFIER_FIELD: dict[str, str] = {
    "Sight": "sight_offset",
    "Manipulation": "manipulation_offset",
    "Moving": "moving_offset",
}


def _stat_entries(resolver: ThingDefResolver, thing_def: RawThingDef, path: tuple[str, ...]) -> dict[str, float]:
    node = resolver.node_at(thing_def, path)
    if node is None:
        return {}
    values: dict[str, float] = {}
    for child in list(node):
        if not isinstance(child.tag, str):
            continue
        text = (child.text or "").strip()
        if not text:
            continue
        try:
            values[child.tag] = float(text)
        except ValueError:
            continue
    return values


def _hediff_stat_entries(
    resolver: HediffDefResolver,
    hediff_def: RawHediffDef,
    path: tuple[str, ...],
) -> dict[str, float]:
    node = resolver.node_at(hediff_def, path)
    return _stat_entries_from_node(node)


def _stat_entries_from_node(node: ElementTree.Element | None) -> dict[str, float]:
    if node is None:
        return {}
    values: dict[str, float] = {}
    for child in list(node):
        if not isinstance(child.tag, str):
            continue
        text = (child.text or "").strip()
        if not text:
            continue
        try:
            values[child.tag.rsplit("}", 1)[-1]] = float(text)
        except ValueError:
            continue
    return values


def _merge_offset_values(target: dict[str, float], source: dict[str, float]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0.0) + value


def _merge_factor_values(target: dict[str, float], source: dict[str, float]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 1.0) * value


def _pick_default_stage(
    resolver: HediffDefResolver,
    hediff_def: RawHediffDef,
) -> ElementTree.Element | None:
    stages_node = resolver.node_at(hediff_def, ("stages",))
    if stages_node is None:
        return None
    stage_nodes = [child for child in list(stages_node) if isinstance(child.tag, str)]
    if not stage_nodes:
        return None

    best_stage = stage_nodes[0]
    best_min_severity = _float_or_default(_child_text(best_stage, "minSeverity"), 0.0)
    for stage_node in stage_nodes[1:]:
        min_severity = _float_or_default(_child_text(stage_node, "minSeverity"), 0.0)
        if min_severity <= 1.0 and min_severity >= best_min_severity:
            best_stage = stage_node
            best_min_severity = min_severity
    return best_stage


def _stage_capacity_entries(stage_node: ElementTree.Element | None) -> tuple[dict[str, float], dict[str, float]]:
    if stage_node is None:
        return {}, {}
    cap_mods_node = stage_node.find("capMods")
    if cap_mods_node is None:
        return {}, {}

    offsets: dict[str, float] = {}
    factors: dict[str, float] = {}
    for child in list(cap_mods_node):
        if not isinstance(child.tag, str):
            continue
        capacity_name = _child_text(child, "capacity")
        if not capacity_name:
            continue

        offset = _float_or_default(_child_text(child, "offset"), 0.0)
        if offset != 0.0:
            offsets[capacity_name] = offsets.get(capacity_name, 0.0) + offset

        post_factor = _child_text(child, "postFactor")
        if post_factor is not None:
            factors[capacity_name] = factors.get(capacity_name, 1.0) * _float_or_default(post_factor, 1.0)

    return offsets, factors


def _modifier_from_stat_payloads(
    label: str,
    *,
    stat_offsets: dict[str, float],
    stat_factors: dict[str, float],
    capacity_offsets: dict[str, float] | None = None,
    capacity_factors: dict[str, float] | None = None,
) -> CombatStatModifier | None:
    payload: dict[str, float | str] = {"name": label}
    capacity_offsets = capacity_offsets or {}
    capacity_factors = capacity_factors or {}

    for stat_name, modifier_field in _APPAREL_OFFSET_TO_MODIFIER_FIELD.items():
        if stat_name in stat_offsets:
            payload[modifier_field] = float(payload.get(modifier_field, 0.0)) + stat_offsets[stat_name]

    for stat_name, modifier_field in _APPAREL_FACTOR_TO_MODIFIER_FIELD.items():
        if stat_name in stat_factors:
            payload[modifier_field] = float(payload.get(modifier_field, 1.0)) * stat_factors[stat_name]

    for capacity_name, modifier_field in _CAPACITY_OFFSET_TO_MODIFIER_FIELD.items():
        if capacity_name in capacity_offsets:
            payload[modifier_field] = float(payload.get(modifier_field, 0.0)) + capacity_offsets[capacity_name]

    for capacity_name, modifier_field in _CAPACITY_FACTOR_TO_MODIFIER_FIELD.items():
        if capacity_name in capacity_factors:
            payload[modifier_field] = float(payload.get(modifier_field, 1.0)) * capacity_factors[capacity_name]

    if len(payload) == 1:
        return None
    return CombatStatModifier(
        name=str(payload["name"]),
        shooting_accuracy_stat_offset=float(payload.get("shooting_accuracy_stat_offset", 0.0)),
        shooting_accuracy_per_tile_offset=float(payload.get("shooting_accuracy_per_tile_offset", 0.0)),
        shooting_accuracy_multiplier=float(payload.get("shooting_accuracy_multiplier", 1.0)),
        aiming_time_stat_offset=float(payload.get("aiming_time_stat_offset", 0.0)),
        aiming_time_multiplier=float(payload.get("aiming_time_multiplier", 1.0)),
        ranged_cooldown_stat_offset=float(payload.get("ranged_cooldown_stat_offset", 0.0)),
        ranged_cooldown_multiplier=float(payload.get("ranged_cooldown_multiplier", 1.0)),
        sight_offset=float(payload.get("sight_offset", 0.0)),
        sight_multiplier=float(payload.get("sight_multiplier", 1.0)),
        manipulation_offset=float(payload.get("manipulation_offset", 0.0)),
        manipulation_multiplier=float(payload.get("manipulation_multiplier", 1.0)),
        moving_offset=float(payload.get("moving_offset", 0.0)),
        moving_multiplier=float(payload.get("moving_multiplier", 1.0)),
    )


def _apparel_modifier(resolver: ThingDefResolver, thing_def: RawThingDef, label: str) -> CombatStatModifier | None:
    stat_offsets = _stat_entries(resolver, thing_def, ("statOffsets",))
    _merge_offset_values(stat_offsets, _stat_entries(resolver, thing_def, ("equippedStatOffsets",)))
    stat_factors = _stat_entries(resolver, thing_def, ("statFactors",))
    _merge_factor_values(stat_factors, _stat_entries(resolver, thing_def, ("equippedStatFactors",)))
    return _modifier_from_stat_payloads(
        label,
        stat_offsets=stat_offsets,
        stat_factors=stat_factors,
    )


def _normalize_body_part_hint(body_part: str) -> str:
    normalized = body_part.strip().lower()
    if normalized in {"eye"}:
        return "Eye"
    if normalized in {"arm", "shoulder", "hand"}:
        return "Arm"
    if normalized in {"leg", "foot"}:
        return "Leg"
    if normalized in {"ear"}:
        return "Ear"
    if normalized in {"brain"}:
        return "Brain"
    if normalized in {"nose"}:
        return "Nose"
    if normalized in {"spine"}:
        return "Spine"
    if normalized in {"heart"}:
        return "Heart"
    if normalized in {"lung"}:
        return "Lung"
    if normalized in {"stomach"}:
        return "Stomach"
    if normalized in {"kidney"}:
        return "Kidney"
    if normalized in {"liver"}:
        return "Liver"
    if normalized in {"jaw"}:
        return "Jaw"
    if normalized in {"torso", "chest"}:
        return "Torso"
    return body_part.strip() or "Unknown"


def _body_part_hint(def_name: str, label: str, recipe_body_part: str | None = None) -> str:
    if recipe_body_part:
        return _normalize_body_part_hint(recipe_body_part)

    text = f"{def_name} {label}".lower()
    if "eye" in text:
        return "Eye"
    if "arm" in text or "hand" in text or "shoulder" in text:
        return "Arm"
    if "leg" in text or "foot" in text:
        return "Leg"
    if "ear" in text:
        return "Ear"
    if "brain" in text:
        return "Brain"
    if "nose" in text:
        return "Nose"
    if "spine" in text:
        return "Spine"
    if "heart" in text:
        return "Heart"
    if "lung" in text:
        return "Lung"
    if "stomach" in text:
        return "Stomach"
    if "kidney" in text:
        return "Kidney"
    if "liver" in text:
        return "Liver"
    if "jaw" in text:
        return "Jaw"
    if "torso" in text or "chest" in text:
        return "Torso"
    return "Unknown"


def _implant_modifier(
    resolver: ThingDefResolver,
    thing_def: RawThingDef,
    label: str,
    *,
    body_part_hint: str,
    part_efficiency: float,
) -> CombatStatModifier | None:
    stat_offsets = _stat_entries(resolver, thing_def, ("statOffsets",))
    stat_factors = _stat_entries(resolver, thing_def, ("statFactors",))
    return _modifier_from_stat_payloads(label, stat_offsets=stat_offsets, stat_factors=stat_factors)


def _hediff_implant_modifier(
    resolver: HediffDefResolver,
    hediff_def: RawHediffDef,
    label: str,
    *,
    body_part_hint: str,
    part_efficiency: float,
) -> CombatStatModifier | None:
    stat_offsets = _hediff_stat_entries(resolver, hediff_def, ("statOffsets",))
    stat_factors = _hediff_stat_entries(resolver, hediff_def, ("statFactors",))
    capacity_offsets: dict[str, float] = {}
    capacity_factors: dict[str, float] = {}

    stage_node = _pick_default_stage(resolver, hediff_def)
    part_efficiency_offset = 0.0
    if stage_node is not None:
        _merge_offset_values(stat_offsets, _stat_entries_from_node(stage_node.find("statOffsets")))
        _merge_factor_values(stat_factors, _stat_entries_from_node(stage_node.find("statFactors")))
        stage_capacity_offsets, stage_capacity_factors = _stage_capacity_entries(stage_node)
        _merge_offset_values(capacity_offsets, stage_capacity_offsets)
        _merge_factor_values(capacity_factors, stage_capacity_factors)
        part_efficiency_offset = _float_or_default(_child_text(stage_node, "partEfficiencyOffset"), 0.0)

    return _modifier_from_stat_payloads(
        label,
        stat_offsets=stat_offsets,
        stat_factors=stat_factors,
        capacity_offsets=capacity_offsets,
        capacity_factors=capacity_factors,
    )


def _is_hediff_implant(resolver: HediffDefResolver, hediff_def: RawHediffDef) -> bool:
    if hediff_def.parent_name in {"ImplantHediffBase", "AddedBodyPartBase"}:
        return True
    if resolver.node_at(hediff_def, ("addedPartProps",)) is not None:
        return True
    if resolver.text_at(hediff_def, ("spawnThingOnRemoved",)) is not None:
        return True
    if _is_true(resolver.text_at(hediff_def, ("countsAsAddedPartOrImplant",))):
        return True
    return False


def _build_recipe_body_part_map(recipe_defs: list[RawRecipeDef]) -> dict[str, str]:
    resolver = RecipeDefResolver(recipe_defs)
    mapping: dict[str, str] = {}
    for recipe_def in recipe_defs:
        if recipe_def.abstract or not recipe_def.def_name:
            continue
        adds_hediff = resolver.text_at(recipe_def, ("addsHediff",))
        body_parts = resolver.list_at(recipe_def, ("appliedOnFixedBodyParts",))
        if adds_hediff and body_parts and adds_hediff not in mapping:
            mapping[adds_hediff] = body_parts[0]
    return mapping


def _language_labels_from_root(root: ElementTree.Element) -> dict[str, str]:
    if root.tag.rsplit("}", 1)[-1] != "LanguageData":
        return {}
    labels: dict[str, str] = {}
    for child in list(root):
        if not isinstance(child.tag, str):
            continue
        tag = child.tag.rsplit("}", 1)[-1]
        if not tag.endswith(".label"):
            continue
        text = (child.text or "").strip()
        if not text:
            continue
        labels[tag[:-6]] = text
    return labels


def _merge_language_labels(
    target: dict[str, str],
    *,
    root: ElementTree.Element,
) -> None:
    target.update(_language_labels_from_root(root))


def _load_simplified_language_labels(
    game_data_root: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    thing_labels: dict[str, str] = {}
    hediff_labels: dict[str, str] = {}

    for package_root in _package_dirs(game_data_root):
        for source in _iter_language_sources(package_root):
            if source.is_dir():
                for def_type, target in (("ThingDef", thing_labels), ("HediffDef", hediff_labels)):
                    defs_root = source / "DefInjected" / def_type
                    if not defs_root.exists():
                        continue
                    for xml_path in defs_root.rglob("*.xml"):
                        if not xml_path.is_file():
                            continue
                        try:
                            root = ElementTree.parse(xml_path).getroot()
                        except ElementTree.ParseError:
                            continue
                        _merge_language_labels(target, root=root)
                continue

            try:
                with tarfile.open(source, "r:*") as archive:
                    for member in archive.getmembers():
                        if not member.isfile():
                            continue
                        member_name = member.name.replace("\\", "/")
                        target: dict[str, str] | None = None
                        if (
                            member_name.startswith("DefInjected/ThingDef/")
                            or "/DefInjected/ThingDef/" in member_name
                        ):
                            target = thing_labels
                        elif (
                            member_name.startswith("DefInjected/HediffDef/")
                            or "/DefInjected/HediffDef/" in member_name
                        ):
                            target = hediff_labels
                        if target is None or not member_name.endswith(".xml"):
                            continue
                        handle = archive.extractfile(member)
                        if handle is None:
                            continue
                        try:
                            root = ElementTree.parse(handle).getroot()
                        except ElementTree.ParseError:
                            continue
                        _merge_language_labels(target, root=root)
            except (tarfile.TarError, OSError):
                continue

    return thing_labels, hediff_labels


def _select_ranged_verb(resolver: ThingDefResolver, thing_def: RawThingDef) -> ElementTree.Element | None:
    node = resolver.node_at(thing_def, ("verbs",))
    if node is None:
        return None
    candidates = [
        child
        for child in list(node)
        if isinstance(child.tag, str)
        and (
            child.find("defaultProjectile") is not None
            or _float_or_default(_child_text(child, "range"), 0.0) > 1.5
        )
    ]
    return candidates[0] if candidates else None


def _melee_tools(resolver: ThingDefResolver, thing_def: RawThingDef) -> list[ElementTree.Element]:
    node = resolver.node_at(thing_def, ("tools",))
    if node is None:
        return []
    return [
        child
        for child in list(node)
        if isinstance(child.tag, str) and _child_text(child, "power") is not None
    ]


def _select_primary_tool(resolver: ThingDefResolver, thing_def: RawThingDef) -> ElementTree.Element | None:
    tools = _melee_tools(resolver, thing_def)
    if not tools:
        return None
    return max(tools, key=lambda tool: _float_or_default(_child_text(tool, "power"), 0.0))


def _tool_capacities(tool: ElementTree.Element) -> list[str]:
    capacities_node = tool.find("capacities")
    return [
        child.text.strip()
        for child in list(capacities_node) if capacities_node is not None
        if child.text and child.text.strip()
    ]


def _damage_type_from_tool(tool: ElementTree.Element) -> str:
    capacities = _tool_capacities(tool)
    if any(capacity.lower() == "blunt" for capacity in capacities):
        return "Blunt"
    return "Sharp"


def _is_ranged_weapon(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    return _select_ranged_verb(resolver, thing_def) is not None


def _is_melee_weapon(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    if resolver.node_at(thing_def, ("apparel",)) is not None:
        return False
    if not _melee_tools(resolver, thing_def):
        return False
    tags = _weapon_tags(resolver, thing_def)
    categories = resolver.list_at(thing_def, ("thingCategories",))
    return "Weapons" in categories or bool(tags)


def _parse_melee_attack_option(tool: ElementTree.Element) -> MeleeAttackOption:
    damage = _float_or_default(_child_text(tool, "power"))
    armor_penetration = _child_text(tool, "armorPenetration")
    armor_penetration_value = damage * 0.015 if armor_penetration is None else _float_or_default(armor_penetration)
    return MeleeAttackOption(
        label=_child_text(tool, "label") or "attack",
        damage_type=_damage_type_from_tool(tool),
        damage=damage,
        armor_penetration=_percent_scale(armor_penetration_value),
        cooldown_seconds=_float_or_default(_child_text(tool, "cooldownTime"), 2.0),
        chance_factor=_float_or_default(_child_text(tool, "chanceFactor"), 1.0),
        capacities=_tool_capacities(tool),
    )


def _is_apparel(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    return resolver.node_at(thing_def, ("apparel",)) is not None


def _is_implant(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    if resolver.node_at(thing_def, ("addedPartProps",)) is None:
        return False
    if _is_ranged_weapon(resolver, thing_def) or _is_melee_weapon(resolver, thing_def) or _is_apparel(resolver, thing_def):
        return False
    return True


def _fallback_damage_type(damage_def_name: str | None) -> str | None:
    normalized = (damage_def_name or "").strip().lower()
    if normalized in {"sharp", "bullet", "arrow", "rangedstab"}:
        return "Sharp"
    if normalized in {"blunt"}:
        return "Blunt"
    if normalized in {"heat", "flame"}:
        return "Heat"
    return None


def _resolve_projectile_damage_profile(
    resolver: ThingDefResolver,
    projectile: RawThingDef,
    damage_resolver: DamageDefResolver,
) -> tuple[float, str, float]:
    damage_def_name = resolver.text_at(projectile, ("projectile", "damageDef"))
    damage_def = damage_resolver.by_def_name.get(damage_def_name) if damage_def_name else None
    armor_category = (
        damage_resolver.text_at(damage_def, ("armorCategory",))
        if damage_def is not None
        else None
    )
    damage_type = armor_category or _fallback_damage_type(damage_def_name) or "Sharp"

    damage_amount_base = _float_or_default(
        resolver.text_at(projectile, ("projectile", "damageAmountBase")),
        -1.0,
    )
    damage = (
        damage_amount_base
        if damage_amount_base >= 0.0
        else _float_or_default(
            damage_resolver.text_at(damage_def, ("defaultDamage",))
            if damage_def is not None
            else None,
            0.0,
        )
    )

    if armor_category is None and _fallback_damage_type(damage_def_name) is None:
        return max(damage, 0.0), damage_type, 0.0

    armor_penetration_base = _float_or_default(
        resolver.text_at(projectile, ("projectile", "armorPenetrationBase")),
        -1.0,
    )
    if armor_penetration_base >= 0.0:
        armor_penetration = _percent_scale(armor_penetration_base)
    elif damage_amount_base >= 0.0:
        # Match RimWorld's ProjectileProperties.GetArmorPenetration:
        # missing base AP on a normal projectile falls back to damage * 0.015.
        armor_penetration = _percent_scale(max(damage, 0.0) * 0.015)
    else:
        armor_penetration = _percent_scale(
            _float_or_default(
                damage_resolver.text_at(damage_def, ("defaultArmorPenetration",))
                if damage_def is not None
                else None,
                0.0,
            )
        )

    return max(damage, 0.0), damage_type, armor_penetration


def _parse_ranged_weapon(
    resolver: ThingDefResolver,
    thing_def: RawThingDef,
    damage_resolver: DamageDefResolver,
) -> VanillaWeaponRecord | None:
    verb = _select_ranged_verb(resolver, thing_def)
    if verb is None:
        return None

    projectile_def = _child_text(verb, "defaultProjectile")
    projectile = resolver.by_def_name.get(projectile_def) if projectile_def else None
    damage = 0.0
    damage_type = "Sharp"
    armor_penetration = 0.0
    if projectile is not None:
        damage, damage_type, armor_penetration = _resolve_projectile_damage_profile(
            resolver,
            projectile,
            damage_resolver,
        )

    label = resolver.text_at(thing_def, ("label",)) or thing_def.def_name or "unnamed-weapon"
    return VanillaWeaponRecord(
        def_name=thing_def.def_name or label,
        label=label,
        source_package=thing_def.source_package,
        root_path=thing_def.root_path,
        attack_mode="ranged",
        damage_type=damage_type,
        damage=damage,
        armor_penetration=armor_penetration,
        cooldown_seconds=_float_or_default(resolver.text_at(thing_def, ("statBases", "RangedWeapon_Cooldown"))),
        warmup_seconds=_float_or_default(_child_text(verb, "warmupTime")),
        burst_shot_count=int(_float_or_default(_child_text(verb, "burstShotCount"), 1.0)),
        burst_shot_interval_seconds=_float_or_default(_child_text(verb, "ticksBetweenBurstShots")) / 60.0,
        accuracy_close=_float_or_default(resolver.text_at(thing_def, ("statBases", "AccuracyTouch")), 1.0),
        accuracy_short=_float_or_default(resolver.text_at(thing_def, ("statBases", "AccuracyShort")), 1.0),
        accuracy_medium=_float_or_default(resolver.text_at(thing_def, ("statBases", "AccuracyMedium")), 1.0),
        accuracy_long=_float_or_default(resolver.text_at(thing_def, ("statBases", "AccuracyLong")), 1.0),
        projectile_def=projectile_def,
        primary_tool_label=None,
        primary_tool_capacities=[],
        tags=_weapon_tags(resolver, thing_def),
        supports_material=_supports_material(resolver, thing_def),
    )


def _parse_melee_weapon(
    resolver: ThingDefResolver,
    thing_def: RawThingDef,
) -> VanillaWeaponRecord | None:
    tools = _melee_tools(resolver, thing_def)
    if not tools:
        return None
    tool = max(tools, key=lambda item: _float_or_default(_child_text(item, "power"), 0.0))
    attack_options = [_parse_melee_attack_option(item) for item in tools]
    primary_attack = _parse_melee_attack_option(tool)
    label = resolver.text_at(thing_def, ("label",)) or thing_def.def_name or "unnamed-weapon"
    return VanillaWeaponRecord(
        def_name=thing_def.def_name or label,
        label=label,
        source_package=thing_def.source_package,
        root_path=thing_def.root_path,
        attack_mode="melee",
        damage_type=primary_attack.damage_type,
        damage=primary_attack.damage,
        armor_penetration=primary_attack.armor_penetration,
        cooldown_seconds=primary_attack.cooldown_seconds,
        warmup_seconds=0.0,
        burst_shot_count=1,
        burst_shot_interval_seconds=0.0,
        accuracy_close=1.0,
        accuracy_short=1.0,
        accuracy_medium=1.0,
        accuracy_long=1.0,
        projectile_def=None,
        primary_tool_label=primary_attack.label,
        primary_tool_capacities=list(primary_attack.capacities),
        melee_attack_options=attack_options,
        tags=_weapon_tags(resolver, thing_def),
        supports_material=_supports_material(resolver, thing_def),
    )


def _parse_apparel(
    resolver: ThingDefResolver,
    thing_def: RawThingDef,
) -> VanillaApparelRecord | None:
    label = resolver.text_at(thing_def, ("label",)) or thing_def.def_name or "unnamed-apparel"
    return VanillaApparelRecord(
        def_name=thing_def.def_name or label,
        label=label,
        source_package=thing_def.source_package,
        root_path=thing_def.root_path,
        layers=resolver.list_at(thing_def, ("apparel", "layers")),
        body_part_groups=resolver.list_at(thing_def, ("apparel", "bodyPartGroups")),
        armor_sharp=_percent_scale(
            _float_or_default(resolver.text_at(thing_def, ("statBases", "ArmorRating_Sharp")))
        ),
        armor_blunt=_percent_scale(
            _float_or_default(resolver.text_at(thing_def, ("statBases", "ArmorRating_Blunt")))
        ),
        armor_heat=_percent_scale(
            _float_or_default(resolver.text_at(thing_def, ("statBases", "ArmorRating_Heat")))
        ),
        stuff_armor_multiplier=_float_or_default(
            resolver.text_at(thing_def, ("statBases", "StuffEffectMultiplierArmor"))
        ),
        modifier=_apparel_modifier(resolver, thing_def, label),
        supports_material=_supports_material(resolver, thing_def),
    )


def _parse_implant(
    resolver: ThingDefResolver,
    thing_def: RawThingDef,
    *,
    recipe_body_parts: dict[str, str] | None = None,
) -> VanillaImplantRecord:
    label = resolver.text_at(thing_def, ("label",)) or thing_def.def_name or "unnamed-implant"
    def_name = thing_def.def_name or label
    body_part_hint = _body_part_hint(def_name, label, (recipe_body_parts or {}).get(def_name))
    part_efficiency = _float_or_default(
        resolver.text_at(thing_def, ("addedPartProps", "partEfficiency")),
        0.0,
    )
    return VanillaImplantRecord(
        def_name=def_name,
        label=label,
        source_package=thing_def.source_package,
        root_path=thing_def.root_path,
        body_part_hint=body_part_hint,
        part_efficiency=part_efficiency,
        modifier=_implant_modifier(
            resolver,
            thing_def,
            label,
            body_part_hint=body_part_hint,
            part_efficiency=part_efficiency,
        ),
    )


def _parse_hediff_implant(
    resolver: HediffDefResolver,
    hediff_def: RawHediffDef,
    *,
    recipe_body_parts: dict[str, str] | None = None,
) -> VanillaImplantRecord:
    label = resolver.text_at(hediff_def, ("label",)) or hediff_def.def_name or "unnamed-implant"
    def_name = hediff_def.def_name or label
    body_part_hint = _body_part_hint(def_name, label, (recipe_body_parts or {}).get(def_name))
    part_efficiency = _float_or_default(
        resolver.text_at(hediff_def, ("addedPartProps", "partEfficiency")),
        0.0,
    )
    stage_node = _pick_default_stage(resolver, hediff_def)
    if stage_node is not None:
        part_efficiency += _float_or_default(_child_text(stage_node, "partEfficiencyOffset"), 0.0)
    return VanillaImplantRecord(
        def_name=def_name,
        label=label,
        source_package=hediff_def.source_package,
        root_path=hediff_def.root_path,
        body_part_hint=body_part_hint,
        part_efficiency=part_efficiency,
        modifier=_hediff_implant_modifier(
            resolver,
            hediff_def,
            label,
            body_part_hint=body_part_hint,
            part_efficiency=part_efficiency,
        ),
    )


def build_vanilla_catalog(game_data_root: Path) -> VanillaCatalog:
    thing_defs = _parse_raw_thing_defs(game_data_root)
    hediff_defs = _parse_raw_hediff_defs(game_data_root)
    recipe_defs = _parse_raw_recipe_defs(game_data_root)
    damage_defs = _parse_raw_damage_defs(game_data_root)

    resolver = ThingDefResolver(thing_defs)
    hediff_resolver = HediffDefResolver(hediff_defs)
    damage_resolver = DamageDefResolver(damage_defs)
    recipe_body_parts = _build_recipe_body_part_map(recipe_defs)
    thing_labels, hediff_labels = _load_simplified_language_labels(game_data_root)

    weapons: list[VanillaWeaponRecord] = []
    apparel: list[VanillaApparelRecord] = []
    implants_by_def_name: dict[str, VanillaImplantRecord] = {}

    for thing_def in thing_defs:
        if thing_def.abstract or not thing_def.def_name:
            continue

        if _is_ranged_weapon(resolver, thing_def):
            record = _parse_ranged_weapon(resolver, thing_def, damage_resolver)
            if record is not None:
                weapons.append(record)
            continue

        if _is_melee_weapon(resolver, thing_def):
            record = _parse_melee_weapon(resolver, thing_def)
            if record is not None:
                weapons.append(record)
            continue

        if _is_apparel(resolver, thing_def):
            record = _parse_apparel(resolver, thing_def)
            if record is not None:
                apparel.append(record)
            continue

        if _is_implant(resolver, thing_def):
            record = _parse_implant(resolver, thing_def, recipe_body_parts=recipe_body_parts)
            record.source_tag = _source_tag(record.root_path)
            translated_label = thing_labels.get(record.def_name)
            if translated_label:
                record.label = translated_label
            implants_by_def_name[record.def_name] = record

    for hediff_def in hediff_defs:
        if hediff_def.abstract or not hediff_def.def_name:
            continue
        if not _is_hediff_implant(hediff_resolver, hediff_def):
            continue
        record = _parse_hediff_implant(
            hediff_resolver,
            hediff_def,
            recipe_body_parts=recipe_body_parts,
        )
        record.source_tag = _source_tag(record.root_path)
        translated_label = hediff_labels.get(record.def_name) or thing_labels.get(record.def_name)
        if translated_label:
            record.label = translated_label
        implants_by_def_name[record.def_name] = record

    for record in weapons:
        record.source_tag = _source_tag(record.root_path)
        translated_label = thing_labels.get(record.def_name)
        if translated_label:
            record.label = translated_label

    for record in apparel:
        record.source_tag = _source_tag(record.root_path)
        translated_label = thing_labels.get(record.def_name)
        if translated_label:
            record.label = translated_label

    return VanillaCatalog(
        game_data_root=str(game_data_root),
        packages=[package.name for package in _package_dirs(game_data_root)],
        weapons=sorted(weapons, key=lambda weapon: (weapon.attack_mode, weapon.label.lower())),
        apparel=sorted(apparel, key=lambda item: item.label.lower()),
        implants=sorted(implants_by_def_name.values(), key=lambda item: item.label.lower()),
    )
