from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from typing import TYPE_CHECKING

from rim_data_analysis.paths import discover_paths
from rim_data_analysis.user_app_data import (
    ComparisonRow,
    ImportSettings,
    SavedScenarioTemplate,
    load_catalog_index,
)

if TYPE_CHECKING:
    from rim_data_analysis.desktop_user_app import RimDataAnalysisDesktopApp


def build_compare_page(app: RimDataAnalysisDesktopApp) -> None:
    page = app.compare_page
    page.grid_rowconfigure(0, weight=1)
    page.grid_columnconfigure(1, weight=1)

    sidebar_shell, sidebar = app._scrollable_sidebar(page, width=330, padx=18, pady=18)
    sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=4)

    main = app._panel(page, padx=18, pady=18)
    main.grid(row=0, column=1, sticky="nsew", pady=4)
    main.grid_rowconfigure(2, weight=1)
    main.grid_columnconfigure(0, weight=1)

    tk.Label(sidebar, text="场景导入", bg=app.colors["panel"], fg=app.colors["ink"], font=("Bahnschrift", 18, "bold")).pack(anchor="w")
    tk.Label(sidebar, textvariable=app.compare_status_var, bg=app.colors["panel"], fg=app.colors["muted"], justify="left", wraplength=280, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 12))
    app._labeled_entry(sidebar, "筛选场景", app.compare_filter_var)
    app.compare_filter_var.trace_add("write", lambda *_args: app._refresh_compare_source_list())
    app.compare_source_listbox = app._simple_listbox(sidebar, height=20, selectmode=tk.MULTIPLE)
    app.compare_source_listbox.pack(fill="both", expand=True, pady=(8, 0))
    app._bind_toggle_multiselect(
        app.compare_source_listbox,
        double_click_callback=app._analyze_compare_scenario_at_index,
    )

    action_column = tk.Frame(sidebar, bg=app.colors["panel"])
    action_column.pack(fill="x", pady=(10, 0))
    ttk.Button(action_column, text="加入选中场景", style="Primary.TButton", command=app._analyze_selected_compare_scenarios).pack(fill="x", pady=(0, 6))
    ttk.Button(action_column, text="分析全部场景", style="Subtle.TButton", command=app._analyze_all_compare_scenarios).pack(fill="x", pady=(0, 6))
    ttk.Button(action_column, text="清空对比表", style="Subtle.TButton", command=app._clear_compare_rows).pack(fill="x", pady=(0, 6))
    ttk.Button(action_column, text="保存本次结果", style="Subtle.TButton", command=app._save_compare_rows).pack(fill="x")

    flow_card = tk.Frame(sidebar, bg=app.colors["panel_alt"], padx=12, pady=12, highlightthickness=1, highlightbackground=app.colors["line"])
    flow_card.pack(fill="x", pady=(12, 0))
    tk.Label(flow_card, text="当前步骤", bg=app.colors["panel_alt"], fg=app.colors["accent"], font=("Bahnschrift", 12, "bold")).pack(anchor="w")
    tk.Label(flow_card, textvariable=app.compare_flow_var, bg=app.colors["panel_alt"], fg=app.colors["ink"], justify="left", wraplength=280, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 10))
    app.compare_to_scenario_button = ttk.Button(flow_card, text="返回场景设计", style="Subtle.TButton", command=lambda: app.notebook.select(app.scenario_page))
    app.compare_to_scenario_button.pack(fill="x")

    tk.Label(main, text="结果对比表", bg=app.colors["panel"], fg=app.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
    tk.Label(main, text="点击表头即可按该列升序或降序排序。", bg=app.colors["panel"], fg=app.colors["muted"], font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 14))

    table_shell = tk.Frame(main, bg=app.colors["panel"])
    table_shell.grid(row=2, column=0, sticky="nsew")
    table_shell.grid_rowconfigure(0, weight=1)
    table_shell.grid_columnconfigure(0, weight=1)
    columns = [
        ("scenario_name", "场景名称", 180),
        ("expected_dps", "期望DPS", 100),
        ("hit_chance_percent", "命中率%", 90),
        ("expected_damage_on_hit", "命中期望伤害", 120),
        ("armor_reduction_percent", "护甲减伤%", 100),
        ("damage_taken_multiplier", "承伤倍率", 90),
        ("theoretical_dps", "理论DPS", 100),
        ("distance_cells", "距离", 70),
        ("attacker_name", "攻击方", 120),
        ("defender_name", "防守方", 120),
        ("weapon_name", "武器", 180),
        ("outfit_valid", "穿戴合法", 90),
    ]
    app.compare_columns = columns
    app.compare_tree = ttk.Treeview(table_shell, columns=[column[0] for column in columns], show="headings", style="Compare.Treeview")
    app.compare_tree.grid(row=0, column=0, sticky="nsew")
    y_scroll = ttk.Scrollbar(table_shell, orient="vertical", command=app.compare_tree.yview)
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll = ttk.Scrollbar(table_shell, orient="horizontal", command=app.compare_tree.xview)
    x_scroll.grid(row=1, column=0, sticky="ew")
    app.compare_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    for key, label, width in columns:
        app.compare_tree.heading(key, text=label, command=lambda c=key: app._sort_compare_rows(c))
        app.compare_tree.column(key, width=width, anchor="center", stretch=False)


def build_import_page(app: RimDataAnalysisDesktopApp) -> None:
    page = app.import_page
    page.grid_rowconfigure(0, weight=1)
    page.grid_columnconfigure(1, weight=1)

    sidebar_shell, sidebar = app._scrollable_sidebar(page, width=380, padx=18, pady=18)
    sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=4)

    main = app._panel(page, padx=18, pady=18)
    main.grid(row=0, column=1, sticky="nsew", pady=4)
    main.grid_rowconfigure(2, weight=1)
    main.grid_columnconfigure(0, weight=1)
    main.grid_columnconfigure(1, weight=1)

    tk.Label(sidebar, text="数据导入", bg=app.colors["panel"], fg=app.colors["ink"], font=("Bahnschrift", 18, "bold")).pack(anchor="w")
    tk.Label(sidebar, text="先告诉应用你的 RimWorld 目录。你可以直接选择游戏根目录，程序会自动修正到 Data 目录。", bg=app.colors["panel"], fg=app.colors["muted"], justify="left", wraplength=320, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(4, 14))
    app._path_picker(sidebar, "游戏 Data 目录", app.import_game_data_var, app._browse_game_data_root)
    app._path_picker(sidebar, "Steam 创意工坊目录", app.import_workshop_var, app._browse_workshop_root)

    note = tk.Frame(sidebar, bg=app.colors["panel_alt"], padx=12, pady=12, highlightthickness=1, highlightbackground=app.colors["line"])
    note.pack(fill="x", pady=(8, 14))
    tk.Label(note, text="当前版本说明", bg=app.colors["panel_alt"], fg=app.colors["accent"], font=("Bahnschrift", 12, "bold")).pack(anchor="w")
    tk.Label(note, text="推荐直接选择 `...\\RimWorld\\Data`，也可以选择 `...\\RimWorld` 根目录。创意工坊路径当前先不参与分析。导入成功后，人物页和场景页会自动可用。", bg=app.colors["panel_alt"], fg=app.colors["ink"], justify="left", wraplength=300, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 0))

    button_row = tk.Frame(sidebar, bg=app.colors["panel"])
    button_row.pack(fill="x")
    ttk.Button(button_row, text="自动检测路径", style="Subtle.TButton", command=app._auto_detect_paths).pack(side="left", fill="x", expand=True, padx=(0, 6))
    ttk.Button(button_row, text="导入原版数据", style="Primary.TButton", command=app._import_catalog).pack(side="left", fill="x", expand=True)
    tk.Label(sidebar, textvariable=app.import_status_var, bg=app.colors["panel"], fg=app.colors["accent"], justify="left", wraplength=320, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(14, 0))

    flow_card = tk.Frame(sidebar, bg=app.colors["panel_alt"], padx=12, pady=12, highlightthickness=1, highlightbackground=app.colors["line"])
    flow_card.pack(fill="x", pady=(14, 0))
    tk.Label(flow_card, text="当前步骤", bg=app.colors["panel_alt"], fg=app.colors["accent"], font=("Bahnschrift", 12, "bold")).pack(anchor="w")
    tk.Label(flow_card, textvariable=app.import_flow_var, bg=app.colors["panel_alt"], fg=app.colors["ink"], justify="left", wraplength=300, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 10))
    app.import_to_characters_button = ttk.Button(flow_card, text="下一步：去人物创建", style="Primary.TButton", command=app._go_to_characters_page)
    app.import_to_characters_button.pack(fill="x")

    summary = tk.Frame(main, bg=app.colors["panel"])
    summary.grid(row=0, column=0, columnspan=2, sticky="ew")
    for idx in range(5):
        summary.grid_columnconfigure(idx, weight=1)
    summary_cards = [
        ("当前目录", app.import_summary_vars["catalog"]),
        ("武器数量", app.import_summary_vars["weapon_count"]),
        ("衣着数量", app.import_summary_vars["apparel_count"]),
        ("植入体数量", app.import_summary_vars["implant_count"]),
        ("导入时间", app.import_summary_vars["import_time"]),
    ]
    for idx, (label, var) in enumerate(summary_cards):
        app._metric_card(summary, 0, idx, label, var, width=220)

    tk.Label(main, text="武器预览", bg=app.colors["panel"], fg=app.colors["ink"], font=("Bahnschrift", 16, "bold")).grid(row=1, column=0, sticky="w", pady=(16, 8))
    tk.Label(main, text="衣着预览", bg=app.colors["panel"], fg=app.colors["ink"], font=("Bahnschrift", 16, "bold")).grid(row=1, column=1, sticky="w", pady=(16, 8))
    app.import_weapon_preview = app._simple_listbox(main, height=20)
    app.import_weapon_preview.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
    app.import_apparel_preview = app._simple_listbox(main, height=20)
    app.import_apparel_preview.grid(row=2, column=1, sticky="nsew", padx=(8, 0))


def build_resources_page(app: RimDataAnalysisDesktopApp) -> None:
    page = app.resources_page
    page.grid_rowconfigure(0, weight=1)
    page.grid_columnconfigure(0, weight=1)
    page.grid_columnconfigure(1, weight=1)

    pawns_panel = app._panel(page, padx=18, pady=18)
    pawns_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=4)
    pawns_panel.grid_rowconfigure(2, weight=1)
    pawns_panel.grid_columnconfigure(0, weight=1)

    scenarios_panel = app._panel(page, padx=18, pady=18)
    scenarios_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=4)
    scenarios_panel.grid_rowconfigure(2, weight=1)
    scenarios_panel.grid_columnconfigure(0, weight=1)

    tk.Label(pawns_panel, text="已保存人物", bg=app.colors["panel"], fg=app.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
    tk.Label(pawns_panel, text="支持载入编辑和删除预设。", bg=app.colors["panel"], fg=app.colors["muted"], font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 8))
    app.resource_pawns_listbox = app._simple_listbox(pawns_panel, height=18, selectmode=tk.MULTIPLE)
    app.resource_pawns_listbox.grid(row=2, column=0, sticky="nsew")
    app.resource_pawns_listbox.bind("<<ListboxSelect>>", lambda _event: app._update_resource_pawn_preview())
    app._bind_toggle_multiselect(
        app.resource_pawns_listbox,
        select_callback=lambda _event: app._update_resource_pawn_preview(),
    )

    app.resource_pawn_preview = tk.Label(pawns_panel, text="选择左侧人物后，这里会显示详情。", bg=app.colors["panel_alt"], fg=app.colors["ink"], justify="left", anchor="nw", wraplength=520, padx=14, pady=14)
    app.resource_pawn_preview.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    pawn_buttons = tk.Frame(pawns_panel, bg=app.colors["panel"])
    pawn_buttons.grid(row=4, column=0, sticky="ew", pady=(12, 0))
    ttk.Button(pawn_buttons, text="载入到人物创建页", style="Subtle.TButton", command=app._load_selected_character_from_resources).pack(side="left", fill="x", expand=True, padx=(0, 6))
    ttk.Button(pawn_buttons, text="删除选中人物", style="Subtle.TButton", command=app._delete_selected_pawn).pack(side="left", fill="x", expand=True)

    tk.Label(scenarios_panel, text="已保存场景", bg=app.colors["panel"], fg=app.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
    tk.Label(scenarios_panel, textvariable=app.resource_status_var, bg=app.colors["panel"], fg=app.colors["muted"], justify="left", wraplength=520, font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 8))
    app.resource_scenarios_listbox = app._simple_listbox(scenarios_panel, height=18, selectmode=tk.MULTIPLE)
    app.resource_scenarios_listbox.grid(row=2, column=0, sticky="nsew")
    app.resource_scenarios_listbox.bind("<<ListboxSelect>>", lambda _event: app._update_resource_scenario_preview())
    app._bind_toggle_multiselect(
        app.resource_scenarios_listbox,
        select_callback=lambda _event: app._update_resource_scenario_preview(),
    )

    app.resource_scenario_preview = tk.Label(scenarios_panel, text="选择左侧场景后，这里会显示详情。", bg=app.colors["panel_alt"], fg=app.colors["ink"], justify="left", anchor="nw", wraplength=520, padx=14, pady=14)
    app.resource_scenario_preview.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    scenario_buttons = tk.Frame(scenarios_panel, bg=app.colors["panel"])
    scenario_buttons.grid(row=4, column=0, sticky="ew", pady=(12, 0))
    ttk.Button(scenario_buttons, text="载入到场景设计页", style="Subtle.TButton", command=app._load_selected_scenario_from_resources).pack(side="left", fill="x", expand=True, padx=(0, 6))
    ttk.Button(scenario_buttons, text="删除选中场景", style="Subtle.TButton", command=app._delete_selected_scenario).pack(side="left", fill="x", expand=True)


def auto_detect_paths(app: RimDataAnalysisDesktopApp) -> None:
    detected = discover_paths()
    if detected.game_data_root is not None:
        app.import_game_data_var.set(str(detected.game_data_root))
    if detected.workshop_root is not None:
        app.import_workshop_var.set(str(detected.workshop_root))
    app.status_var.set("已根据本机环境自动检测路径。确认无误后点击“导入原版数据”。")


def browse_game_data_root(app: RimDataAnalysisDesktopApp) -> None:
    path = filedialog.askdirectory(title="选择 RimWorld 安装目录或 Data 目录")
    if path:
        app.import_game_data_var.set(path)


def browse_workshop_root(app: RimDataAnalysisDesktopApp) -> None:
    path = filedialog.askdirectory(title="选择 Steam 创意工坊目录")
    if path:
        app.import_workshop_var.set(path)


def import_catalog(app: RimDataAnalysisDesktopApp) -> None:
    app._load_catalog_from_settings(show_success=True)


def load_catalog_from_settings(app: RimDataAnalysisDesktopApp, *, show_success: bool) -> None:
    root = app.import_game_data_var.get().strip()
    normalized_path, correction_message, error_message = app._resolve_game_data_root(root)
    if error_message is not None:
        messagebox.showerror("目录设置错误", error_message)
        app.import_status_var.set("请把路径指向 RimWorld 根目录或其中的 Data 目录。")
        return
    assert normalized_path is not None
    path = normalized_path
    normalized_root = str(path)
    if normalized_root != root:
        app.import_game_data_var.set(normalized_root)
    try:
        app.catalog_index = load_catalog_index(path)
    except Exception as exc:
        messagebox.showerror(
            "导入失败",
            "读取原版数据时出错。\n\n"
            "请确认你选择的是 RimWorld 根目录或其中的 Data 目录。\n"
            f"当前使用路径：{path}\n\n"
            f"详细错误：\n{exc}",
        )
        app.import_status_var.set("导入失败，请检查路径是否正确指向 RimWorld 根目录或 Data 目录。")
        app._refresh_workflow_guidance()
        return
    app.import_settings = app.store.save_import_settings(
        ImportSettings(
            game_data_root=normalized_root,
            workshop_root=app.import_workshop_var.get().strip(),
            catalog_weapon_count=len(app.catalog_index.catalog.weapons),
            catalog_apparel_count=len(app.catalog_index.catalog.apparel),
            catalog_implant_count=len(app.catalog_index.catalog.implants),
            last_imported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    )
    app._update_import_summary()
    app._refresh_import_previews()
    app._refresh_character_option_list()
    app._refresh_character_firepower_preview()
    app._run_scenario_analysis()
    app.notebook.select(app.characters_page)
    if correction_message is not None:
        app.status_var.set(f"{correction_message} 原版数据已导入，下一步请到“人物创建”页建立人物。")
    else:
        app.status_var.set("原版数据已导入。下一步请到“人物创建”页建立攻击方和防守方。")
    app.import_status_var.set("导入成功。人物创建、场景设计和结果对比页现在都可以使用。")
    if show_success:
        messagebox.showinfo(
            "导入完成",
            f"{(correction_message + chr(10) + chr(10)) if correction_message else ''}"
            f"已载入 {len(app.catalog_index.catalog.weapons)} 个武器、"
            f"{len(app.catalog_index.catalog.apparel)} 件衣着、"
            f"{len(app.catalog_index.catalog.implants)} 个植入体。",
        )
    app._refresh_workflow_guidance()


def resolve_game_data_root(app: RimDataAnalysisDesktopApp, raw_path: str) -> tuple[Path | None, str | None, str | None]:
    normalized = raw_path.strip()
    if not normalized:
        return None, None, "请先选择 RimWorld 的安装目录或 Data 目录。"

    path = Path(normalized).expanduser()
    if not path.exists():
        return None, None, "填写的路径不存在。请重新选择 RimWorld 根目录或其中的 Data 目录。"
    if not path.is_dir():
        return None, None, "选择的路径不是文件夹。请重新选择 RimWorld 根目录或其中的 Data 目录。"

    candidates = [
        (path, None),
        (
            path / "Data",
            "你选择的是 RimWorld 根目录，程序已自动切换到其中的 Data 目录。",
        ),
        (
            path.parent,
            "你选择的是 Core 目录，程序已自动切换到上一级 Data 目录。",
        ),
        (
            path.parent.parent,
            "你选择的是 Core/Defs 目录，程序已自动切换到上一级 Data 目录。",
        ),
    ]
    for candidate, message in candidates:
        if candidate.exists() and candidate.is_dir() and (candidate / "Core" / "Defs").exists():
            return candidate, message, None

    return (
        None,
        None,
        "当前路径看起来不是有效的 RimWorld 数据目录。\n\n"
        "请选择以下两种路径之一：\n"
        "1. RimWorld 安装根目录，例如：E:\\SteamLibrary\\steamapps\\common\\RimWorld\n"
        "2. 其中的 Data 目录，例如：E:\\SteamLibrary\\steamapps\\common\\RimWorld\\Data",
    )


def update_import_summary(app: RimDataAnalysisDesktopApp) -> None:
    current_dir = app.import_game_data_var.get().strip() or "未设置"
    app.import_summary_vars["catalog"].set(current_dir)
    app.import_summary_vars["weapon_count"].set(str(app.import_settings.catalog_weapon_count))
    app.import_summary_vars["apparel_count"].set(str(app.import_settings.catalog_apparel_count))
    app.import_summary_vars["implant_count"].set(str(app.import_settings.catalog_implant_count))
    app.import_summary_vars["import_time"].set(app.import_settings.last_imported_at or "-")


def refresh_import_previews(app: RimDataAnalysisDesktopApp) -> None:
    app.import_weapon_preview.delete(0, tk.END)
    app.import_apparel_preview.delete(0, tk.END)
    if app.catalog_index is None:
        app.import_weapon_preview.insert(tk.END, "尚未导入任何原版武器。")
        app.import_apparel_preview.insert(tk.END, "尚未导入任何原版衣着。")
        return
    for record in app.catalog_index.catalog.weapons[:60]:
        app.import_weapon_preview.insert(tk.END, f"{record.display_label} / {record.def_name}")
    for record in app.catalog_index.catalog.apparel[:60]:
        app.import_apparel_preview.insert(tk.END, f"{record.display_label} / {record.def_name}")


def refresh_compare_source_list(app: RimDataAnalysisDesktopApp) -> None:
    app.compare_source_listbox.delete(0, tk.END)
    query = app.compare_filter_var.get().strip().lower()
    for scenario in app.saved_scenarios:
        display = app._scenario_display(scenario)
        if query and query not in display.lower():
            continue
        app.compare_source_listbox.insert(tk.END, display)
    app._refresh_workflow_guidance()


def refresh_resource_lists(app: RimDataAnalysisDesktopApp) -> None:
    app.resource_pawns_listbox.delete(0, tk.END)
    app.resource_scenarios_listbox.delete(0, tk.END)
    for pawn in app.saved_pawns:
        app.resource_pawns_listbox.insert(tk.END, app._pawn_display(pawn))
    for scenario in app.saved_scenarios:
        app.resource_scenarios_listbox.insert(tk.END, app._scenario_display(scenario))
    app._update_resource_pawn_preview()
    app._update_resource_scenario_preview()


def load_selected_character_from_resources(app: RimDataAnalysisDesktopApp) -> None:
    pawn = app._require_single_saved_pawn(app.resource_pawns_listbox, action_label="载入到人物创建页")
    if pawn is not None:
        app._load_character_into_editor(pawn)
        app.notebook.select(app.characters_page)


def load_selected_scenario_from_resources(app: RimDataAnalysisDesktopApp) -> None:
    scenario = app._require_single_saved_scenario(app.resource_scenarios_listbox, action_label="载入到场景设计页")
    if scenario is not None:
        app._load_scenario_into_editor(scenario)
        app.notebook.select(app.scenario_page)


def selected_compare_scenarios(app: RimDataAnalysisDesktopApp) -> list[SavedScenarioTemplate]:
    displays = [app.compare_source_listbox.get(index) for index in app.compare_source_listbox.curselection()]
    scenarios: list[SavedScenarioTemplate] = []
    for display in displays:
        for scenario in app.saved_scenarios:
            if app._scenario_display(scenario) == display:
                scenarios.append(scenario)
                break
    return scenarios


def scenario_from_compare_source_index(app: RimDataAnalysisDesktopApp, index: int) -> SavedScenarioTemplate | None:
    if index < 0 or index >= app.compare_source_listbox.size():
        return None
    display = app.compare_source_listbox.get(index)
    for scenario in app.saved_scenarios:
        if app._scenario_display(scenario) == display:
            return scenario
    return None


def merge_compare_rows(app: RimDataAnalysisDesktopApp, new_rows: list[ComparisonRow]) -> None:
    by_id = {row.scenario_id: row for row in app.compare_rows}
    for row in new_rows:
        by_id[row.scenario_id] = row
    app.compare_rows = list(by_id.values())
    app._apply_compare_sort()
    app._refresh_compare_table()
    app._refresh_workflow_guidance()


def analyze_selected_compare_scenarios(app: RimDataAnalysisDesktopApp) -> None:
    scenarios = app._selected_compare_scenarios()
    if not scenarios:
        messagebox.showerror("没有选择场景", "请先在左侧场景列表中选择至少一个场景。")
        return
    try:
        rows = app._comparison_rows_for_scenarios(scenarios)
    except Exception as exc:
        messagebox.showerror("计算失败", str(exc))
        return
    app._merge_compare_rows(rows)
    app.compare_status_var.set(f"已将 {len(rows)} 个场景加入对比表。")
    app.status_var.set("结果对比表已刷新。")


def analyze_compare_scenario_at_index(app: RimDataAnalysisDesktopApp, index: int) -> None:
    scenario = app._scenario_from_compare_source_index(index)
    if scenario is None:
        return
    try:
        rows = app._comparison_rows_for_scenarios([scenario])
    except Exception as exc:
        messagebox.showerror("计算失败", str(exc))
        return
    app._merge_compare_rows(rows)
    app.compare_status_var.set(f"已将场景“{scenario.name}”加入对比表。")
    app.status_var.set("结果对比表已刷新。")


def analyze_all_compare_scenarios(app: RimDataAnalysisDesktopApp) -> None:
    if not app.saved_scenarios:
        messagebox.showerror("没有场景", "当前还没有任何已保存场景。")
        return
    try:
        rows = app._comparison_rows_for_scenarios(app.saved_scenarios)
    except Exception as exc:
        messagebox.showerror("计算失败", str(exc))
        return
    app.compare_rows = rows
    app._apply_compare_sort()
    app._refresh_compare_table()
    app.compare_status_var.set(f"已分析全部 {len(rows)} 个场景。")
    app.status_var.set("全部场景的对比结果已生成。")


def clear_compare_rows(app: RimDataAnalysisDesktopApp) -> None:
    app.compare_rows = []
    app._refresh_compare_table()
    app.compare_status_var.set("对比表已清空。")
    app._refresh_workflow_guidance()


def save_compare_rows(app: RimDataAnalysisDesktopApp) -> None:
    if not app.compare_rows:
        messagebox.showerror("没有结果", "请先生成至少一条对比结果。")
        return
    output = app.store.save_result_rows(app.compare_rows, label="comparison-results")
    app.status_var.set("对比结果已自动保存到应用数据目录。")
    messagebox.showinfo("保存完成", f"本次结果已保存。\n{output}")


def refresh_compare_table(app: RimDataAnalysisDesktopApp) -> None:
    app.compare_tree.delete(*app.compare_tree.get_children())
    for row in app.compare_rows:
        values = []
        for key, _label, _width in app.compare_columns:
            raw = getattr(row, key)
            if key == "outfit_valid":
                values.append("是" if raw else "否")
            elif isinstance(raw, float):
                values.append(f"{raw:.2f}" if key.endswith("percent") else f"{raw:.4f}")
            else:
                values.append(raw)
        app.compare_tree.insert("", tk.END, values=values)


def update_resource_pawn_preview(app: RimDataAnalysisDesktopApp) -> None:
    pawn = app._selected_saved_pawn_from_listbox(app.resource_pawns_listbox)
    if pawn is None:
        app.resource_pawn_preview.configure(text="选择左侧人物后，这里会显示详情。")
        return
    app.resource_pawn_preview.configure(text=app._build_pawn_preview_text(pawn))


def update_resource_scenario_preview(app: RimDataAnalysisDesktopApp) -> None:
    scenario = app._selected_saved_scenario_from_listbox(app.resource_scenarios_listbox)
    if scenario is None:
        app.resource_scenario_preview.configure(text="选择左侧场景后，这里会显示详情。")
        return
    attacker = next((pawn for pawn in app.saved_pawns if pawn.id == scenario.attacker_pawn_id), None)
    defender = next((pawn for pawn in app.saved_pawns if pawn.id == scenario.defender_pawn_id), None)
    preview = [
        f"场景名称：{scenario.name}",
        f"攻击方：{attacker.name if attacker else scenario.attacker_pawn_id}",
        f"防守方：{defender.name if defender else scenario.defender_pawn_id}",
        f"距离：{scenario.distance_cells}",
        f"最终命中率%：{scenario.hit_chance_percent:.0f}",
    ]
    app.resource_scenario_preview.configure(text="\n".join(preview))


def delete_selected_pawn(app: RimDataAnalysisDesktopApp) -> None:
    pawns = app._selected_saved_pawns_from_listbox(app.resource_pawns_listbox)
    if not pawns:
        return
    if len(pawns) == 1:
        prompt = f"要删除人物“{pawns[0].name}”吗？"
    else:
        prompt = f"要删除选中的 {len(pawns)} 个人物吗？"
    if not messagebox.askyesno("确认删除", prompt):
        return
    deleted_count = 0
    failures: list[str] = []
    for pawn in pawns:
        try:
            app.store.delete_pawn(pawn.id)
            deleted_count += 1
        except Exception as exc:
            failures.append(f"{pawn.name}：{exc}")
    app._refresh_saved_data()
    if deleted_count > 0:
        app.status_var.set(f"已删除 {deleted_count} 个人物。")
    if failures:
        messagebox.showerror("部分人物无法删除", "\n".join(failures))


def delete_selected_scenario(app: RimDataAnalysisDesktopApp) -> None:
    scenarios = app._selected_saved_scenarios_from_listbox(app.resource_scenarios_listbox)
    if not scenarios:
        return
    if len(scenarios) == 1:
        prompt = f"要删除场景“{scenarios[0].name}”吗？"
    else:
        prompt = f"要删除选中的 {len(scenarios)} 个场景吗？"
    if not messagebox.askyesno("确认删除", prompt):
        return
    for scenario in scenarios:
        app.store.delete_scenario(scenario.id)
    app._refresh_saved_data()
    app.status_var.set(f"已删除 {len(scenarios)} 个场景。")
