from __future__ import annotations

from collections import Counter
from math import prod

from rim_data_analysis.combat_constants import DISTANCE_BANDS, LAYER_PRIORITY, SHOOTING_ACCURACY_CURVE_POINTS
from rim_data_analysis.combat_models import (
    AccuracyResult,
    ApparelConflict,
    ApparelProfile,
    ArmorLayerSnapshot,
    ArmorResolutionResult,
    CombatAnalysisResult,
    CombatScenario,
    DamageSummary,
    PawnCombatProfile,
    WeaponProfile,
)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _trait_names(pawn: PawnCombatProfile) -> set[str]:
    return {trait.strip().lower() for trait in pawn.traits}


def _bounded_capacity(value: float, *, upper: float = 2.0) -> float:
    return _clamp(value, 0.1, upper)


def _ranged_accuracy_sight_multiplier(pawn: PawnCombatProfile) -> float:
    sight = _bounded_capacity(pawn.capacities.sight)
    return _clamp(0.6 + 0.4 * sight, 0.45, 1.35)


def _ranged_aiming_sight_multiplier(pawn: PawnCombatProfile) -> float:
    sight = _bounded_capacity(pawn.capacities.sight)
    return _clamp(1.25 - 0.25 * sight, 0.7, 1.3)


def _ranged_aiming_manipulation_multiplier(pawn: PawnCombatProfile) -> float:
    manipulation = _bounded_capacity(pawn.capacities.manipulation)
    return _clamp(1.25 - 0.25 * manipulation, 0.7, 1.35)


def _ranged_cooldown_manipulation_multiplier(pawn: PawnCombatProfile) -> float:
    manipulation = _bounded_capacity(pawn.capacities.manipulation)
    return _clamp(1.2 - 0.2 * manipulation, 0.72, 1.35)


def _shooting_accuracy_stat_value(pawn: PawnCombatProfile) -> float:
    skill = float(pawn.shooting_skill)
    stat_value = skill
    traits = _trait_names(pawn)
    if "careful_shooter" in traits:
        stat_value += 5.0
    if "trigger_happy" in traits:
        stat_value -= 5.0
    stat_value += (_bounded_capacity(pawn.capacities.sight) - 1.0) * 12.0
    stat_value += (min(_bounded_capacity(pawn.capacities.manipulation), 1.0) - 1.0) * 8.0
    if pawn.modifiers:
        stat_value += sum(mod.shooting_accuracy_stat_offset for mod in pawn.modifiers)
        stat_value += sum(mod.shooting_skill_offset for mod in pawn.modifiers)
    return stat_value


def _curve_value(points: tuple[tuple[float, float], ...], score: float) -> float:
    if score <= points[0][0]:
        return points[0][1]
    if score >= points[-1][0]:
        return points[-1][1]
    for (left_x, left_y), (right_x, right_y) in zip(points, points[1:]):
        if left_x <= score <= right_x:
            if right_x == left_x:
                return right_y
            ratio = (score - left_x) / (right_x - left_x)
            return left_y + (right_y - left_y) * ratio
    return points[-1][1]


def compute_shooting_accuracy_per_tile(pawn: PawnCombatProfile) -> float:
    if pawn.shooting_accuracy_per_tile_override is not None:
        return _clamp(pawn.shooting_accuracy_per_tile_override, 0.01, 0.9999)

    stat_value = _shooting_accuracy_stat_value(pawn)
    base = _curve_value(SHOOTING_ACCURACY_CURVE_POINTS, stat_value)
    multiplier = prod(mod.shooting_accuracy_multiplier for mod in pawn.modifiers) if pawn.modifiers else 1.0
    offset = sum(mod.shooting_accuracy_per_tile_offset for mod in pawn.modifiers)
    return _clamp(
        base * multiplier + offset,
        0.01,
        0.9999,
    )


def compute_aiming_time_multiplier(pawn: PawnCombatProfile) -> float:
    traits = _trait_names(pawn)
    stat_value = 1.0
    if "careful_shooter" in traits:
        stat_value += 0.25
    if "trigger_happy" in traits:
        stat_value -= 0.5
    if pawn.modifiers:
        stat_value += sum(mod.aiming_time_stat_offset for mod in pawn.modifiers)
    multiplier = max(stat_value, 0.01)
    for modifier in pawn.modifiers:
        multiplier *= modifier.aiming_time_multiplier
    return max(multiplier, 0.01)


def compute_ranged_cooldown_multiplier(pawn: PawnCombatProfile) -> float:
    stat_value = 1.0
    stat_value += sum(mod.ranged_cooldown_stat_offset for mod in pawn.modifiers)
    multiplier = max(stat_value, 0.01)
    for modifier in pawn.modifiers:
        multiplier *= modifier.ranged_cooldown_multiplier
    return max(multiplier, 0.01)


def compute_incoming_damage_multiplier(pawn: PawnCombatProfile) -> float:
    traits = _trait_names(pawn)
    multiplier = 1.0
    if "tough" in traits:
        multiplier *= 0.5
    for modifier in pawn.modifiers:
        multiplier *= modifier.incoming_damage_multiplier
    return max(multiplier, 0.0)


def compute_armor_penetration(weapon: WeaponProfile, attacker: PawnCombatProfile) -> float:
    multiplier = prod(mod.armor_penetration_multiplier for mod in attacker.modifiers) if attacker.modifiers else 1.0
    return max(weapon.armor_penetration * multiplier, 0.0)


def _melee_hit_curve(score: float) -> float:
    if score <= -20:
        return 0.05
    if score <= -10:
        return 0.10 + (score + 10.0) * 0.005
    if score <= 0:
        return 0.10 + (score + 10.0) * 0.04
    if score <= 10:
        return 0.50 + score * 0.03
    if score <= 20:
        return 0.80 + (score - 10.0) * 0.01
    if score <= 40:
        return 0.90 + (score - 20.0) * 0.003
    if score <= 60:
        return 0.96 + (score - 40.0) * 0.001
    return 0.98


def _melee_dodge_curve(score: float) -> float:
    if score <= 5:
        return 0.0
    if score <= 20:
        return (score - 5.0) * 0.02
    if score <= 60:
        return 0.30 + (score - 20.0) * 0.005
    return 0.50


def compute_melee_hit_chance(pawn: PawnCombatProfile) -> float:
    if pawn.melee_hit_chance_override is not None:
        return _clamp(pawn.melee_hit_chance_override, 0.0, 1.0)

    traits = _trait_names(pawn)
    sight = min(pawn.capacities.sight, 1.5)
    manipulation = min(pawn.capacities.manipulation, 1.5)

    score = float(pawn.melee_skill)
    score += 12.0 * (sight - 1.0)
    score += 12.0 * (manipulation - 1.0)
    if "brawler" in traits:
        score += 4.0
    score += sum(mod.melee_hit_score_offset for mod in pawn.modifiers)

    chance = _melee_hit_curve(score)
    chance += sum(mod.melee_hit_chance_offset for mod in pawn.modifiers)
    if pawn.modifiers:
        chance *= prod(mod.melee_hit_chance_multiplier for mod in pawn.modifiers)
    return _clamp(chance, 0.0, 1.0)


def compute_melee_dodge_chance(
    pawn: PawnCombatProfile,
    *,
    target_is_aiming_or_firing: bool = False,
) -> float:
    if target_is_aiming_or_firing:
        return 0.0

    if pawn.melee_dodge_chance_override is not None:
        return _clamp(pawn.melee_dodge_chance_override, 0.0, 0.8)

    traits = _trait_names(pawn)
    sight = min(pawn.capacities.sight, 1.4)
    score = float(pawn.melee_skill)
    score += 18.0 * (pawn.capacities.moving - 1.0)
    score += 8.0 * (sight - 1.0)
    if "nimble" in traits:
        score += 15.0
    score += sum(mod.melee_dodge_score_offset for mod in pawn.modifiers)

    chance = _melee_dodge_curve(score)
    chance += sum(mod.melee_dodge_chance_offset for mod in pawn.modifiers)
    if pawn.modifiers:
        chance *= prod(mod.melee_dodge_chance_multiplier for mod in pawn.modifiers)
    return _clamp(chance, 0.0, 0.8)


def _normalize_layers(layers: list[str]) -> list[str]:
    return [layer.strip().lower() for layer in layers]


def find_apparel_conflicts(apparel_items: list[ApparelProfile]) -> list[ApparelConflict]:
    conflicts: list[ApparelConflict] = []
    for index, first in enumerate(apparel_items):
        for second in apparel_items[index + 1 :]:
            shared_layers = sorted(set(_normalize_layers(first.layers)) & set(_normalize_layers(second.layers)))
            shared_regions = sorted(set(first.covers) & set(second.covers))
            if shared_layers and shared_regions:
                conflicts.append(
                    ApparelConflict(
                        first_item=first.name,
                        second_item=second.name,
                        shared_layers=shared_layers,
                        shared_regions=shared_regions,
                    )
                )
    return conflicts


def _layer_priority(apparel: ApparelProfile) -> int:
    if apparel.layer_priority_override is not None:
        return apparel.layer_priority_override
    priorities = [LAYER_PRIORITY.get(layer, 0) for layer in _normalize_layers(apparel.layers)]
    return max(priorities) if priorities else 0


def _armor_value_for_damage_type(apparel: ApparelProfile, damage_type: str) -> float:
    normalized = damage_type.strip().lower()
    if normalized == "sharp":
        return apparel.armor_sharp
    if normalized == "heat":
        return apparel.armor_heat
    return apparel.armor_blunt


def _armor_event_probabilities(effective_armor: float) -> tuple[float, float, float]:
    if effective_armor <= 0:
        return 0.0, 0.0, 1.0
    deflect = _clamp(effective_armor / 200.0, 0.0, 1.0)
    no_effect = _clamp(1.0 - min(effective_armor, 100.0) / 100.0, 0.0, 1.0)
    half = _clamp(1.0 - deflect - no_effect, 0.0, 1.0)
    return deflect, half, no_effect


def _relevant_layers(defender: PawnCombatProfile, body_region: str) -> list[ApparelProfile]:
    items = [apparel for apparel in defender.apparel if body_region in apparel.covers]
    return sorted(items, key=_layer_priority, reverse=True)


def resolve_armor(
    defender: PawnCombatProfile,
    weapon: WeaponProfile,
    *,
    body_region: str,
    attacker: PawnCombatProfile | None = None,
) -> ArmorResolutionResult:
    applicable_layers = _relevant_layers(defender, body_region)
    final_multiplier = compute_incoming_damage_multiplier(defender)
    attack_damage_type = weapon.damage_type
    effective_ap = compute_armor_penetration(weapon, attacker) if attacker else weapon.armor_penetration

    snapshots: list[ArmorLayerSnapshot] = []
    for apparel in applicable_layers:
        armor_value = _armor_value_for_damage_type(apparel, attack_damage_type)
        effective_armor = armor_value - effective_ap
        deflect, half, full = _armor_event_probabilities(effective_armor)
        snapshots.append(
            ArmorLayerSnapshot(
                apparel_name=apparel.name,
                source=apparel.source,
                applicable_layers=apparel.layers,
                applicable_regions=apparel.covers,
                armor_value=armor_value,
                effective_armor=effective_armor,
                local_deflect_chance=deflect,
                local_half_chance=half,
                local_full_damage_chance=full,
            )
        )

    outcomes: list[tuple[float, float, str]] = []

    def walk(layer_index: int, current_damage: float, sharp_mitigated: bool, probability: float) -> None:
        if probability <= 0.0:
            return
        if current_damage <= 0.0 or layer_index >= len(applicable_layers):
            final_type = attack_damage_type
            if attack_damage_type.strip().lower() == "sharp" and sharp_mitigated and current_damage > 0.0:
                final_type = "Blunt"
            outcomes.append((probability, current_damage, final_type))
            return

        apparel = applicable_layers[layer_index]
        armor_value = _armor_value_for_damage_type(apparel, attack_damage_type)
        effective_armor = armor_value - effective_ap
        deflect, half, full = _armor_event_probabilities(effective_armor)

        walk(layer_index + 1, 0.0, True, probability * deflect)
        walk(layer_index + 1, current_damage * 0.5, True, probability * half)
        walk(layer_index + 1, current_damage, sharp_mitigated, probability * full)

    walk(0, weapon.damage, False, 1.0)

    damage_by_type: Counter[str] = Counter()
    expected_damage_after_armor = 0.0
    for probability, damage, final_type in outcomes:
        damage_by_type[final_type] += probability * damage
        expected_damage_after_armor += probability * damage

    expected_damage_after_final_multiplier = expected_damage_after_armor * final_multiplier
    reduction_rate = 0.0 if weapon.damage <= 0 else 1.0 - (expected_damage_after_armor / weapon.damage)

    return ArmorResolutionResult(
        original_damage_type=attack_damage_type,
        final_damage_distribution=dict(sorted(damage_by_type.items())),
        expected_damage_after_armor=expected_damage_after_armor,
        expected_damage_after_final_multiplier=expected_damage_after_final_multiplier,
        reduction_rate_from_armor=_clamp(reduction_rate, 0.0, 1.0),
        total_damage_taken_multiplier=final_multiplier,
        layers=snapshots,
    )


def _weapon_accuracy_band(distance_cells: int) -> str:
    for upper_bound, band in DISTANCE_BANDS:
        if distance_cells <= upper_bound:
            return band
    return "long"


def _lerp(start: float, end: float, ratio: float) -> float:
    return start + (end - start) * ratio


def _weapon_accuracy_value(weapon: WeaponProfile, distance_cells: int) -> tuple[str, float]:
    band = _weapon_accuracy_band(distance_cells)
    if distance_cells <= 3:
        return band, weapon.accuracy_close
    if distance_cells < 12:
        ratio = (distance_cells - 3) / 9.0
        return band, _lerp(weapon.accuracy_close, weapon.accuracy_short, ratio)
    if distance_cells < 25:
        ratio = (distance_cells - 12) / 13.0
        return band, _lerp(weapon.accuracy_short, weapon.accuracy_medium, ratio)
    if distance_cells < 40:
        ratio = (distance_cells - 25) / 15.0
        return band, _lerp(weapon.accuracy_medium, weapon.accuracy_long, ratio)
    return band, weapon.accuracy_long


def _target_size_factor(body_size: float) -> float:
    return _clamp(body_size, 0.5, 2.0)


def compute_accuracy_result(scenario: CombatScenario) -> AccuracyResult:
    weapon = scenario.weapon
    context = scenario.context

    if weapon.attack_mode == "ranged":
        pawn_accuracy = compute_shooting_accuracy_per_tile(scenario.attacker)
        band, weapon_accuracy = _weapon_accuracy_value(weapon, context.distance_cells)
        target_size = _target_size_factor(scenario.defender.body_size)
        raw_hit = (
            (pawn_accuracy**context.distance_cells)
            * weapon_accuracy
            * target_size
            * context.weather_accuracy_multiplier
            * context.smoke_accuracy_multiplier
            * context.hit_chance_multiplier
        )
        raw_hit += context.combat_in_darkness_accuracy_offset
        raw_hit = _clamp(raw_hit, 0.0, 1.0)
        final_hit = raw_hit * (1.0 - _clamp(context.cover_block_chance, 0.0, 1.0))
        return AccuracyResult(
            attack_mode="ranged",
            raw_hit_chance_before_cover=raw_hit,
            cover_block_chance=_clamp(context.cover_block_chance, 0.0, 1.0),
            final_hit_chance=_clamp(final_hit, 0.0, 1.0),
            accuracy_band=band,
            attacker_shooting_accuracy_per_tile=pawn_accuracy,
            weapon_accuracy_at_distance=weapon_accuracy,
            target_size_factor=target_size,
            weather_accuracy_multiplier=context.weather_accuracy_multiplier,
            smoke_accuracy_multiplier=context.smoke_accuracy_multiplier,
            combat_in_darkness_accuracy_offset=context.combat_in_darkness_accuracy_offset,
            hit_chance_multiplier=context.hit_chance_multiplier,
            attacker_melee_hit_chance=None,
            defender_melee_dodge_chance=None,
        )

    attacker_hit = compute_melee_hit_chance(scenario.attacker)
    defender_dodge = compute_melee_dodge_chance(
        scenario.defender,
        target_is_aiming_or_firing=context.target_is_aiming_or_firing,
    )
    final_hit = attacker_hit * (1.0 - defender_dodge) * context.hit_chance_multiplier
    return AccuracyResult(
        attack_mode="melee",
        raw_hit_chance_before_cover=_clamp(attacker_hit, 0.0, 1.0),
        cover_block_chance=0.0,
        final_hit_chance=_clamp(final_hit, 0.0, 1.0),
        accuracy_band=None,
        attacker_shooting_accuracy_per_tile=None,
        weapon_accuracy_at_distance=None,
        target_size_factor=None,
        weather_accuracy_multiplier=None,
        smoke_accuracy_multiplier=None,
        combat_in_darkness_accuracy_offset=None,
        hit_chance_multiplier=context.hit_chance_multiplier,
        attacker_melee_hit_chance=attacker_hit,
        defender_melee_dodge_chance=defender_dodge,
    )


def _weapon_cycle_seconds(weapon: WeaponProfile, attacker: PawnCombatProfile) -> float:
    if weapon.attack_mode == "ranged":
        warmup = weapon.warmup_seconds * compute_aiming_time_multiplier(attacker)
        cooldown = weapon.cooldown_seconds * compute_ranged_cooldown_multiplier(attacker)
        burst = max(weapon.burst_shot_count - 1, 0) * weapon.burst_shot_interval_seconds
        return max(warmup + cooldown + burst, 0.01)
    return max(weapon.cooldown_seconds, 0.01)


def _melee_damage_multiplier(attacker: PawnCombatProfile) -> float:
    return max(prod(mod.melee_damage_multiplier for mod in attacker.modifiers), 0.0) if attacker.modifiers else 1.0


def _effective_melee_weapon(weapon: WeaponProfile, attacker: PawnCombatProfile) -> WeaponProfile:
    damage_multiplier = _melee_damage_multiplier(attacker)
    melee_attack_options = [
        type(option)(
            label=option.label,
            damage_type=option.damage_type,
            damage=option.damage * damage_multiplier,
            armor_penetration=option.armor_penetration,
            cooldown_seconds=option.cooldown_seconds,
            chance_factor=option.chance_factor,
            capacities=list(option.capacities),
        )
        for option in weapon.melee_attack_options
    ]
    return WeaponProfile(
        name=weapon.name,
        attack_mode=weapon.attack_mode,
        damage_type=weapon.damage_type,
        damage=weapon.damage * damage_multiplier,
        armor_penetration=weapon.armor_penetration,
        warmup_seconds=weapon.warmup_seconds,
        cooldown_seconds=weapon.cooldown_seconds,
        burst_shot_count=weapon.burst_shot_count,
        burst_shot_interval_seconds=weapon.burst_shot_interval_seconds,
        accuracy_close=weapon.accuracy_close,
        accuracy_short=weapon.accuracy_short,
        accuracy_medium=weapon.accuracy_medium,
        accuracy_long=weapon.accuracy_long,
        melee_attack_options=melee_attack_options,
    )


def _melee_initial_selection_weight(weapon: WeaponProfile) -> float:
    cooldown = max(weapon.cooldown_seconds, 0.01)
    return max(weapon.damage, 0.0) * (1.0 + max(weapon.armor_penetration, 0.0) / 100.0) / cooldown


def _weighted_melee_profiles(weapon: WeaponProfile) -> list[tuple[WeaponProfile, float]]:
    if not weapon.melee_attack_options:
        return [(weapon, 1.0)]

    attack_profiles: list[tuple[WeaponProfile, float]] = []
    for option in weapon.melee_attack_options:
        attack_profiles.append(
            (
                WeaponProfile(
                    name=f"{weapon.name}:{option.label}",
                    attack_mode="melee",
                    damage_type=option.damage_type,
                    damage=option.damage,
                    armor_penetration=option.armor_penetration,
                    cooldown_seconds=option.cooldown_seconds,
                ),
                max(option.chance_factor, 0.0),
            )
        )

    weighted_candidates = [
        (attack, chance_factor * _melee_initial_selection_weight(attack))
        for attack, chance_factor in attack_profiles
    ]
    highest_weight = max((weight for _, weight in weighted_candidates), default=0.0)
    if highest_weight <= 0.0:
        equal_share = 1.0 / max(len(weighted_candidates), 1)
        return [(attack, equal_share) for attack, _ in weighted_candidates]

    grouped: dict[str, list[tuple[WeaponProfile, float]]] = {
        "best": [],
        "mid": [],
        "worst": [],
    }
    for attack, weight in weighted_candidates:
        ratio = weight / highest_weight
        if ratio > 0.95:
            grouped["best"].append((attack, weight))
        elif ratio >= 0.75:
            grouped["mid"].append((attack, weight))
        else:
            grouped["worst"].append((attack, weight))

    final_weights: list[tuple[WeaponProfile, float]] = []
    for bucket, share in (("best", 0.75), ("mid", 0.25), ("worst", 0.05)):
        bucket_items = grouped[bucket]
        bucket_total = sum(weight for _, weight in bucket_items)
        if bucket_total <= 0.0:
            continue
        for attack, weight in bucket_items:
            final_weights.append((attack, share * (weight / bucket_total)))

    normalization = sum(weight for _, weight in final_weights)
    if normalization <= 0.0:
        equal_share = 1.0 / max(len(weighted_candidates), 1)
        return [(attack, equal_share) for attack, _ in weighted_candidates]
    return [(attack, weight / normalization) for attack, weight in final_weights]


def _combine_armor_results(
    attack_results: list[tuple[ArmorResolutionResult, float]],
    *,
    weighted_raw_damage_on_hit: float,
) -> ArmorResolutionResult:
    if not attack_results:
        return ArmorResolutionResult(
            original_damage_type="Sharp",
            final_damage_distribution={},
            expected_damage_after_armor=0.0,
            expected_damage_after_final_multiplier=0.0,
            reduction_rate_from_armor=0.0,
            total_damage_taken_multiplier=1.0,
            layers=[],
        )

    damage_distribution: Counter[str] = Counter()
    original_damage_types: set[str] = set()
    layer_totals: dict[tuple[str, str], dict[str, object]] = {}
    expected_damage_after_armor = 0.0
    expected_damage_after_final_multiplier = 0.0
    total_damage_taken_multiplier = 0.0

    for result, weight in attack_results:
        original_damage_types.add(result.original_damage_type)
        expected_damage_after_armor += result.expected_damage_after_armor * weight
        expected_damage_after_final_multiplier += result.expected_damage_after_final_multiplier * weight
        total_damage_taken_multiplier += result.total_damage_taken_multiplier * weight
        for damage_type, expected_damage in result.final_damage_distribution.items():
            damage_distribution[damage_type] += expected_damage * weight
        for layer in result.layers:
            key = (layer.apparel_name, layer.source)
            bucket = layer_totals.setdefault(
                key,
                {
                    "applicable_layers": list(layer.applicable_layers),
                    "applicable_regions": list(layer.applicable_regions),
                    "armor_value": 0.0,
                    "effective_armor": 0.0,
                    "local_deflect_chance": 0.0,
                    "local_half_chance": 0.0,
                    "local_full_damage_chance": 0.0,
                },
            )
            bucket["armor_value"] += layer.armor_value * weight
            bucket["effective_armor"] += layer.effective_armor * weight
            bucket["local_deflect_chance"] += layer.local_deflect_chance * weight
            bucket["local_half_chance"] += layer.local_half_chance * weight
            bucket["local_full_damage_chance"] += layer.local_full_damage_chance * weight

    layers = [
        ArmorLayerSnapshot(
            apparel_name=apparel_name,
            source=source,
            applicable_layers=list(payload["applicable_layers"]),
            applicable_regions=list(payload["applicable_regions"]),
            armor_value=float(payload["armor_value"]),
            effective_armor=float(payload["effective_armor"]),
            local_deflect_chance=float(payload["local_deflect_chance"]),
            local_half_chance=float(payload["local_half_chance"]),
            local_full_damage_chance=float(payload["local_full_damage_chance"]),
        )
        for (apparel_name, source), payload in layer_totals.items()
    ]
    reduction_rate = 0.0
    if weighted_raw_damage_on_hit > 0.0:
        reduction_rate = 1.0 - (expected_damage_after_armor / weighted_raw_damage_on_hit)
    return ArmorResolutionResult(
        original_damage_type=original_damage_types.pop() if len(original_damage_types) == 1 else "Mixed",
        final_damage_distribution=dict(sorted(damage_distribution.items())),
        expected_damage_after_armor=expected_damage_after_armor,
        expected_damage_after_final_multiplier=expected_damage_after_final_multiplier,
        reduction_rate_from_armor=_clamp(reduction_rate, 0.0, 1.0),
        total_damage_taken_multiplier=max(total_damage_taken_multiplier, 0.0),
        layers=layers,
    )


def analyze_scenario(scenario: CombatScenario) -> CombatAnalysisResult:
    conflicts = find_apparel_conflicts(scenario.defender.apparel)
    accuracy = compute_accuracy_result(scenario)

    effective_weapon = scenario.weapon
    if scenario.weapon.attack_mode == "melee":
        effective_weapon = _effective_melee_weapon(scenario.weapon, scenario.attacker)

    if effective_weapon.attack_mode == "melee":
        weighted_attacks = _weighted_melee_profiles(effective_weapon)
        raw_damage_on_hit = sum(attack.damage * weight for attack, weight in weighted_attacks)
        cycle_seconds = sum(max(attack.cooldown_seconds, 0.01) * weight for attack, weight in weighted_attacks)
        armor = _combine_armor_results(
            [
                (
                    resolve_armor(
                        scenario.defender,
                        attack,
                        body_region=scenario.context.target_body_region,
                        attacker=scenario.attacker,
                    ),
                    weight,
                )
                for attack, weight in weighted_attacks
            ],
            weighted_raw_damage_on_hit=raw_damage_on_hit,
        )
        shots_per_cycle = 1
        expected_damage_on_hit_after_defense = armor.expected_damage_after_final_multiplier
    else:
        armor = resolve_armor(
            scenario.defender,
            effective_weapon,
            body_region=scenario.context.target_body_region,
            attacker=scenario.attacker,
        )
        cycle_seconds = _weapon_cycle_seconds(scenario.weapon, scenario.attacker)
        shots_per_cycle = max(scenario.weapon.burst_shot_count, 1)
        raw_damage_on_hit = effective_weapon.damage * shots_per_cycle
        expected_damage_on_hit_after_defense = armor.expected_damage_after_final_multiplier * shots_per_cycle

    expected_damage_per_attack_cycle = accuracy.final_hit_chance * expected_damage_on_hit_after_defense
    theoretical_dps = raw_damage_on_hit / cycle_seconds
    expected_dps = expected_damage_per_attack_cycle / cycle_seconds
    realized_ratio = 0.0 if theoretical_dps <= 0 else expected_dps / theoretical_dps

    damage = DamageSummary(
        raw_damage_on_hit=raw_damage_on_hit,
        expected_damage_on_hit_after_defense=expected_damage_on_hit_after_defense,
        expected_damage_per_attack_cycle=expected_damage_per_attack_cycle,
        theoretical_dps=theoretical_dps,
        expected_dps=expected_dps,
        realized_dps_ratio=realized_ratio,
    )

    return CombatAnalysisResult(
        scenario_name=scenario.name,
        attacker=scenario.attacker.to_dict(),
        defender=scenario.defender.to_dict(),
        weapon=scenario.weapon.to_dict(),
        context=scenario.context.to_dict(),
        can_wear_outfit=not conflicts,
        apparel_conflicts=conflicts,
        accuracy=accuracy,
        armor=armor,
        damage=damage,
    )
