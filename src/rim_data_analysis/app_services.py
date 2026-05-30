from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

from rim_data_analysis.combat_engine import analyze_scenario
from rim_data_analysis.combat_io import load_scenario, scenario_from_dict, write_json
from rim_data_analysis.paths import discover_paths
from rim_data_analysis.reporting import write_inventory_report
from rim_data_analysis.scanner import build_inventory
from rim_data_analysis.scenario_library import analyze_library, load_scenario_library
from rim_data_analysis.scenario_library_reporting import write_scenario_library_report
from rim_data_analysis.vanilla_parser import build_vanilla_catalog
from rim_data_analysis.vanilla_reporting import write_vanilla_analysis


@dataclass(slots=True)
class SummaryCard:
    label: str
    value: str
    tone: str = "neutral"


@dataclass(slots=True)
class WorkflowResult:
    workflow_name: str
    title: str
    cards: list[SummaryCard] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    outputs: dict[str, Path] = field(default_factory=dict)


def _normalize_output_dir(output_dir: str | Path | None, default_path: Path) -> Path:
    if output_dir is None:
        return default_path
    if isinstance(output_dir, Path):
        return output_dir
    normalized = output_dir.strip()
    return Path(normalized) if normalized else default_path


def _normalize_optional_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    normalized = value.strip()
    return Path(normalized) if normalized else None


def _format_output_lines(outputs: dict[str, Path]) -> list[str]:
    return [f"{label}: {path}" for label, path in outputs.items()]


def run_inventory_workflow(
    *,
    output_dir: str | Path | None = None,
    game_data_root: str | Path | None = None,
    local_mods_root: str | Path | None = None,
    workshop_root: str | Path | None = None,
    save_data_root: str | Path | None = None,
) -> WorkflowResult:
    discovered = discover_paths()
    resolved_game_data_root = _normalize_optional_path(game_data_root) or discovered.game_data_root
    resolved_local_mods_root = _normalize_optional_path(local_mods_root) or discovered.local_mods_root
    resolved_workshop_root = _normalize_optional_path(workshop_root) or discovered.workshop_root
    resolved_save_data_root = _normalize_optional_path(save_data_root) or discovered.save_data_root
    resolved_output_dir = _normalize_output_dir(output_dir, Path("artifacts") / "gui-inventory")

    inventory = build_inventory(
        game_data_root=resolved_game_data_root,
        local_mods_root=resolved_local_mods_root,
        workshop_root=resolved_workshop_root,
        save_data_root=resolved_save_data_root,
    )
    outputs = write_inventory_report(resolved_output_dir, inventory)
    source_types = sorted({package.source_type for package in inventory.packages})
    top_def_type = "无"
    top_def_count = 0
    def_counter: dict[str, int] = {}
    for package in inventory.packages:
        for def_type, count in package.def_type_counts.items():
            def_counter[def_type] = def_counter.get(def_type, 0) + count
    if def_counter:
        top_def_type, top_def_count = max(def_counter.items(), key=lambda item: item[1])

    details = [
        f"扫描包数量: {len(inventory.packages)}",
        f"游戏 Data 路径: {inventory.game_data_root or '未发现'}",
        f"本地 Mods 路径: {inventory.local_mods_root or '未发现'}",
        f"Workshop 路径: {inventory.workshop_root or '未发现'}",
        f"存档路径: {inventory.save_data_root or '未发现'}",
        f"来源类型: {', '.join(source_types) if source_types else '无'}",
        f"最高频 Def 类型: {top_def_type} ({top_def_count})",
    ]
    details.extend(_format_output_lines(outputs))

    return WorkflowResult(
        workflow_name="inventory",
        title="包扫描完成",
        cards=[
            SummaryCard("包数量", str(len(inventory.packages))),
            SummaryCard("来源类型", str(len(source_types))),
            SummaryCard("最高频 Def", top_def_type),
            SummaryCard("输出文件", str(len(outputs))),
        ],
        details=details,
        outputs=outputs,
    )


def run_vanilla_workflow(
    *,
    game_data_root: str | Path,
    output_dir: str | Path | None = None,
    ranged_distance_cells: int = 18,
    shooting_skill: int = 12,
    melee_skill: int = 12,
) -> WorkflowResult:
    resolved_game_data_root = Path(game_data_root)
    resolved_output_dir = _normalize_output_dir(output_dir, Path("artifacts") / "gui-vanilla-analysis")

    catalog = build_vanilla_catalog(resolved_game_data_root)
    outputs = write_vanilla_analysis(
        resolved_output_dir,
        catalog,
        ranged_distance_cells=ranged_distance_cells,
        shooting_skill=shooting_skill,
        melee_skill=melee_skill,
    )

    details = [
        f"游戏 Data 路径: {catalog.game_data_root}",
        f"包数量: {len(catalog.packages)}",
        f"武器数量: {len(catalog.weapons)}",
        f"护具数量: {len(catalog.apparel)}",
        f"分析距离: {ranged_distance_cells} 格",
        f"射击技能: {shooting_skill}",
        f"近战技能: {melee_skill}",
    ]
    details.extend(_format_output_lines(outputs))

    return WorkflowResult(
        workflow_name="vanilla",
        title="原版目录分析完成",
        cards=[
            SummaryCard("包数量", str(len(catalog.packages))),
            SummaryCard("武器", str(len(catalog.weapons))),
            SummaryCard("护具", str(len(catalog.apparel))),
            SummaryCard("距离", f"{ranged_distance_cells} 格"),
        ],
        details=details,
        outputs=outputs,
    )


def run_scenario_workflow(
    *,
    scenario_path: str | Path,
    output_path: str | Path | None = None,
) -> WorkflowResult:
    resolved_scenario_path = Path(scenario_path)
    scenario = load_scenario(resolved_scenario_path)
    result = analyze_scenario(scenario)

    outputs: dict[str, Path] = {}
    if output_path is not None:
        resolved_output_path = Path(output_path)
        write_json(resolved_output_path, result.to_dict())
        outputs["analysis_json"] = resolved_output_path

    details = [
        f"场景: {result.scenario_name}",
        f"攻击模式: {result.accuracy.attack_mode}",
        f"穿戴合法: {'是' if result.can_wear_outfit else '否'}",
        f"最终命中率: {result.accuracy.final_hit_chance:.4f}",
        f"命中期望伤害: {result.damage.expected_damage_on_hit_after_defense:.4f}",
        f"期望 DPS: {result.damage.expected_dps:.4f}",
        f"理论 DPS: {result.damage.theoretical_dps:.4f}",
        f"护甲减伤率: {result.armor.reduction_rate_from_armor:.4f}",
        f"最终承伤倍率: {result.armor.total_damage_taken_multiplier:.4f}",
    ]
    if result.apparel_conflicts:
        details.append(f"护具冲突数量: {len(result.apparel_conflicts)}")
    details.extend(_format_output_lines(outputs))

    return WorkflowResult(
        workflow_name="scenario",
        title="单场景分析完成",
        cards=[
            SummaryCard("攻击模式", result.accuracy.attack_mode),
            SummaryCard("命中率", f"{result.accuracy.final_hit_chance:.4f}"),
            SummaryCard("期望 DPS", f"{result.damage.expected_dps:.4f}", tone="accent"),
            SummaryCard("穿戴合法", "是" if result.can_wear_outfit else "否", tone="good" if result.can_wear_outfit else "bad"),
        ],
        details=details,
        outputs=outputs,
    )


def load_scenario_payload(path: str | Path) -> dict[str, object]:
    resolved_path = Path(path)
    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("场景 JSON 根节点必须是对象。")
    scenario_from_dict(payload)
    return payload


def save_scenario_payload(
    *,
    payload: dict[str, object],
    output_path: str | Path,
) -> Path:
    scenario_from_dict(payload)
    resolved_output_path = Path(output_path)
    write_json(resolved_output_path, payload)
    return resolved_output_path


def run_scenario_payload_workflow(
    *,
    payload: dict[str, object],
    output_path: str | Path | None = None,
) -> WorkflowResult:
    scenario = scenario_from_dict(payload)
    result = analyze_scenario(scenario)

    outputs: dict[str, Path] = {}
    if output_path is not None:
        resolved_output_path = save_scenario_payload(payload=payload, output_path=output_path)
        outputs["scenario_json"] = resolved_output_path
        analysis_output_path = resolved_output_path.with_name(f"{resolved_output_path.stem}.analysis.json")
        write_json(analysis_output_path, result.to_dict())
        outputs["analysis_json"] = analysis_output_path

    details = [
        f"场景: {result.scenario_name}",
        f"攻击模式: {result.accuracy.attack_mode}",
        f"穿戴合法: {'是' if result.can_wear_outfit else '否'}",
        f"最终命中率: {result.accuracy.final_hit_chance:.4f}",
        f"命中期望伤害: {result.damage.expected_damage_on_hit_after_defense:.4f}",
        f"期望 DPS: {result.damage.expected_dps:.4f}",
        f"理论 DPS: {result.damage.theoretical_dps:.4f}",
        f"护甲减伤率: {result.armor.reduction_rate_from_armor:.4f}",
        f"最终承伤倍率: {result.armor.total_damage_taken_multiplier:.4f}",
    ]
    if result.apparel_conflicts:
        details.append(f"护具冲突数量: {len(result.apparel_conflicts)}")
    details.extend(_format_output_lines(outputs))

    return WorkflowResult(
        workflow_name="scenario_editor",
        title="场景编辑器分析完成",
        cards=[
            SummaryCard("攻击模式", result.accuracy.attack_mode),
            SummaryCard("命中率", f"{result.accuracy.final_hit_chance:.4f}"),
            SummaryCard("期望 DPS", f"{result.damage.expected_dps:.4f}", tone="accent"),
            SummaryCard(
                "穿戴合法",
                "是" if result.can_wear_outfit else "否",
                tone="good" if result.can_wear_outfit else "bad",
            ),
        ],
        details=details,
        outputs=outputs,
    )


def run_library_workflow(
    *,
    library_path: str | Path,
    game_data_root: str | Path,
    output_dir: str | Path | None = None,
    tags: list[str] | None = None,
    scenario_ids: list[str] | None = None,
    name_contains: str | None = None,
) -> WorkflowResult:
    resolved_library_path = Path(library_path)
    resolved_game_data_root = Path(game_data_root)
    resolved_output_dir = _normalize_output_dir(output_dir, Path("artifacts") / "gui-scenario-library")

    catalog = build_vanilla_catalog(resolved_game_data_root)
    library = load_scenario_library(resolved_library_path)
    records = analyze_library(
        library,
        catalog,
        required_tags=tags,
        scenario_ids=scenario_ids,
        name_contains=name_contains,
    )
    outputs = write_scenario_library_report(resolved_output_dir, records)

    ranged_count = sum(1 for record in records if record.attack_mode == "ranged")
    melee_count = sum(1 for record in records if record.attack_mode == "melee")
    average_dps = mean([record.analysis.damage.expected_dps for record in records]) if records else 0.0
    best_record = max(records, key=lambda record: record.analysis.damage.expected_dps) if records else None

    details = [
        f"场景库: {library.name}",
        f"场景数量: {len(records)}",
        f"远程场景: {ranged_count}",
        f"近战场景: {melee_count}",
        f"平均期望 DPS: {average_dps:.4f}",
        f"游戏 Data 路径: {catalog.game_data_root}",
    ]
    if tags:
        details.append(f"标签过滤: {', '.join(tags)}")
    if scenario_ids:
        details.append(f"场景 ID 过滤: {', '.join(scenario_ids)}")
    if name_contains:
        details.append(f"名称包含: {name_contains}")
    if best_record is not None:
        details.append(
            "最高期望 DPS: "
            f"{best_record.scenario_name} ({best_record.analysis.damage.expected_dps:.4f})"
        )
    details.extend(_format_output_lines(outputs))

    return WorkflowResult(
        workflow_name="library",
        title="场景库批量分析完成",
        cards=[
            SummaryCard("场景", str(len(records))),
            SummaryCard("远程", str(ranged_count)),
            SummaryCard("近战", str(melee_count)),
            SummaryCard("平均 DPS", f"{average_dps:.4f}", tone="accent"),
        ],
        details=details,
        outputs=outputs,
    )
