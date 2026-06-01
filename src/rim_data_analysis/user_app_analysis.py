from __future__ import annotations

from math import prod

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
from rim_data_analysis.user_app_catalog import CatalogIndex
from rim_data_analysis.user_app_models import (
    ComparisonRow,
    EquipmentChoice,
    FirepowerPreview,
    FirepowerPreviewTarget,
    SavedPawnTemplate,
    SavedScenarioTemplate,
)
from rim_data_analysis.user_app_options import (
    FEATURE_BY_ID,
    FULL_BODY_ARMOR_COVERS,
    IMPLANT_BY_ID,
    MATERIAL_BY_ID,
    QUALITY_BY_ID,
    REFERENCE_ARMOR_TARGETS,
    RANGED_PREVIEW_DISTANCE_CHOICES,
    SPECIES_BY_ID,
    SUPPORT_GEAR_BY_ID,
    WEAPON_QUALITY_RULES_BY_ID,
)
from rim_data_analysis.vanilla_models import (
    VanillaApparelRecord,
    VanillaImplantRecord,
    VanillaWeaponRecord,
)


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
