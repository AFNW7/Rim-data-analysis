from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from rim_data_analysis.vanilla_models import VanillaApparelRecord, VanillaCatalog, VanillaWeaponRecord


@dataclass(slots=True)
class RawThingDef:
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


def _weapon_tags(resolver: ThingDefResolver, thing_def: RawThingDef) -> list[str]:
    return resolver.list_at(thing_def, ("weaponTags",))


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


def _select_primary_tool(resolver: ThingDefResolver, thing_def: RawThingDef) -> ElementTree.Element | None:
    node = resolver.node_at(thing_def, ("tools",))
    if node is None:
        return None
    tools = [
        child
        for child in list(node)
        if isinstance(child.tag, str) and _child_text(child, "power") is not None
    ]
    if not tools:
        return None
    return max(tools, key=lambda tool: _float_or_default(_child_text(tool, "power"), 0.0))


def _damage_type_from_tool(tool: ElementTree.Element) -> str:
    capacities_node = tool.find("capacities")
    capacities = [
        child.text.strip()
        for child in list(capacities_node) if capacities_node is not None
        if child.text and child.text.strip()
    ]
    if any(capacity.lower() == "blunt" for capacity in capacities):
        return "Blunt"
    return "Sharp"


def _is_ranged_weapon(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    return _select_ranged_verb(resolver, thing_def) is not None


def _is_melee_weapon(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    if resolver.node_at(thing_def, ("apparel",)) is not None:
        return False
    if _select_primary_tool(resolver, thing_def) is None:
        return False
    tags = _weapon_tags(resolver, thing_def)
    categories = resolver.list_at(thing_def, ("thingCategories",))
    return "Weapons" in categories or bool(tags)


def _is_apparel(resolver: ThingDefResolver, thing_def: RawThingDef) -> bool:
    return resolver.node_at(thing_def, ("apparel",)) is not None


def _parse_ranged_weapon(
    resolver: ThingDefResolver,
    thing_def: RawThingDef,
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
        damage = _float_or_default(resolver.text_at(projectile, ("projectile", "damageAmountBase")))
        damage_type = _text_or_default(resolver.text_at(projectile, ("projectile", "damageDef")), "Sharp")
        armor_penetration = _percent_scale(
            _float_or_default(resolver.text_at(projectile, ("projectile", "armorPenetrationBase")))
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
    )


def _parse_melee_weapon(
    resolver: ThingDefResolver,
    thing_def: RawThingDef,
) -> VanillaWeaponRecord | None:
    tool = _select_primary_tool(resolver, thing_def)
    if tool is None:
        return None

    capacities_node = tool.find("capacities")
    capacities = [
        child.text.strip()
        for child in list(capacities_node) if capacities_node is not None
        if child.text and child.text.strip()
    ]
    label = resolver.text_at(thing_def, ("label",)) or thing_def.def_name or "unnamed-weapon"
    return VanillaWeaponRecord(
        def_name=thing_def.def_name or label,
        label=label,
        source_package=thing_def.source_package,
        root_path=thing_def.root_path,
        attack_mode="melee",
        damage_type=_damage_type_from_tool(tool),
        damage=_float_or_default(_child_text(tool, "power")),
        armor_penetration=_percent_scale(_float_or_default(_child_text(tool, "armorPenetration"))),
        cooldown_seconds=_float_or_default(_child_text(tool, "cooldownTime"), 2.0),
        warmup_seconds=0.0,
        burst_shot_count=1,
        burst_shot_interval_seconds=0.0,
        accuracy_close=1.0,
        accuracy_short=1.0,
        accuracy_medium=1.0,
        accuracy_long=1.0,
        projectile_def=None,
        primary_tool_label=_child_text(tool, "label"),
        primary_tool_capacities=capacities,
        tags=_weapon_tags(resolver, thing_def),
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
    )


def build_vanilla_catalog(game_data_root: Path) -> VanillaCatalog:
    thing_defs = _parse_raw_thing_defs(game_data_root)
    resolver = ThingDefResolver(thing_defs)

    weapons: list[VanillaWeaponRecord] = []
    apparel: list[VanillaApparelRecord] = []

    for thing_def in thing_defs:
        if thing_def.abstract or not thing_def.def_name:
            continue

        if _is_ranged_weapon(resolver, thing_def):
            record = _parse_ranged_weapon(resolver, thing_def)
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

    return VanillaCatalog(
        game_data_root=str(game_data_root),
        packages=[package.name for package in _package_dirs(game_data_root)],
        weapons=sorted(weapons, key=lambda weapon: (weapon.attack_mode, weapon.label.lower())),
        apparel=sorted(apparel, key=lambda item: item.label.lower()),
    )
