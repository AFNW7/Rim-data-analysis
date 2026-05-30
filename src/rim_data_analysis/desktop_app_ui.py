from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

from rim_data_analysis.app_services import (
    WorkflowResult,
    load_scenario_payload,
    run_inventory_workflow,
    run_library_workflow,
    run_scenario_payload_workflow,
    run_vanilla_workflow,
    save_scenario_payload,
)
from rim_data_analysis.paths import discover_paths
from rim_data_analysis.scenario_library import ScenarioLibrary, load_scenario_library
from rim_data_analysis.vanilla_models import VanillaApparelRecord, VanillaCatalog, VanillaWeaponRecord
from rim_data_analysis.vanilla_parser import build_vanilla_catalog

TRAIT_OPTIONS: list[tuple[str, str, str]] = [
    ("tough", "坚韧", "受到的最终伤害更低"),
    ("careful_shooter", "谨慎射手", "远程更稳，但瞄准更慢"),
    ("trigger_happy", "手快枪快", "远程更急，但精度更低"),
    ("brawler", "斗殴者", "近战命中更高"),
    ("nimble", "灵活", "近战闪避更强"),
]

WEAPON_MODE_FILTERS: list[tuple[str, str]] = [
    ("全部", "all"),
    ("远程", "ranged"),
    ("近战", "melee"),
]

BODY_REGION_OPTIONS: list[tuple[str, str]] = [
    ("躯干", "Torso"),
    ("头部", "Head"),
    ("手臂", "Arms"),
    ("腿部", "Legs"),
    ("手", "Hands"),
    ("脚", "Feet"),
]

COVER_PRESET_OPTIONS: list[tuple[str, float]] = [
    ("0% 无掩体", 0.0),
    ("15% 轻掩体", 0.15),
    ("35% 半掩体", 0.35),
    ("55% 重掩体", 0.55),
]


@dataclass(slots=True)
class ResultWidgets:
    cards_frame: tk.Frame
    details_text: tk.Text
    outputs_listbox: tk.Listbox
    open_file_button: ttk.Button
    open_dir_button: ttk.Button
    open_report_button: ttk.Button
    outputs: list[tuple[str, Path]]


@dataclass(slots=True)
class ScenarioApparelEditorState:
    items: list[dict[str, object]]
    listbox: tk.Listbox | None = None


class RimDataAnalysisDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Rim 数据分析")
        self.geometry("1480x920")
        self.minsize(1280, 820)

        self.colors = {
            "bg": "#f4efe4",
            "panel": "#fffaf2",
            "panel_alt": "#ecdfc7",
            "line": "#d8c3a4",
            "ink": "#1e2425",
            "muted": "#5e696d",
            "accent": "#93561d",
            "accent_soft": "#f1d3aa",
            "good": "#2f6b4b",
            "bad": "#96463b",
            "log_bg": "#fbf5ea",
        }
        self.card_fonts = {
            "title": ("Bahnschrift", 12, "bold"),
            "value": ("Bahnschrift", 24, "bold"),
        }

        self.status_var = tk.StringVar(value="桌面应用已就绪")
        self.log_queue: queue.Queue[tuple[str, str, object]] = queue.Queue()
        self.log_lines: list[str] = ["桌面应用已启动。"]
        self.log_window: tk.Toplevel | None = None
        self.log_text: tk.Text | None = None
        self._busy = False
        self._result_widgets: dict[str, ResultWidgets] = {}

        self.repo_root = Path(__file__).resolve().parents[2]
        self.discovered_paths = discover_paths()

        self.scenario_apparel_state = ScenarioApparelEditorState(items=[])
        self.scenario_catalog: VanillaCatalog | None = None
        self.scenario_visible_weapon_records: list[VanillaWeaponRecord] = []
        self.scenario_visible_apparel_records: list[VanillaApparelRecord] = []
        self.scenario_weapon_listbox: tk.Listbox | None = None
        self.scenario_catalog_apparel_listbox: tk.Listbox | None = None
        self.scenario_advanced_frame: tk.Frame | None = None
        self.scenario_advanced_toggle_button: ttk.Button | None = None
        self.scenario_advanced_visible = False
        self.library_preview: ScenarioLibrary | None = None
        self.library_tag_variables: dict[str, tk.BooleanVar] = {}
        self.library_tag_checks_frame: tk.Frame | None = None
        self.library_scenario_listbox: tk.Listbox | None = None

        self._init_vars()
        self._configure_window()
        self._build_layout()
        self._load_defaults()
        self.after(120, self._poll_worker_events)

    def _init_vars(self) -> None:
        self.inventory_game_data_var = tk.StringVar()
        self.inventory_local_mods_var = tk.StringVar()
        self.inventory_workshop_var = tk.StringVar()
        self.inventory_save_var = tk.StringVar()
        self.inventory_output_var = tk.StringVar(value=str(Path("artifacts") / "gui-inventory"))

        self.vanilla_game_data_var = tk.StringVar()
        self.vanilla_output_var = tk.StringVar(value=str(Path("artifacts") / "gui-vanilla-analysis"))
        self.vanilla_distance_var = tk.StringVar(value="18")
        self.vanilla_shooting_skill_var = tk.StringVar(value="12")
        self.vanilla_melee_skill_var = tk.StringVar(value="12")

        self.scenario_game_data_var = tk.StringVar()
        self.scenario_catalog_status_var = tk.StringVar(
            value="还没有加载原版装备目录。先选择 RimWorld Data 路径，再点“载入原版装备目录”。"
        )
        self.scenario_path_var = tk.StringVar()
        self.scenario_output_var = tk.StringVar(
            value=str(Path("artifacts") / "gui-scenario" / "current-scenario.json")
        )
        self.scenario_name_var = tk.StringVar()
        self.scenario_weapon_filter_var = tk.StringVar(value="all")
        self.scenario_cover_preset_var = tk.StringVar(value=COVER_PRESET_OPTIONS[1][0])
        self.context_region_choice_var = tk.StringVar(value=BODY_REGION_OPTIONS[0][0])
        self.scenario_weapon_summary_var = tk.StringVar(
            value="还没有选择武器。载入原版装备目录后，在列表中点选即可。"
        )
        self.scenario_apparel_summary_var = tk.StringVar(
            value="还没有为防守方穿戴护具。可从左侧列表中点选并添加。"
        )

        self.scenario_known_attacker_traits = {
            trait_id: tk.BooleanVar(value=False) for trait_id, _label, _description in TRAIT_OPTIONS
        }
        self.scenario_known_defender_traits = {
            trait_id: tk.BooleanVar(value=False) for trait_id, _label, _description in TRAIT_OPTIONS
        }
        self.scenario_attacker_extra_traits_var = tk.StringVar()
        self.scenario_defender_extra_traits_var = tk.StringVar()

        self.attacker_name_var = tk.StringVar()
        self.attacker_shooting_skill_var = tk.StringVar(value="10")
        self.attacker_melee_skill_var = tk.StringVar(value="10")
        self.defender_name_var = tk.StringVar()
        self.defender_shooting_skill_var = tk.StringVar(value="10")
        self.defender_melee_skill_var = tk.StringVar(value="10")

        self.weapon_name_var = tk.StringVar()
        self.weapon_attack_mode_var = tk.StringVar(value="ranged")
        self.weapon_damage_type_var = tk.StringVar(value="Sharp")
        self.weapon_damage_var = tk.StringVar(value="10")
        self.weapon_armor_penetration_var = tk.StringVar(value="0")
        self.weapon_warmup_var = tk.StringVar(value="0")
        self.weapon_cooldown_var = tk.StringVar(value="0")
        self.weapon_burst_count_var = tk.StringVar(value="1")
        self.weapon_burst_interval_var = tk.StringVar(value="0")
        self.weapon_accuracy_close_var = tk.StringVar(value="1.0")
        self.weapon_accuracy_short_var = tk.StringVar(value="1.0")
        self.weapon_accuracy_medium_var = tk.StringVar(value="1.0")
        self.weapon_accuracy_long_var = tk.StringVar(value="1.0")

        self.context_distance_var = tk.StringVar(value="12")
        self.context_region_var = tk.StringVar(value="Torso")
        self.context_cover_block_var = tk.StringVar(value="0.15")
        self.context_hit_multiplier_var = tk.StringVar(value="1.0")
        self.context_target_aiming_var = tk.BooleanVar(value=False)

        self.apparel_name_var = tk.StringVar()
        self.apparel_source_var = tk.StringVar(value="manual")
        self.apparel_layers_var = tk.StringVar()
        self.apparel_covers_var = tk.StringVar()
        self.apparel_armor_sharp_var = tk.StringVar(value="0")
        self.apparel_armor_blunt_var = tk.StringVar(value="0")
        self.apparel_armor_heat_var = tk.StringVar(value="0")

        self.library_path_var = tk.StringVar()
        self.library_game_data_var = tk.StringVar()
        self.library_output_var = tk.StringVar(value=str(Path("artifacts") / "gui-scenario-library"))
        self.library_tags_var = tk.StringVar()
        self.library_ids_var = tk.StringVar()
        self.library_name_contains_var = tk.StringVar()
        self.library_status_var = tk.StringVar(
            value="先选择一个场景库文件，再点“读取库内容”，之后就可以通过勾选标签和场景来批量分析。"
        )
        self.library_selection_summary_var = tk.StringVar(
            value="还没有读取场景库内容。"
        )
        self.library_name_contains_var.trace_add("write", lambda *_args: self._update_library_selection_summary())

    def _configure_window(self) -> None:
        self.configure(bg=self.colors["bg"])

        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Microsoft YaHei UI", size=10)
        text_font = font.nametofont("TkTextFont")
        text_font.configure(family="Microsoft YaHei UI", size=10)
        heading_font = font.nametofont("TkHeadingFont")
        heading_font.configure(family="Bahnschrift", size=11, weight="bold")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=self.colors["bg"], foreground=self.colors["ink"])
        style.configure(
            "Primary.TButton",
            background=self.colors["accent"],
            foreground="#fff8f0",
            bordercolor=self.colors["accent"],
            padding=(14, 10),
        )
        style.map("Primary.TButton", background=[("active", "#784415"), ("disabled", "#ccb79b")])
        style.configure(
            "Subtle.TButton",
            background=self.colors["panel_alt"],
            foreground=self.colors["ink"],
            bordercolor=self.colors["line"],
            padding=(12, 8),
        )
        style.map("Subtle.TButton", background=[("active", "#e1d0b6")])
        style.configure("Workbench.TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure(
            "Workbench.TNotebook.Tab",
            background=self.colors["panel_alt"],
            foreground=self.colors["ink"],
            padding=(16, 11),
            borderwidth=0,
            font=("Bahnschrift", 11, "bold"),
        )
        style.map(
            "Workbench.TNotebook.Tab",
            background=[("selected", self.colors["panel"]), ("active", self.colors["accent_soft"])],
            foreground=[("selected", self.colors["accent"])],
        )

    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        topbar = tk.Frame(
            self,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=18,
            pady=12,
        )
        topbar.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        topbar.grid_columnconfigure(0, weight=1)

        title_shell = tk.Frame(topbar, bg=self.colors["panel"])
        title_shell.grid(row=0, column=0, sticky="w")
        tk.Label(
            title_shell,
            text="Rim 数据分析",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 19, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_shell,
            text="把复杂配置改成可点选的桌面应用，优先面向单场景分析与普通用户操作。",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        ttk.Button(topbar, text="查看日志", style="Subtle.TButton", command=self._open_log_window).grid(
            row=0,
            column=1,
            sticky="e",
        )

        content = tk.Frame(self, bg=self.colors["bg"], padx=18, pady=0)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(content, style="Workbench.TNotebook")
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self._build_scenario_tab()
        self._build_vanilla_tab()
        self._build_library_tab()
        self._build_inventory_tab()

        status_bar = tk.Frame(self, bg=self.colors["accent"], padx=18, pady=8)
        status_bar.grid(row=2, column=0, sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg=self.colors["accent"],
            fg="#fff6ec",
            font=("Microsoft YaHei UI", 10),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Button(status_bar, text="日志", style="Subtle.TButton", command=self._open_log_window).grid(
            row=0,
            column=1,
            sticky="e",
            padx=(12, 0),
        )

    def _create_tab_shell(self, title: str, description: str) -> ttk.Frame:
        shell = ttk.Frame(self.notebook, padding=16)
        shell.grid_rowconfigure(1, weight=0)
        shell.grid_rowconfigure(2, weight=1)
        shell.grid_columnconfigure(0, weight=1)
        self.notebook.add(shell, text=title)

        header = tk.Frame(shell, bg=self.colors["panel"], padx=10, pady=10)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(
            header,
            text=title,
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text=description,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        return shell

    def _split_tab(
        self,
        shell: ttk.Frame,
        *,
        control_width: int = 430,
        control_weight: int = 2,
        result_weight: int = 3,
        row: int = 2,
    ) -> tuple[tk.Frame, tk.Frame]:
        body = tk.Frame(shell, bg=self.colors["panel"])
        body.grid(row=row, column=0, sticky="nsew", pady=(10, 0))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=control_weight)
        body.grid_columnconfigure(1, weight=result_weight)

        control = tk.Frame(
            body,
            bg=self.colors["panel_alt"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=18,
            pady=18,
            width=control_width,
        )
        control.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        control.grid_propagate(False)

        result = tk.Frame(
            body,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=18,
            pady=18,
        )
        result.grid(row=0, column=1, sticky="nsew")
        result.grid_rowconfigure(2, weight=1)
        result.grid_columnconfigure(0, weight=1)
        return control, result

    def _create_scrollable_form(self, parent: tk.Frame, *, bg: str) -> tk.Frame:
        shell = tk.Frame(parent, bg=bg)
        shell.pack(fill="both", expand=True)

        canvas = tk.Canvas(shell, bg=bg, highlightthickness=0, relief="flat", bd=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        inner = tk.Frame(canvas, bg=bg)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        return inner

    def _create_card(
        self,
        parent: tk.Widget,
        title: str,
        description: str | None = None,
        *,
        bg: str | None = None,
    ) -> tuple[tk.Frame, tk.Frame]:
        card_bg = bg or self.colors["panel"]
        shell = tk.Frame(
            parent,
            bg=card_bg,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=16,
            pady=16,
        )
        tk.Label(
            shell,
            text=title,
            bg=card_bg,
            fg=self.colors["ink"],
            font=("Bahnschrift", 13, "bold"),
            anchor="w",
        ).pack(anchor="w")
        if description:
            tk.Label(
                shell,
                text=description,
                bg=card_bg,
                fg=self.colors["muted"],
                font=("Microsoft YaHei UI", 9),
                anchor="w",
                justify="left",
                wraplength=860,
            ).pack(anchor="w", pady=(4, 0))
        body = tk.Frame(shell, bg=card_bg)
        body.pack(fill="both", expand=True, pady=(12, 0))
        return shell, body

    def _build_inventory_tab(self) -> None:
        frame = self._create_tab_shell("包扫描", "扫描 Core、DLC、本地 Mods 和 Workshop 的基础元数据。")
        control, result = self._split_tab(frame)

        self._path_row(control, "游戏 Data 路径", self.inventory_game_data_var, mode="directory")
        self._path_row(control, "本地 Mods 路径", self.inventory_local_mods_var, mode="directory")
        self._path_row(control, "Workshop 路径", self.inventory_workshop_var, mode="directory")
        self._path_row(control, "存档路径", self.inventory_save_var, mode="directory")
        self._path_row(control, "输出目录", self.inventory_output_var, mode="directory")
        self._button_bar(
            control,
            [
                ("自动填入路径", self._load_discovered_inventory_paths, "Subtle.TButton"),
                ("载入仓库样例", self._load_inventory_fixture_paths, "Subtle.TButton"),
                ("开始扫描", self._submit_inventory_workflow, "Primary.TButton"),
            ],
        )
        self._result_widgets["inventory"] = self._create_result_panel(result)

    def _build_vanilla_tab(self) -> None:
        frame = self._create_tab_shell("原版装备目录", "提取原版武器和护具，并生成基础对比结果。")
        control, result = self._split_tab(frame)

        self._path_row(control, "游戏 Data 路径", self.vanilla_game_data_var, mode="directory")
        self._path_row(control, "输出目录", self.vanilla_output_var, mode="directory")
        self._spinbox_row(control, "分析距离", self.vanilla_distance_var, from_=1, to=60)
        self._spinbox_row(control, "射击技能", self.vanilla_shooting_skill_var, from_=0, to=20)
        self._spinbox_row(control, "近战技能", self.vanilla_melee_skill_var, from_=0, to=20)
        self._button_bar(
            control,
            [
                ("自动填入路径", self._load_discovered_vanilla_paths, "Subtle.TButton"),
                ("载入仓库样例", self._load_vanilla_fixture_paths, "Subtle.TButton"),
                ("生成原版目录", self._submit_vanilla_workflow, "Primary.TButton"),
            ],
        )
        self._result_widgets["vanilla"] = self._create_result_panel(result)

    def _build_scenario_tab(self) -> None:
        shell = self._create_tab_shell(
            "场景编辑",
            "新手推荐：先载入原版装备目录，然后只用点选武器、护具和特性，不需要记住 defName。",
        )
        shell.grid_rowconfigure(2, weight=1)

        toolbar_card, toolbar = self._create_card(
            shell,
            "快速操作",
            "1. 选择 RimWorld Data 路径  2. 载入原版装备目录  3. 点选人物、武器、护具  4. 直接开始分析",
        )
        toolbar_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self._path_row(toolbar, "RimWorld Data 路径", self.scenario_game_data_var, mode="directory")
        self._button_bar(
            toolbar,
            [
                ("自动填入路径", self._load_discovered_scenario_paths, "Subtle.TButton"),
                ("载入仓库样例路径", self._load_scenario_fixture_paths, "Subtle.TButton"),
                ("载入原版装备目录", self._submit_scenario_catalog_load, "Primary.TButton"),
            ],
        )

        self._path_row(
            toolbar,
            "场景文件",
            self.scenario_path_var,
            mode="file",
            file_types=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        self._button_bar(
            toolbar,
            [
                ("从文件载入场景", self._load_scenario_from_selected_file, "Subtle.TButton"),
                ("载入示例场景", self._load_scenario_fixture_paths, "Subtle.TButton"),
            ],
        )

        self._path_row(
            toolbar,
            "输出 JSON",
            self.scenario_output_var,
            mode="save",
            file_types=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        self._button_bar(
            toolbar,
            [
                ("保存当前场景", self._save_current_scenario, "Subtle.TButton"),
                ("开始分析", self._submit_scenario_workflow, "Primary.TButton"),
            ],
        )

        status_chip = tk.Label(
            toolbar,
            textvariable=self.scenario_catalog_status_var,
            bg=self.colors["accent_soft"],
            fg=self.colors["ink"],
            font=("Microsoft YaHei UI", 9),
            justify="left",
            anchor="w",
            wraplength=960,
            padx=10,
            pady=8,
        )
        status_chip.pack(fill="x", pady=(12, 0))

        control, result = self._split_tab(shell, control_width=760, control_weight=3, result_weight=2, row=2)
        form = self._create_scrollable_form(control, bg=self.colors["panel_alt"])
        self._build_scenario_editor(form)
        self._result_widgets["scenario"] = self._create_result_panel(result)

    def _build_library_tab(self) -> None:
        frame = self._create_tab_shell("场景库", "先读取场景库内容，再勾选标签和场景，最后一键批量分析。")

        toolbar_card, toolbar = self._create_card(
            frame,
            "批量分析快速操作",
            "1. 选择场景库文件  2. 读取库内容  3. 勾选标签或场景  4. 开始批量分析",
        )
        toolbar_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self._path_row(
            toolbar,
            "场景库文件",
            self.library_path_var,
            mode="file",
            file_types=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        self._path_row(toolbar, "游戏 Data 路径", self.library_game_data_var, mode="directory")
        self._path_row(toolbar, "输出目录", self.library_output_var, mode="directory")
        self._button_bar(
            toolbar,
            [
                ("自动填入路径", self._load_discovered_library_paths, "Subtle.TButton"),
                ("载入仓库样例", self._load_library_fixture_paths, "Subtle.TButton"),
                ("载入射击测试库", self._load_shooting_test_library_paths, "Subtle.TButton"),
                ("读取库内容", self._load_library_preview, "Subtle.TButton"),
                ("批量分析", self._submit_library_workflow, "Primary.TButton"),
            ],
        )

        tk.Label(
            toolbar,
            textvariable=self.library_status_var,
            bg=self.colors["accent_soft"],
            fg=self.colors["ink"],
            font=("Microsoft YaHei UI", 9),
            justify="left",
            anchor="w",
            wraplength=960,
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(12, 0))

        control, result = self._split_tab(frame, control_width=720, control_weight=3, result_weight=2)
        form = self._create_scrollable_form(control, bg=self.colors["panel_alt"])
        self._build_library_editor(form)
        self._result_widgets["library"] = self._create_result_panel(result, report_key="comparison_report_html")

    def _build_scenario_editor(self, parent: tk.Frame) -> None:
        base_card, base_body = self._create_card(
            parent,
            "场景名称",
            "只要给这次对比起一个名字即可，后续导出的 JSON 和分析结果都会沿用这个名称。",
        )
        base_card.pack(fill="x", pady=(0, 16))
        self._entry_row(base_body, "场景名称", self.scenario_name_var)

        actors_shell = tk.Frame(parent, bg=self.colors["panel_alt"])
        actors_shell.pack(fill="x", pady=(0, 16))
        actors_shell.grid_columnconfigure(0, weight=1)
        actors_shell.grid_columnconfigure(1, weight=1)

        attacker_card, attacker_body = self._create_card(
            actors_shell,
            "攻击方",
            "普通用户只需要填写名字、技能，再勾选特性。",
        )
        attacker_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._entry_row(attacker_body, "名字", self.attacker_name_var)
        self._spinbox_row(attacker_body, "射击技能", self.attacker_shooting_skill_var, from_=0, to=20)
        self._spinbox_row(attacker_body, "近战技能", self.attacker_melee_skill_var, from_=0, to=20)
        self._trait_check_grid(attacker_body, self.scenario_known_attacker_traits)

        defender_card, defender_body = self._create_card(
            actors_shell,
            "防守方",
            "这里同样以点选为主，护具在下方列表中添加。",
        )
        defender_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._entry_row(defender_body, "名字", self.defender_name_var)
        self._spinbox_row(defender_body, "射击技能", self.defender_shooting_skill_var, from_=0, to=20)
        self._spinbox_row(defender_body, "近战技能", self.defender_melee_skill_var, from_=0, to=20)
        self._trait_check_grid(defender_body, self.scenario_known_defender_traits)

        weapon_card, weapon_body = self._create_card(
            parent,
            "武器选择",
            "先切换远程或近战，再在列表中点一把武器。选中后会自动套用对应伤害、穿甲和精度参数。",
        )
        weapon_card.pack(fill="x", pady=(0, 16))
        self._build_scenario_weapon_selector(weapon_body)

        apparel_card, apparel_body = self._create_card(
            parent,
            "防守方护具",
            "左边是可选原版护具，右边是已经穿戴的护具。选中后点击添加或移除即可。",
        )
        apparel_card.pack(fill="x", pady=(0, 16))
        self._build_scenario_apparel_selector(apparel_body)

        context_card, context_body = self._create_card(
            parent,
            "战斗条件",
            "这里只保留普通用户最常用的操作：距离、命中部位和掩体情况。",
        )
        context_card.pack(fill="x", pady=(0, 16))
        self._build_scenario_context_editor(context_body)

        advanced_holder = tk.Frame(parent, bg=self.colors["panel_alt"])
        advanced_holder.pack(fill="x", pady=(0, 16))
        self.scenario_advanced_toggle_button = ttk.Button(
            advanced_holder,
            text="显示高级设置",
            style="Subtle.TButton",
            command=self._toggle_scenario_advanced,
        )
        self.scenario_advanced_toggle_button.pack(anchor="w")

        advanced_card, advanced_body = self._create_card(
            advanced_holder,
            "高级设置",
            "仅在需要手工输入自定义武器、额外特性或自定义护具时使用。普通用户可以完全忽略这一块。",
        )
        self.scenario_advanced_frame = advanced_card
        self._build_scenario_advanced_editor(advanced_body)

        self._refresh_scenario_weapon_listbox()
        self._refresh_catalog_apparel_listbox()
        self._refresh_apparel_listbox()
        self._update_weapon_summary_from_vars()
        self._update_apparel_summary()

    def _build_scenario_weapon_selector(self, parent: tk.Frame) -> None:
        mode_row = tk.Frame(parent, bg=parent.cget("bg"))
        mode_row.pack(fill="x", pady=(0, 12))
        tk.Label(
            mode_row,
            text="武器类型",
            bg=parent.cget("bg"),
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
        ).pack(anchor="w")

        filter_row = tk.Frame(mode_row, bg=parent.cget("bg"))
        filter_row.pack(fill="x", pady=(6, 0))
        for text, value in WEAPON_MODE_FILTERS:
            tk.Radiobutton(
                filter_row,
                text=text,
                value=value,
                variable=self.scenario_weapon_filter_var,
                command=self._refresh_scenario_weapon_listbox,
                bg=parent.cget("bg"),
                fg=self.colors["ink"],
                activebackground=parent.cget("bg"),
                activeforeground=self.colors["ink"],
                selectcolor="#fffdf8",
                font=("Microsoft YaHei UI", 10),
            ).pack(side="left", padx=(0, 14))

        self.scenario_weapon_listbox = tk.Listbox(
            parent,
            height=8,
            exportselection=False,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff8f0",
        )
        self.scenario_weapon_listbox.pack(fill="x", pady=(0, 12))
        self.scenario_weapon_listbox.bind("<<ListboxSelect>>", self._on_weapon_selected)

        tk.Label(
            parent,
            textvariable=self.scenario_weapon_summary_var,
            bg=self.colors["accent_soft"],
            fg=self.colors["ink"],
            justify="left",
            anchor="w",
            wraplength=820,
            padx=10,
            pady=8,
            font=("Microsoft YaHei UI", 9),
        ).pack(fill="x")

    def _build_scenario_apparel_selector(self, parent: tk.Frame) -> None:
        shell = tk.Frame(parent, bg=parent.cget("bg"))
        shell.pack(fill="x")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_columnconfigure(1, weight=0)
        shell.grid_columnconfigure(2, weight=1)

        available_frame = tk.Frame(shell, bg=parent.cget("bg"))
        available_frame.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            available_frame,
            text="可选护具",
            bg=parent.cget("bg"),
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
        ).pack(anchor="w")
        self.scenario_catalog_apparel_listbox = tk.Listbox(
            available_frame,
            height=10,
            exportselection=False,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff8f0",
        )
        self.scenario_catalog_apparel_listbox.pack(fill="x", pady=(6, 0))
        self.scenario_catalog_apparel_listbox.bind("<<ListboxSelect>>", self._on_catalog_apparel_selected)
        self.scenario_catalog_apparel_listbox.bind("<Double-Button-1>", lambda _event: self._add_selected_catalog_apparel())

        actions = tk.Frame(shell, bg=parent.cget("bg"), padx=12)
        actions.grid(row=0, column=1, sticky="ns")
        ttk.Button(actions, text="添加 >", style="Subtle.TButton", command=self._add_selected_catalog_apparel).pack(
            fill="x",
            pady=(26, 8),
        )
        ttk.Button(actions, text="< 移除", style="Subtle.TButton", command=self._remove_selected_apparel).pack(
            fill="x",
            pady=(0, 8),
        )
        ttk.Button(actions, text="清空全部", style="Subtle.TButton", command=self._clear_all_apparel).pack(fill="x")

        selected_frame = tk.Frame(shell, bg=parent.cget("bg"))
        selected_frame.grid(row=0, column=2, sticky="nsew")
        tk.Label(
            selected_frame,
            text="已穿戴护具",
            bg=parent.cget("bg"),
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
        ).pack(anchor="w")
        self.scenario_apparel_state.listbox = tk.Listbox(
            selected_frame,
            height=10,
            exportselection=False,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff8f0",
        )
        self.scenario_apparel_state.listbox.pack(fill="x", pady=(6, 0))
        self.scenario_apparel_state.listbox.bind("<<ListboxSelect>>", self._on_apparel_selected)

        tk.Label(
            parent,
            textvariable=self.scenario_apparel_summary_var,
            bg=self.colors["accent_soft"],
            fg=self.colors["ink"],
            justify="left",
            anchor="w",
            wraplength=820,
            padx=10,
            pady=8,
            font=("Microsoft YaHei UI", 9),
        ).pack(fill="x", pady=(12, 0))

    def _build_scenario_context_editor(self, parent: tk.Frame) -> None:
        self._spinbox_row(parent, "战斗距离（格）", self.context_distance_var, from_=0, to=80)

        region_values = [label for label, _value in BODY_REGION_OPTIONS]
        region_combo = self._combobox_row(parent, "命中部位", self.context_region_choice_var, values=region_values)
        region_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_context_vars_from_simple_controls())

        cover_values = [label for label, _value in COVER_PRESET_OPTIONS]
        cover_combo = self._combobox_row(parent, "掩体情况", self.scenario_cover_preset_var, values=cover_values)
        cover_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_context_vars_from_simple_controls())

        self._checkbox_row(
            parent,
            "目标正在瞄准或开火（近战时更不容易闪避）",
            self.context_target_aiming_var,
        )

    def _build_scenario_advanced_editor(self, parent: tk.Frame) -> None:
        self._entry_row(
            parent,
            "攻击方额外特性",
            self.scenario_attacker_extra_traits_var,
            hint="如果上面的勾选不够，可在这里填写英文 trait id，多个用英文逗号分隔。",
        )
        self._entry_row(
            parent,
            "防守方额外特性",
            self.scenario_defender_extra_traits_var,
            hint="例如自定义 Mod trait；普通用户一般不需要填写。",
        )
        self._entry_row(parent, "武器名称", self.weapon_name_var)
        self._combobox_row(parent, "攻击模式", self.weapon_attack_mode_var, values=["ranged", "melee"])
        self._combobox_row(parent, "伤害类型", self.weapon_damage_type_var, values=["Sharp", "Blunt", "Heat"])
        self._entry_row(parent, "基础伤害", self.weapon_damage_var)
        self._entry_row(parent, "护甲穿透", self.weapon_armor_penetration_var)
        self._entry_row(parent, "准备时间（秒）", self.weapon_warmup_var)
        self._entry_row(parent, "冷却时间（秒）", self.weapon_cooldown_var)
        self._entry_row(parent, "连发次数", self.weapon_burst_count_var)
        self._entry_row(parent, "连发间隔（秒）", self.weapon_burst_interval_var)
        self._entry_row(parent, "贴脸精度", self.weapon_accuracy_close_var)
        self._entry_row(parent, "近距离精度", self.weapon_accuracy_short_var)
        self._entry_row(parent, "中距离精度", self.weapon_accuracy_medium_var)
        self._entry_row(parent, "远距离精度", self.weapon_accuracy_long_var)
        self._entry_row(parent, "命中倍率", self.context_hit_multiplier_var)
        self._button_bar(parent, [("刷新武器摘要", self._update_weapon_summary_from_vars, "Subtle.TButton")])

        advanced_apparel_card, advanced_apparel_body = self._create_card(
            parent,
            "自定义护具编辑",
            "先在“已穿戴护具”里选中一件护具，下面会自动带出参数；也可以直接填写并新增自定义护具。",
            bg=str(parent.cget("bg")),
        )
        advanced_apparel_card.pack(fill="x", pady=(16, 0))
        self._entry_row(advanced_apparel_body, "护具名称", self.apparel_name_var)
        self._entry_row(advanced_apparel_body, "来源", self.apparel_source_var)
        self._entry_row(
            advanced_apparel_body,
            "层级",
            self.apparel_layers_var,
            hint="多个层级用英文逗号分隔，例如 Shell,Middle",
        )
        self._entry_row(
            advanced_apparel_body,
            "覆盖部位",
            self.apparel_covers_var,
            hint="多个部位用英文逗号分隔，例如 Torso,Arms",
        )
        self._entry_row(advanced_apparel_body, "锐器护甲", self.apparel_armor_sharp_var)
        self._entry_row(advanced_apparel_body, "钝器护甲", self.apparel_armor_blunt_var)
        self._entry_row(advanced_apparel_body, "热护甲", self.apparel_armor_heat_var)
        self._button_bar(
            advanced_apparel_body,
            [
                ("新增/更新护具", self._upsert_current_apparel, "Subtle.TButton"),
                ("清空护具输入", self._clear_current_apparel_fields, "Subtle.TButton"),
            ],
        )

    def _build_library_editor(self, parent: tk.Frame) -> None:
        overview_card, overview_body = self._create_card(
            parent,
            "库概览",
            "读取后会显示场景库名称、模板数量、场景数量和可用标签，普通用户可以直接从这里确认内容是否正确。",
        )
        overview_card.pack(fill="x", pady=(0, 16))
        tk.Label(
            overview_body,
            textvariable=self.library_selection_summary_var,
            bg=self.colors["accent_soft"],
            fg=self.colors["ink"],
            justify="left",
            anchor="w",
            wraplength=820,
            padx=10,
            pady=8,
            font=("Microsoft YaHei UI", 9),
        ).pack(fill="x")

        tag_card, tag_body = self._create_card(
            parent,
            "标签筛选",
            "先读取库内容。读取完成后，这里会显示所有标签。勾选后只分析带这些标签的场景。",
        )
        tag_card.pack(fill="x", pady=(0, 16))
        tag_actions = tk.Frame(tag_body, bg=tag_body.cget("bg"))
        tag_actions.pack(fill="x", pady=(0, 10))
        ttk.Button(tag_actions, text="全部清空", style="Subtle.TButton", command=self._clear_library_tags).pack(
            side="left",
            padx=(0, 10),
        )
        ttk.Button(tag_actions, text="常见战斗标签", style="Subtle.TButton", command=self._select_common_library_tags).pack(
            side="left"
        )
        self.library_tag_checks_frame = tk.Frame(tag_body, bg=tag_body.cget("bg"))
        self.library_tag_checks_frame.pack(fill="x")

        scenarios_card, scenarios_body = self._create_card(
            parent,
            "场景选择",
            "默认会分析库里的全部场景。你也可以只选中其中几项做对比。",
        )
        scenarios_card.pack(fill="x", pady=(0, 16))
        scenario_actions = tk.Frame(scenarios_body, bg=scenarios_body.cget("bg"))
        scenario_actions.pack(fill="x", pady=(0, 10))
        ttk.Button(
            scenario_actions,
            text="全选场景",
            style="Subtle.TButton",
            command=self._select_all_library_scenarios,
        ).pack(side="left", padx=(0, 10))
        ttk.Button(
            scenario_actions,
            text="清空选择",
            style="Subtle.TButton",
            command=self._clear_library_scenario_selection,
        ).pack(side="left")
        self.library_scenario_listbox = tk.Listbox(
            scenarios_body,
            height=10,
            selectmode="extended",
            exportselection=False,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff8f0",
        )
        self.library_scenario_listbox.pack(fill="x")
        self.library_scenario_listbox.bind("<<ListboxSelect>>", self._on_library_scenario_selected)

        advanced_card, advanced_body = self._create_card(
            parent,
            "补充筛选",
            "如果标签和场景列表还不够，可以继续用名称包含做进一步收窄。",
        )
        advanced_card.pack(fill="x")
        self._entry_row(advanced_body, "名称包含", self.library_name_contains_var)

    def _toggle_scenario_advanced(self) -> None:
        if self.scenario_advanced_frame is None or self.scenario_advanced_toggle_button is None:
            return
        if self.scenario_advanced_visible:
            self.scenario_advanced_frame.pack_forget()
            self.scenario_advanced_toggle_button.configure(text="显示高级设置")
            self.scenario_advanced_visible = False
            return
        self.scenario_advanced_frame.pack(fill="x", pady=(12, 0))
        self.scenario_advanced_toggle_button.configure(text="隐藏高级设置")
        self.scenario_advanced_visible = True

    def _trait_check_grid(self, parent: tk.Frame, variables: dict[str, tk.BooleanVar]) -> None:
        shell = tk.Frame(parent, bg=parent.cget("bg"))
        shell.pack(fill="x", pady=(0, 8))
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_columnconfigure(1, weight=1)

        tk.Label(
            shell,
            text="特性",
            bg=parent.cget("bg"),
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        for index, (trait_id, label, description) in enumerate(TRAIT_OPTIONS):
            cell = tk.Frame(shell, bg=parent.cget("bg"))
            cell.grid(row=index // 2 + 1, column=index % 2, sticky="ew", padx=(0, 8), pady=(0, 8))
            tk.Checkbutton(
                cell,
                text=label,
                variable=variables[trait_id],
                bg=parent.cget("bg"),
                fg=self.colors["ink"],
                activebackground=parent.cget("bg"),
                activeforeground=self.colors["ink"],
                selectcolor="#fffdf8",
                font=("Microsoft YaHei UI", 10),
                anchor="w",
            ).pack(anchor="w")
            tk.Label(
                cell,
                text=description,
                bg=parent.cget("bg"),
                fg=self.colors["muted"],
                font=("Microsoft YaHei UI", 8),
                justify="left",
            ).pack(anchor="w", padx=(24, 0))

    def _path_row(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        *,
        mode: str,
        file_types: list[tuple[str, str]] | None = None,
    ) -> None:
        bg = str(parent.cget("bg"))
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=(0, 12))
        tk.Label(
            row,
            text=label,
            bg=bg,
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
            anchor="w",
        ).pack(anchor="w")
        entry_shell = tk.Frame(row, bg=bg)
        entry_shell.pack(fill="x", pady=(6, 0))
        entry = tk.Entry(
            entry_shell,
            textvariable=variable,
            relief="flat",
            bg="#fffdf8",
            fg=self.colors["ink"],
            insertbackground=self.colors["accent"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=8)
        ttk.Button(
            entry_shell,
            text="浏览",
            style="Subtle.TButton",
            command=lambda: self._browse_path(variable, mode=mode, file_types=file_types),
        ).pack(side="left")

    def _entry_row(self, parent: tk.Frame, label: str, variable: tk.StringVar, hint: str | None = None) -> tk.Entry:
        bg = str(parent.cget("bg"))
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=(0, 12))
        tk.Label(
            row,
            text=label,
            bg=bg,
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
            anchor="w",
        ).pack(anchor="w")
        entry = tk.Entry(
            row,
            textvariable=variable,
            relief="flat",
            bg="#fffdf8",
            fg=self.colors["ink"],
            insertbackground=self.colors["accent"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
        )
        entry.pack(fill="x", pady=(6, 0), ipady=8)
        if hint:
            tk.Label(
                row,
                text=hint,
                bg=bg,
                fg=self.colors["muted"],
                font=("Microsoft YaHei UI", 9),
                anchor="w",
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        return entry

    def _spinbox_row(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        *,
        from_: int,
        to: int,
        increment: int = 1,
    ) -> ttk.Spinbox:
        bg = str(parent.cget("bg"))
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=(0, 12))
        tk.Label(
            row,
            text=label,
            bg=bg,
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
            anchor="w",
        ).pack(anchor="w")
        spinner = ttk.Spinbox(row, textvariable=variable, from_=from_, to=to, increment=increment)
        spinner.pack(fill="x", pady=(6, 0), ipady=4)
        return spinner

    def _combobox_row(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        *,
        values: list[str],
    ) -> ttk.Combobox:
        bg = str(parent.cget("bg"))
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=(0, 12))
        tk.Label(
            row,
            text=label,
            bg=bg,
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
            anchor="w",
        ).pack(anchor="w")
        combo = ttk.Combobox(row, textvariable=variable, values=values, state="readonly")
        combo.pack(fill="x", pady=(6, 0), ipady=4)
        return combo

    def _checkbox_row(self, parent: tk.Frame, label: str, variable: tk.BooleanVar) -> None:
        bg = str(parent.cget("bg"))
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=(0, 12))
        tk.Checkbutton(
            row,
            text=label,
            variable=variable,
            bg=bg,
            fg=self.colors["ink"],
            activebackground=bg,
            activeforeground=self.colors["ink"],
            selectcolor="#fffdf8",
            anchor="w",
            justify="left",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w")

    def _button_bar(self, parent: tk.Frame, buttons: list[tuple[str, object, str]]) -> None:
        bg = str(parent.cget("bg"))
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=(8, 0))
        for text, command, style_name in buttons:
            ttk.Button(row, text=text, command=command, style=style_name).pack(side="left", padx=(0, 10))

    def _create_result_panel(self, parent: tk.Frame, report_key: str | None = None) -> ResultWidgets:
        tk.Label(
            parent,
            text="本次结果",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 14, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        cards_frame = tk.Frame(parent, bg=self.colors["panel"])
        cards_frame.grid(row=1, column=0, sticky="ew", pady=(12, 16))
        self._render_placeholder_cards(cards_frame)

        body = tk.Frame(parent, bg=self.colors["panel"])
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        details_shell = tk.Frame(
            body,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=14,
            pady=14,
        )
        details_shell.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        details_shell.grid_rowconfigure(1, weight=1)
        details_shell.grid_columnconfigure(0, weight=1)
        tk.Label(
            details_shell,
            text="结果说明",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        details_text = tk.Text(
            details_shell,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            wrap="word",
            padx=12,
            pady=12,
            insertbackground=self.colors["accent"],
        )
        details_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        details_text.insert("1.0", "还没有运行分析。\n")
        details_text.configure(state="disabled")

        outputs_shell = tk.Frame(
            body,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=14,
            pady=14,
        )
        outputs_shell.grid(row=1, column=0, sticky="nsew")
        outputs_shell.grid_rowconfigure(1, weight=1)
        outputs_shell.grid_columnconfigure(0, weight=1)
        tk.Label(
            outputs_shell,
            text="生成文件",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        outputs_listbox = tk.Listbox(
            outputs_shell,
            exportselection=False,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff8f0",
        )
        outputs_listbox.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        outputs_listbox.insert("end", "还没有生成文件")

        actions = tk.Frame(outputs_shell, bg=self.colors["panel"])
        actions.grid(row=2, column=0, sticky="ew")
        open_file_button = ttk.Button(actions, text="打开选中文件", style="Subtle.TButton", state="disabled")
        open_file_button.pack(side="left", padx=(0, 8))
        open_dir_button = ttk.Button(actions, text="打开输出目录", style="Subtle.TButton", state="disabled")
        open_dir_button.pack(side="left", padx=(0, 8))
        open_report_button = ttk.Button(actions, text="打开 HTML 报告", style="Subtle.TButton", state="disabled")
        open_report_button.pack(side="left")

        widgets = ResultWidgets(
            cards_frame=cards_frame,
            details_text=details_text,
            outputs_listbox=outputs_listbox,
            open_file_button=open_file_button,
            open_dir_button=open_dir_button,
            open_report_button=open_report_button,
            outputs=[],
        )
        open_file_button.configure(command=lambda: self._open_selected_output(widgets))
        open_dir_button.configure(command=lambda: self._open_output_directory(widgets))
        open_report_button.configure(command=lambda: self._open_report_output(widgets, report_key))
        outputs_listbox.bind("<Double-Button-1>", lambda _event: self._open_selected_output(widgets))
        return widgets

    def _render_placeholder_cards(self, parent: tk.Frame) -> None:
        for index in range(4):
            parent.grid_columnconfigure(index, weight=1)
            card = tk.Frame(
                parent,
                bg=self.colors["panel_alt"],
                highlightthickness=1,
                highlightbackground=self.colors["line"],
                padx=14,
                pady=14,
            )
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < 3 else 0))
            tk.Label(
                card,
                text="等待运行",
                bg=self.colors["panel_alt"],
                fg=self.colors["muted"],
                font=("Bahnschrift", 10, "bold"),
            ).pack(anchor="w")
            tk.Label(
                card,
                text="--",
                bg=self.colors["panel_alt"],
                fg=self.colors["ink"],
                font=("Bahnschrift", 24, "bold"),
            ).pack(anchor="w", pady=(10, 0))

    def _load_defaults(self) -> None:
        self._load_discovered_inventory_paths()
        self._load_discovered_vanilla_paths()
        self._load_discovered_library_paths()
        self._load_discovered_scenario_paths()
        self._load_scenario_fixture_paths()

    def _load_discovered_inventory_paths(self) -> None:
        self.inventory_game_data_var.set(str(self.discovered_paths.game_data_root or ""))
        self.inventory_local_mods_var.set(str(self.discovered_paths.local_mods_root or ""))
        self.inventory_workshop_var.set(str(self.discovered_paths.workshop_root or ""))
        self.inventory_save_var.set(str(self.discovered_paths.save_data_root or ""))
        self._append_log("已载入自动发现的包扫描路径。")

    def _load_inventory_fixture_paths(self) -> None:
        self.inventory_game_data_var.set(str(self.repo_root / "tests" / "fixtures" / "game_data"))
        self.inventory_local_mods_var.set(str(self.repo_root / "tests" / "fixtures" / "local_mods"))
        self.inventory_workshop_var.set(str(self.repo_root / "tests" / "fixtures" / "workshop_mods"))
        self.inventory_save_var.set("")
        self.inventory_output_var.set(str(self.repo_root / "artifacts" / "gui-inventory-fixture"))
        self._append_log("已载入仓库自带的包扫描样例路径。")

    def _load_discovered_vanilla_paths(self) -> None:
        self.vanilla_game_data_var.set(str(self.discovered_paths.game_data_root or ""))
        self._append_log("已载入自动发现的原版 Data 路径。")

    def _load_vanilla_fixture_paths(self) -> None:
        self.vanilla_game_data_var.set(str(self.repo_root / "tests" / "fixtures" / "vanilla_game_data"))
        self.vanilla_output_var.set(str(self.repo_root / "artifacts" / "gui-vanilla-fixture"))
        self._append_log("已载入仓库自带的原版装备样例路径。")

    def _load_discovered_scenario_paths(self) -> None:
        self.scenario_game_data_var.set(str(self.discovered_paths.game_data_root or ""))
        if self.discovered_paths.game_data_root:
            self.scenario_catalog_status_var.set(
                "已自动填入 RimWorld Data 路径。点击“载入原版装备目录”后，就可以直接点选武器和护具。"
            )
        else:
            self.scenario_catalog_status_var.set(
                "没有自动发现 RimWorld Data 路径。你仍然可以使用示例场景，或手动选择游戏 Data 目录。"
            )
        self._append_log("已刷新场景编辑器的游戏路径。")

    def _load_scenario_fixture_paths(self) -> None:
        scenario_path = self.repo_root / "assets" / "scenarios" / "sample-ranged-vs-armor.json"
        self.scenario_path_var.set(str(scenario_path))
        self.scenario_output_var.set(
            str(self.repo_root / "artifacts" / "gui-scenario" / "sample-ranged-vs-armor.scenario.json")
        )
        self._load_scenario_payload_into_form(load_scenario_payload(scenario_path))
        self._append_log("已载入仓库自带的示例场景。")

    def _load_discovered_library_paths(self) -> None:
        self.library_game_data_var.set(str(self.discovered_paths.game_data_root or ""))
        self._append_log("已载入自动发现的场景库分析路径。")

    def _load_library_fixture_paths(self) -> None:
        self.library_path_var.set(str(self.repo_root / "assets" / "scenario-libraries" / "sample-library.json"))
        self.library_game_data_var.set(str(self.repo_root / "tests" / "fixtures" / "vanilla_game_data"))
        self.library_output_var.set(str(self.repo_root / "artifacts" / "gui-library-fixture"))
        self._load_library_preview()
        self._append_log("已载入仓库自带的场景库样例。")

    def _load_shooting_test_library_paths(self) -> None:
        self.library_path_var.set(str(self.repo_root / "assets" / "scenario-libraries" / "shooting-test-library.json"))
        self.library_game_data_var.set(str(self.repo_root / "tests" / "fixtures" / "vanilla_game_data"))
        self.library_output_var.set(str(self.repo_root / "artifacts" / "gui-shooting-test-library"))
        self._load_library_preview()
        self._append_log("已载入射击测试场景库。")

    def _load_library_preview(self) -> None:
        try:
            library_path = self._require_non_empty(self.library_path_var.get(), "请先选择场景库文件。")
            library = load_scenario_library(Path(library_path))
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))
            return
        self.library_preview = library
        self._render_library_preview()
        self._append_log(f"已读取场景库内容: {library_path}")

    def _render_library_preview(self) -> None:
        if self.library_preview is None:
            return

        tags = self._library_preview_tags()
        self.library_status_var.set(
            f"已读取场景库：{self.library_preview.name}。"
            f" 共 {len(self.library_preview.templates)} 个模板，{len(self.library_preview.scenarios)} 个场景，"
            f"{len(tags)} 个标签。"
        )
        self.library_selection_summary_var.set(
            f"当前场景库：{self.library_preview.name}\n"
            f"模板数量：{len(self.library_preview.templates)}\n"
            f"场景数量：{len(self.library_preview.scenarios)}\n"
            f"可用标签：{', '.join(tags) if tags else '无标签'}"
        )
        self._render_library_tag_filters()
        self._refresh_library_scenario_listbox()
        self._select_all_library_scenarios()

    def _library_preview_tags(self) -> list[str]:
        if self.library_preview is None:
            return []
        tags = {
            tag.strip()
            for scenario in self.library_preview.scenarios
            for tag in scenario.tags
            if tag.strip()
        }
        return sorted(tags, key=str.lower)

    def _render_library_tag_filters(self) -> None:
        if self.library_tag_checks_frame is None:
            return

        for child in self.library_tag_checks_frame.winfo_children():
            child.destroy()

        tags = self._library_preview_tags()
        preserved = {
            tag: variable.get()
            for tag, variable in self.library_tag_variables.items()
        }
        self.library_tag_variables = {
            tag: tk.BooleanVar(value=preserved.get(tag, False))
            for tag in tags
        }

        if not tags:
            tk.Label(
                self.library_tag_checks_frame,
                text="还没有可用标签。先读取场景库内容。",
                bg=self.library_tag_checks_frame.cget("bg"),
                fg=self.colors["muted"],
                font=("Microsoft YaHei UI", 9),
                justify="left",
            ).pack(anchor="w")
            return

        grid = tk.Frame(self.library_tag_checks_frame, bg=self.library_tag_checks_frame.cget("bg"))
        grid.pack(fill="x")
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1)
        for index, tag in enumerate(tags):
            tk.Checkbutton(
                grid,
                text=tag,
                variable=self.library_tag_variables[tag],
                command=self._on_library_tag_changed,
                bg=grid.cget("bg"),
                fg=self.colors["ink"],
                activebackground=grid.cget("bg"),
                activeforeground=self.colors["ink"],
                selectcolor="#fffdf8",
                anchor="w",
                font=("Microsoft YaHei UI", 10),
            ).grid(row=index // 3, column=index % 3, sticky="w", padx=(0, 10), pady=(0, 8))

    def _refresh_library_scenario_listbox(self) -> None:
        listbox = self.library_scenario_listbox
        if listbox is None:
            return

        listbox.delete(0, "end")
        if self.library_preview is None or not self.library_preview.scenarios:
            listbox.insert("end", "还没有读取场景库内容")
            self._update_library_selection_summary()
            return

        for scenario in self.library_preview.scenarios:
            tags = " / ".join(scenario.tags) if scenario.tags else "无标签"
            attack_mode = "自定义武器" if scenario.manual_weapon is not None else (scenario.weapon_def_name or "未指定武器")
            listbox.insert("end", f"{scenario.name}  ·  {tags}  ·  {attack_mode}")
        self._update_library_selection_summary()

    def _select_all_library_scenarios(self) -> None:
        listbox = self.library_scenario_listbox
        if listbox is None or self.library_preview is None:
            return
        listbox.selection_clear(0, "end")
        for index in range(len(self.library_preview.scenarios)):
            listbox.selection_set(index)
        self._update_library_selection_summary()

    def _clear_library_scenario_selection(self) -> None:
        if self.library_scenario_listbox is None:
            return
        self.library_scenario_listbox.selection_clear(0, "end")
        self._update_library_selection_summary()

    def _on_library_scenario_selected(self, _event: object) -> None:
        self._update_library_selection_summary()

    def _clear_library_tags(self) -> None:
        for variable in self.library_tag_variables.values():
            variable.set(False)
        self._update_library_selection_summary()

    def _select_common_library_tags(self) -> None:
        common = {"ranged", "melee", "tough", "layered", "vest"}
        for tag, variable in self.library_tag_variables.items():
            variable.set(tag.lower() in common)
        self._update_library_selection_summary()

    def _on_library_tag_changed(self) -> None:
        self._update_library_selection_summary()

    def _selected_library_tags(self) -> list[str]:
        return [tag for tag, variable in self.library_tag_variables.items() if variable.get()]

    def _selected_library_scenario_ids(self) -> list[str]:
        listbox = self.library_scenario_listbox
        if listbox is None or self.library_preview is None:
            return []
        ids: list[str] = []
        for index in listbox.curselection():
            if 0 <= index < len(self.library_preview.scenarios):
                ids.append(self.library_preview.scenarios[index].scenario_id)
        return ids

    def _update_library_selection_summary(self) -> None:
        if self.library_preview is None:
            self.library_selection_summary_var.set("还没有读取场景库内容。")
            return

        selected_tags = self._selected_library_tags()
        selected_ids = self._selected_library_scenario_ids()
        total = len(self.library_preview.scenarios)
        scenario_text = f"已选中 {len(selected_ids)} / {total} 个场景" if selected_ids else f"当前未单独选场景，将默认分析全部 {total} 个场景"
        tag_text = f"标签过滤：{', '.join(selected_tags)}" if selected_tags else "标签过滤：未启用"
        name_text = f"名称包含：{self.library_name_contains_var.get().strip()}" if self.library_name_contains_var.get().strip() else "名称包含：未启用"
        self.library_selection_summary_var.set(
            f"当前场景库：{self.library_preview.name}\n{scenario_text}\n{tag_text}\n{name_text}"
        )

    def _submit_scenario_catalog_load(self) -> None:
        if self._busy:
            messagebox.showinfo("任务进行中", "当前已有任务在运行，请等待完成后再载入装备目录。")
            return
        try:
            game_data_root = self._require_non_empty(
                self.scenario_game_data_var.get(),
                "请先选择 RimWorld 的 Data 目录。",
            )
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))
            return

        self._busy = True
        start_message = "正在读取原版武器和护具目录"
        self.status_var.set(start_message)
        self._append_log(start_message)

        def runner() -> None:
            try:
                catalog = build_vanilla_catalog(Path(game_data_root))
                self.log_queue.put(("catalog", "scenario", catalog))
            except Exception as exc:  # pragma: no cover - UI error path
                self.log_queue.put(("error", "scenario_catalog", (str(exc), traceback.format_exc())))

        threading.Thread(target=runner, daemon=True).start()

    def _load_scenario_from_selected_file(self) -> None:
        try:
            scenario_path = self._require_non_empty(self.scenario_path_var.get(), "请选择要载入的场景文件。")
            payload = load_scenario_payload(scenario_path)
            self._load_scenario_payload_into_form(payload)
            self._append_log(f"已从文件载入场景表单: {scenario_path}")
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _save_current_scenario(self) -> None:
        try:
            payload = self._build_scenario_payload_from_form()
            output_path = self._require_non_empty(self.scenario_output_var.get(), "请选择场景保存路径。")
            saved_path = save_scenario_payload(payload=payload, output_path=output_path)
            self._append_log(f"已保存当前场景: {saved_path}")
            messagebox.showinfo("保存完成", f"场景已保存到:\n{saved_path}")
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _load_scenario_payload_into_form(self, payload: dict[str, object]) -> None:
        attacker = payload.get("attacker", {}) if isinstance(payload.get("attacker"), dict) else {}
        defender = payload.get("defender", {}) if isinstance(payload.get("defender"), dict) else {}
        weapon = payload.get("weapon", {}) if isinstance(payload.get("weapon"), dict) else {}
        context = payload.get("context", {}) if isinstance(payload.get("context"), dict) else {}

        self.scenario_name_var.set(str(payload.get("name", "")))

        self.attacker_name_var.set(str(attacker.get("name", "")))
        self.attacker_shooting_skill_var.set(str(attacker.get("shooting_skill", 10)))
        self.attacker_melee_skill_var.set(str(attacker.get("melee_skill", 10)))
        self._set_trait_selection("attacker", self._ensure_string_list(attacker.get("traits", [])))

        self.defender_name_var.set(str(defender.get("name", "")))
        self.defender_shooting_skill_var.set(str(defender.get("shooting_skill", 10)))
        self.defender_melee_skill_var.set(str(defender.get("melee_skill", 10)))
        self._set_trait_selection("defender", self._ensure_string_list(defender.get("traits", [])))

        self.weapon_name_var.set(str(weapon.get("name", "")))
        self.weapon_attack_mode_var.set(str(weapon.get("attack_mode", "ranged")))
        self.weapon_damage_type_var.set(str(weapon.get("damage_type", "Sharp")))
        self.weapon_damage_var.set(str(weapon.get("damage", 10)))
        self.weapon_armor_penetration_var.set(str(weapon.get("armor_penetration", 0)))
        self.weapon_warmup_var.set(str(weapon.get("warmup_seconds", 0)))
        self.weapon_cooldown_var.set(str(weapon.get("cooldown_seconds", 0)))
        self.weapon_burst_count_var.set(str(weapon.get("burst_shot_count", 1)))
        self.weapon_burst_interval_var.set(str(weapon.get("burst_shot_interval_seconds", 0)))
        self.weapon_accuracy_close_var.set(str(weapon.get("accuracy_close", 1.0)))
        self.weapon_accuracy_short_var.set(str(weapon.get("accuracy_short", 1.0)))
        self.weapon_accuracy_medium_var.set(str(weapon.get("accuracy_medium", 1.0)))
        self.weapon_accuracy_long_var.set(str(weapon.get("accuracy_long", 1.0)))

        self.context_distance_var.set(str(context.get("distance_cells", 12)))
        self.context_region_var.set(str(context.get("target_body_region", "Torso")))
        self.context_cover_block_var.set(str(context.get("cover_block_chance", 0)))
        self.context_hit_multiplier_var.set(str(context.get("hit_chance_multiplier", 1.0)))
        self.context_target_aiming_var.set(bool(context.get("target_is_aiming_or_firing", False)))
        self.context_region_choice_var.set(self._region_display_for_value(self.context_region_var.get()))
        self.scenario_cover_preset_var.set(self._cover_display_for_value(self.context_cover_block_var.get()))

        apparel_items = defender.get("apparel", [])
        self.scenario_apparel_state.items = []
        if isinstance(apparel_items, list):
            for item in apparel_items:
                if isinstance(item, dict):
                    self.scenario_apparel_state.items.append(dict(item))

        self.scenario_weapon_filter_var.set(self.weapon_attack_mode_var.get().strip() or "all")
        self._refresh_scenario_weapon_listbox()
        self._refresh_apparel_listbox()
        self._clear_current_apparel_fields()
        self._update_weapon_summary_from_vars()
        self._update_apparel_summary()

    def _build_scenario_payload_from_form(self) -> dict[str, object]:
        self._sync_context_vars_from_simple_controls()
        self._update_weapon_summary_from_vars()

        scenario_name = self._require_non_empty(self.scenario_name_var.get(), "场景名称不能为空。")
        attacker_name = self._require_non_empty(self.attacker_name_var.get(), "攻击方名称不能为空。")
        defender_name = self._require_non_empty(self.defender_name_var.get(), "防守方名称不能为空。")
        weapon_name = self._require_non_empty(self.weapon_name_var.get(), "请先选择武器，或在高级设置里填写武器。")

        return {
            "name": scenario_name,
            "attacker": {
                "name": attacker_name,
                "shooting_skill": self._parse_int(self.attacker_shooting_skill_var.get(), "攻击方射击技能"),
                "melee_skill": self._parse_int(self.attacker_melee_skill_var.get(), "攻击方近战技能"),
                "traits": self._collect_traits("attacker"),
            },
            "defender": {
                "name": defender_name,
                "shooting_skill": self._parse_int(self.defender_shooting_skill_var.get(), "防守方射击技能"),
                "melee_skill": self._parse_int(self.defender_melee_skill_var.get(), "防守方近战技能"),
                "traits": self._collect_traits("defender"),
                "apparel": [dict(item) for item in self.scenario_apparel_state.items],
            },
            "weapon": {
                "name": weapon_name,
                "attack_mode": self.weapon_attack_mode_var.get().strip() or "ranged",
                "damage_type": self.weapon_damage_type_var.get().strip() or "Sharp",
                "damage": self._parse_float(self.weapon_damage_var.get(), "基础伤害"),
                "armor_penetration": self._parse_float(self.weapon_armor_penetration_var.get(), "护甲穿透"),
                "warmup_seconds": self._parse_float(self.weapon_warmup_var.get(), "准备时间"),
                "cooldown_seconds": self._parse_float(self.weapon_cooldown_var.get(), "冷却时间"),
                "burst_shot_count": self._parse_int(self.weapon_burst_count_var.get(), "连发次数"),
                "burst_shot_interval_seconds": self._parse_float(self.weapon_burst_interval_var.get(), "连发间隔"),
                "accuracy_close": self._parse_float(self.weapon_accuracy_close_var.get(), "贴脸精度"),
                "accuracy_short": self._parse_float(self.weapon_accuracy_short_var.get(), "近距离精度"),
                "accuracy_medium": self._parse_float(self.weapon_accuracy_medium_var.get(), "中距离精度"),
                "accuracy_long": self._parse_float(self.weapon_accuracy_long_var.get(), "远距离精度"),
            },
            "context": {
                "distance_cells": self._parse_int(self.context_distance_var.get(), "距离"),
                "target_body_region": self._require_non_empty(self.context_region_var.get(), "命中部位不能为空。"),
                "cover_block_chance": self._parse_float(self.context_cover_block_var.get(), "掩体概率"),
                "hit_chance_multiplier": self._parse_float(self.context_hit_multiplier_var.get(), "命中倍率"),
                "target_is_aiming_or_firing": self.context_target_aiming_var.get(),
            },
        }

    def _sync_context_vars_from_simple_controls(self) -> None:
        region_value = next(
            (value for label, value in BODY_REGION_OPTIONS if label == self.context_region_choice_var.get()),
            self.context_region_var.get() or "Torso",
        )
        self.context_region_var.set(region_value)

        cover_value = next(
            (value for label, value in COVER_PRESET_OPTIONS if label == self.scenario_cover_preset_var.get()),
            None,
        )
        if cover_value is not None:
            self.context_cover_block_var.set(str(cover_value))
            return

        preset_text = self.scenario_cover_preset_var.get().strip()
        if preset_text.endswith("自定义"):
            maybe_percent = preset_text.split("%", 1)[0]
            try:
                self.context_cover_block_var.set(str(float(maybe_percent) / 100.0))
            except ValueError:
                pass

    def _set_trait_selection(self, side: str, traits: list[str]) -> None:
        variables = self.scenario_known_attacker_traits if side == "attacker" else self.scenario_known_defender_traits
        extra_var = self.scenario_attacker_extra_traits_var if side == "attacker" else self.scenario_defender_extra_traits_var
        normalized_lookup = {trait.strip().lower(): trait.strip() for trait in traits if trait.strip()}
        known_ids = {trait_id for trait_id, _label, _description in TRAIT_OPTIONS}
        extras: list[str] = []
        for trait_id in variables:
            variables[trait_id].set(trait_id in normalized_lookup)
        for normalized_key, original in normalized_lookup.items():
            if normalized_key not in known_ids:
                extras.append(original)
        extra_var.set(",".join(extras))

    def _collect_traits(self, side: str) -> list[str]:
        variables = self.scenario_known_attacker_traits if side == "attacker" else self.scenario_known_defender_traits
        extra_var = self.scenario_attacker_extra_traits_var if side == "attacker" else self.scenario_defender_extra_traits_var
        selected = [trait_id for trait_id, _label, _description in TRAIT_OPTIONS if variables[trait_id].get()]
        extras = self._split_csv_values(extra_var.get()) or []
        merged: list[str] = []
        seen: set[str] = set()
        for item in selected + extras:
            normalized = item.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(item.strip())
        return merged

    def _refresh_scenario_weapon_listbox(self) -> None:
        listbox = self.scenario_weapon_listbox
        if listbox is None:
            return

        listbox.delete(0, "end")
        self.scenario_visible_weapon_records = []

        if self.scenario_catalog is None:
            listbox.insert("end", "请先载入原版装备目录")
            self._update_weapon_summary_from_vars()
            return

        filter_value = self.scenario_weapon_filter_var.get().strip() or "all"
        for record in self.scenario_catalog.weapons:
            if filter_value != "all" and record.attack_mode != filter_value:
                continue
            self.scenario_visible_weapon_records.append(record)
            listbox.insert("end", self._weapon_display_text(record))

        matched_index = self._matching_weapon_index_from_form()
        if matched_index is not None:
            listbox.selection_set(matched_index)
            listbox.see(matched_index)
            self._apply_weapon_record(self.scenario_visible_weapon_records[matched_index], append_log=False)
            return

        if not self.scenario_visible_weapon_records:
            listbox.insert("end", "当前筛选条件下没有武器")
        self._update_weapon_summary_from_vars()

    def _matching_weapon_index_from_form(self) -> int | None:
        target_name = self.weapon_name_var.get().strip().lower()
        if not target_name:
            return None
        for index, record in enumerate(self.scenario_visible_weapon_records):
            if record.label.strip().lower() == target_name or record.def_name.strip().lower() == target_name:
                return index
        return None

    def _on_weapon_selected(self, _event: object) -> None:
        if self.scenario_weapon_listbox is None:
            return
        selection = self.scenario_weapon_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(self.scenario_visible_weapon_records):
            return
        self._apply_weapon_record(self.scenario_visible_weapon_records[index])

    def _apply_weapon_record(self, record: VanillaWeaponRecord, *, append_log: bool = True) -> None:
        self.weapon_name_var.set(record.label)
        self.weapon_attack_mode_var.set(record.attack_mode)
        self.weapon_damage_type_var.set(record.damage_type)
        self.weapon_damage_var.set(self._format_number(record.damage))
        self.weapon_armor_penetration_var.set(self._format_number(record.armor_penetration))
        self.weapon_warmup_var.set(self._format_number(record.warmup_seconds))
        self.weapon_cooldown_var.set(self._format_number(record.cooldown_seconds))
        self.weapon_burst_count_var.set(str(record.burst_shot_count))
        self.weapon_burst_interval_var.set(self._format_number(record.burst_shot_interval_seconds))
        self.weapon_accuracy_close_var.set(self._format_number(record.accuracy_close))
        self.weapon_accuracy_short_var.set(self._format_number(record.accuracy_short))
        self.weapon_accuracy_medium_var.set(self._format_number(record.accuracy_medium))
        self.weapon_accuracy_long_var.set(self._format_number(record.accuracy_long))
        self._update_weapon_summary_from_vars(source_package=record.source_package)
        if append_log:
            self._append_log(f"已选择武器: {record.label}")

    def _update_weapon_summary_from_vars(self, source_package: str | None = None) -> None:
        weapon_name = self.weapon_name_var.get().strip()
        if not weapon_name:
            self.scenario_weapon_summary_var.set("还没有选择武器。载入原版装备目录后，在列表中点选即可。")
            return

        attack_mode = self._attack_mode_label(self.weapon_attack_mode_var.get().strip() or "ranged")
        damage_type = self._damage_type_label(self.weapon_damage_type_var.get().strip() or "Sharp")
        summary = (
            f"当前武器：{weapon_name}  |  {attack_mode}  |  {damage_type}  |  "
            f"伤害 {self.weapon_damage_var.get().strip() or '-'}  |  "
            f"穿甲 {self.weapon_armor_penetration_var.get().strip() or '-'}"
        )
        if source_package:
            summary += f"  |  来源 {source_package}"
        self.scenario_weapon_summary_var.set(summary)

    def _refresh_catalog_apparel_listbox(self) -> None:
        listbox = self.scenario_catalog_apparel_listbox
        if listbox is None:
            return

        listbox.delete(0, "end")
        self.scenario_visible_apparel_records = []

        if self.scenario_catalog is None:
            listbox.insert("end", "请先载入原版装备目录")
            return

        for record in self.scenario_catalog.apparel:
            self.scenario_visible_apparel_records.append(record)
            listbox.insert("end", self._apparel_display_text(record))

        if not self.scenario_visible_apparel_records:
            listbox.insert("end", "目录里没有可用护具")

    def _selected_catalog_apparel_record(self) -> VanillaApparelRecord | None:
        listbox = self.scenario_catalog_apparel_listbox
        if listbox is None:
            return None
        selection = listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self.scenario_visible_apparel_records):
            return None
        return self.scenario_visible_apparel_records[index]

    def _on_catalog_apparel_selected(self, _event: object) -> None:
        record = self._selected_catalog_apparel_record()
        if record is None:
            self._update_apparel_summary()
            return
        self.scenario_apparel_summary_var.set(
            f"当前可选护具：{record.label}  |  层级 {', '.join(record.layers) or '-'}  |  "
            f"覆盖 {', '.join(record.body_part_groups) or '-'}  |  "
            f"锐 {self._format_number(record.armor_sharp)} / 钝 {self._format_number(record.armor_blunt)} / "
            f"热 {self._format_number(record.armor_heat)}"
        )

    def _add_selected_catalog_apparel(self) -> None:
        record = self._selected_catalog_apparel_record()
        if record is None:
            messagebox.showinfo("未选择护具", "请先在左侧列表中选中一件护具。")
            return
        self.scenario_apparel_state.items.append(
            {
                "name": record.label,
                "source": record.source_package,
                "layers": list(record.layers),
                "covers": list(record.body_part_groups),
                "armor_sharp": record.armor_sharp,
                "armor_blunt": record.armor_blunt,
                "armor_heat": record.armor_heat,
            }
        )
        self._refresh_apparel_listbox(select_index=len(self.scenario_apparel_state.items) - 1)
        self._clear_current_apparel_fields()
        self._update_apparel_summary()
        self._append_log(f"已为防守方添加护具: {record.label}")

    def _upsert_current_apparel(self) -> None:
        try:
            apparel_name = self._require_non_empty(self.apparel_name_var.get(), "护具名称不能为空。")
            apparel_item = {
                "name": apparel_name,
                "source": self.apparel_source_var.get().strip() or "manual",
                "layers": self._split_csv_values(self.apparel_layers_var.get()) or [],
                "covers": self._split_csv_values(self.apparel_covers_var.get()) or [],
                "armor_sharp": self._parse_float(self.apparel_armor_sharp_var.get(), "锐器护甲"),
                "armor_blunt": self._parse_float(self.apparel_armor_blunt_var.get(), "钝器护甲"),
                "armor_heat": self._parse_float(self.apparel_armor_heat_var.get(), "热护甲"),
            }
            selected_index = self._selected_apparel_index()
            target_index: int
            if selected_index is None:
                self.scenario_apparel_state.items.append(apparel_item)
                self._append_log(f"已新增护具: {apparel_name}")
                target_index = len(self.scenario_apparel_state.items) - 1
            else:
                self.scenario_apparel_state.items[selected_index] = apparel_item
                self._append_log(f"已更新护具: {apparel_name}")
                target_index = selected_index
            self._refresh_apparel_listbox(select_index=target_index)
            self._update_apparel_summary()
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _remove_selected_apparel(self) -> None:
        selected_index = self._selected_apparel_index()
        if selected_index is None:
            messagebox.showinfo("未选择护具", "请先在右侧“已穿戴护具”中选中一件护具。")
            return
        removed = self.scenario_apparel_state.items.pop(selected_index)
        self._refresh_apparel_listbox()
        self._clear_current_apparel_fields()
        self._update_apparel_summary()
        self._append_log(f"已移除护具: {removed.get('name', 'unnamed')}")

    def _clear_all_apparel(self) -> None:
        if not self.scenario_apparel_state.items:
            return
        self.scenario_apparel_state.items.clear()
        self._refresh_apparel_listbox()
        self._clear_current_apparel_fields()
        self._update_apparel_summary()
        self._append_log("已清空防守方的全部护具。")

    def _clear_current_apparel_fields(self) -> None:
        self.apparel_name_var.set("")
        self.apparel_source_var.set("manual")
        self.apparel_layers_var.set("")
        self.apparel_covers_var.set("")
        self.apparel_armor_sharp_var.set("0")
        self.apparel_armor_blunt_var.set("0")
        self.apparel_armor_heat_var.set("0")
        if self.scenario_apparel_state.listbox is not None:
            self.scenario_apparel_state.listbox.selection_clear(0, "end")

    def _refresh_apparel_listbox(self, select_index: int | None = None) -> None:
        listbox = self.scenario_apparel_state.listbox
        if listbox is None:
            return
        listbox.delete(0, "end")
        if not self.scenario_apparel_state.items:
            listbox.insert("end", "还没有护具")
            return
        for item in self.scenario_apparel_state.items:
            layers = ",".join(self._ensure_string_list(item.get("layers", []))) or "-"
            covers = ",".join(self._ensure_string_list(item.get("covers", []))) or "-"
            listbox.insert("end", f"{item.get('name', 'unnamed')}  [{layers}]  ->  {covers}")
        if select_index is not None and 0 <= select_index < len(self.scenario_apparel_state.items):
            listbox.selection_set(select_index)
            listbox.see(select_index)

    def _on_apparel_selected(self, _event: object) -> None:
        selected_index = self._selected_apparel_index()
        if selected_index is None:
            self._update_apparel_summary()
            return
        item = self.scenario_apparel_state.items[selected_index]
        self.apparel_name_var.set(str(item.get("name", "")))
        self.apparel_source_var.set(str(item.get("source", "manual")))
        self.apparel_layers_var.set(",".join(self._ensure_string_list(item.get("layers", []))))
        self.apparel_covers_var.set(",".join(self._ensure_string_list(item.get("covers", []))))
        self.apparel_armor_sharp_var.set(str(item.get("armor_sharp", 0)))
        self.apparel_armor_blunt_var.set(str(item.get("armor_blunt", 0)))
        self.apparel_armor_heat_var.set(str(item.get("armor_heat", 0)))
        self._update_apparel_summary()

    def _update_apparel_summary(self) -> None:
        count = len(self.scenario_apparel_state.items)
        selected_index = self._selected_apparel_index()
        if selected_index is not None:
            item = self.scenario_apparel_state.items[selected_index]
            layers = ",".join(self._ensure_string_list(item.get("layers", []))) or "-"
            covers = ",".join(self._ensure_string_list(item.get("covers", []))) or "-"
            self.scenario_apparel_summary_var.set(
                f"已穿戴 {count} 件护具。当前选中：{item.get('name', 'unnamed')}  |  "
                f"层级 {layers}  |  覆盖 {covers}"
            )
            return
        if count:
            self.scenario_apparel_summary_var.set(f"已穿戴 {count} 件护具。可在右侧列表中点选一件查看和修改。")
            return
        self.scenario_apparel_summary_var.set("还没有为防守方穿戴护具。可从左侧列表中点选并添加。")

    def _selected_apparel_index(self) -> int | None:
        listbox = self.scenario_apparel_state.listbox
        if listbox is None:
            return None
        selection = listbox.curselection()
        if not selection or not self.scenario_apparel_state.items:
            return None
        index = selection[0]
        if index >= len(self.scenario_apparel_state.items):
            return None
        return index

    def _submit_inventory_workflow(self) -> None:
        try:
            self._run_background_workflow(
                "inventory",
                "开始扫描 RimWorld / Mod 元数据",
                run_inventory_workflow,
                {
                    "game_data_root": self.inventory_game_data_var.get(),
                    "local_mods_root": self.inventory_local_mods_var.get(),
                    "workshop_root": self.inventory_workshop_var.get(),
                    "save_data_root": self.inventory_save_var.get(),
                    "output_dir": self.inventory_output_var.get(),
                },
            )
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _submit_vanilla_workflow(self) -> None:
        try:
            game_data_root = self._require_non_empty(self.vanilla_game_data_var.get(), "原版分析需要游戏 Data 路径。")
            self._run_background_workflow(
                "vanilla",
                "正在生成原版武器和护具目录",
                run_vanilla_workflow,
                {
                    "game_data_root": game_data_root,
                    "output_dir": self.vanilla_output_var.get(),
                    "ranged_distance_cells": self._parse_int(self.vanilla_distance_var.get(), "分析距离"),
                    "shooting_skill": self._parse_int(self.vanilla_shooting_skill_var.get(), "射击技能"),
                    "melee_skill": self._parse_int(self.vanilla_melee_skill_var.get(), "近战技能"),
                },
            )
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _submit_scenario_workflow(self) -> None:
        try:
            payload = self._build_scenario_payload_from_form()
            self._run_background_workflow(
                "scenario",
                "正在分析当前场景",
                run_scenario_payload_workflow,
                {
                    "payload": payload,
                    "output_path": self.scenario_output_var.get(),
                },
            )
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _submit_library_workflow(self) -> None:
        try:
            library_path = self._require_non_empty(self.library_path_var.get(), "场景库分析需要场景库文件路径。")
            game_data_root = self._require_non_empty(self.library_game_data_var.get(), "场景库分析需要游戏 Data 路径。")
            selected_tags = self._selected_library_tags()
            selected_ids = self._selected_library_scenario_ids()
            self.library_tags_var.set(",".join(selected_tags))
            self.library_ids_var.set(",".join(selected_ids))
            self._update_library_selection_summary()
            self._run_background_workflow(
                "library",
                "开始批量分析场景库",
                run_library_workflow,
                {
                    "library_path": library_path,
                    "game_data_root": game_data_root,
                    "output_dir": self.library_output_var.get(),
                    "tags": selected_tags or None,
                    "scenario_ids": selected_ids or None,
                    "name_contains": self.library_name_contains_var.get().strip() or None,
                },
            )
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _run_background_workflow(
        self,
        workflow_key: str,
        start_message: str,
        worker,
        kwargs: dict[str, object],
    ) -> None:
        if self._busy:
            messagebox.showinfo("任务进行中", "当前已有任务在运行，请等待完成后再发起新的分析。")
            return

        self._busy = True
        self.status_var.set(start_message)
        self._append_log(start_message)

        def runner() -> None:
            try:
                result = worker(**kwargs)
                self.log_queue.put(("result", workflow_key, result))
            except Exception as exc:  # pragma: no cover - UI error path
                self.log_queue.put(("error", workflow_key, (str(exc), traceback.format_exc())))

        threading.Thread(target=runner, daemon=True).start()

    def _poll_worker_events(self) -> None:
        try:
            while True:
                event_type, workflow_key, payload = self.log_queue.get_nowait()
                if event_type == "result":
                    self._busy = False
                    result = payload
                    self._render_workflow_result(workflow_key, result)
                    self.status_var.set(result.title)
                    self._append_log(result.title)
                elif event_type == "catalog":
                    self._busy = False
                    self._apply_loaded_catalog(payload)
                elif event_type == "error":
                    self._busy = False
                    message, tb = payload
                    self.status_var.set("任务失败")
                    self._append_log(tb)
                    messagebox.showerror("任务失败", message)
        except queue.Empty:
            pass
        self.after(120, self._poll_worker_events)

    def _apply_loaded_catalog(self, catalog: VanillaCatalog) -> None:
        self.scenario_catalog = catalog
        self.scenario_catalog_status_var.set(
            f"已载入原版装备目录：{len(catalog.weapons)} 把武器，{len(catalog.apparel)} 件护具。"
            " 现在可以直接点选，不需要手工输入名称。"
        )
        self._refresh_scenario_weapon_listbox()
        self._refresh_catalog_apparel_listbox()
        self._update_weapon_summary_from_vars()
        self._update_apparel_summary()
        message = f"已载入原版装备目录：{len(catalog.weapons)} 把武器，{len(catalog.apparel)} 件护具。"
        self.status_var.set(message)
        self._append_log(message)

    def _render_workflow_result(self, workflow_key: str, result: WorkflowResult) -> None:
        widgets = self._result_widgets[workflow_key]
        for child in widgets.cards_frame.winfo_children():
            child.destroy()

        for index, card in enumerate(result.cards):
            widgets.cards_frame.grid_columnconfigure(index, weight=1)
            card_bg = self.colors["panel_alt"]
            value_color = self.colors["ink"]
            if card.tone == "accent":
                card_bg = self.colors["accent_soft"]
                value_color = self.colors["accent"]
            elif card.tone == "good":
                card_bg = "#dcebdc"
                value_color = self.colors["good"]
            elif card.tone == "bad":
                card_bg = "#f2d8d4"
                value_color = self.colors["bad"]

            frame = tk.Frame(
                widgets.cards_frame,
                bg=card_bg,
                highlightthickness=1,
                highlightbackground=self.colors["line"],
                padx=14,
                pady=14,
            )
            frame.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < len(result.cards) - 1 else 0))
            tk.Label(
                frame,
                text=card.label,
                bg=card_bg,
                fg=self.colors["muted"],
                font=self.card_fonts["title"],
                anchor="w",
            ).pack(anchor="w")
            tk.Label(
                frame,
                text=card.value,
                bg=card_bg,
                fg=value_color,
                font=self.card_fonts["value"],
                anchor="w",
            ).pack(anchor="w", pady=(8, 0))

        widgets.details_text.configure(state="normal")
        widgets.details_text.delete("1.0", "end")
        widgets.details_text.insert("1.0", "\n".join(result.details) + "\n")
        widgets.details_text.configure(state="disabled")

        widgets.outputs_listbox.delete(0, "end")
        widgets.outputs = list(result.outputs.items())
        if widgets.outputs:
            for label, path in widgets.outputs:
                widgets.outputs_listbox.insert("end", f"{label}  ->  {path.name}")
            widgets.outputs_listbox.selection_set(0)
            widgets.open_file_button.configure(state="normal")
            widgets.open_dir_button.configure(state="normal")
        else:
            widgets.outputs_listbox.insert("end", "这次任务没有生成输出文件")
            widgets.open_file_button.configure(state="disabled")
            widgets.open_dir_button.configure(state="disabled")

        has_html_report = any(label == "comparison_report_html" for label, _path in widgets.outputs)
        widgets.open_report_button.configure(state="normal" if has_html_report else "disabled")

    def _open_selected_output(self, widgets: ResultWidgets) -> None:
        selection = widgets.outputs_listbox.curselection()
        if not selection or not widgets.outputs:
            return
        _label, path = widgets.outputs[selection[0]]
        self._open_path(path)

    def _open_output_directory(self, widgets: ResultWidgets) -> None:
        if widgets.outputs:
            self._open_path(widgets.outputs[0][1].parent)

    def _open_report_output(self, widgets: ResultWidgets, report_key: str | None) -> None:
        if report_key is None:
            return
        for label, path in widgets.outputs:
            if label == report_key:
                webbrowser.open(path.resolve().as_uri())
                return

    def _open_path(self, path: Path) -> None:
        resolved = path.resolve()
        if os.name == "nt":
            os.startfile(resolved)  # type: ignore[attr-defined]
            return
        if sys.platform == "darwin":  # pragma: no cover - non-Windows fallback
            subprocess.run(["open", str(resolved)], check=False)
            return
        subprocess.run(["xdg-open", str(resolved)], check=False)  # pragma: no cover - non-Windows fallback

    def _browse_path(
        self,
        variable: tk.StringVar,
        *,
        mode: str,
        file_types: list[tuple[str, str]] | None = None,
    ) -> None:
        selected: str | None = None
        if mode == "directory":
            selected = filedialog.askdirectory()
        elif mode == "file":
            selected = filedialog.askopenfilename(filetypes=file_types or [("所有文件", "*.*")])
        elif mode == "save":
            selected = filedialog.asksaveasfilename(filetypes=file_types or [("所有文件", "*.*")])
        if selected:
            variable.set(selected)

    def _open_log_window(self) -> None:
        if self.log_window is not None and self.log_window.winfo_exists():
            self.log_window.deiconify()
            self.log_window.lift()
            return

        self.log_window = tk.Toplevel(self)
        self.log_window.title("工作日志")
        self.log_window.geometry("880x520")
        self.log_window.configure(bg=self.colors["panel"])
        self.log_window.protocol("WM_DELETE_WINDOW", self._close_log_window)
        self.log_window.grid_rowconfigure(0, weight=1)
        self.log_window.grid_columnconfigure(0, weight=1)

        shell = tk.Frame(self.log_window, bg=self.colors["panel"], padx=16, pady=16)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_rowconfigure(1, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        tk.Label(
            shell,
            text="工作日志",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.log_text = tk.Text(
            shell,
            bg=self.colors["log_bg"],
            fg=self.colors["ink"],
            relief="flat",
            wrap="word",
            padx=12,
            pady=12,
            insertbackground=self.colors["accent"],
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self._render_log_text()

    def _close_log_window(self) -> None:
        if self.log_window is not None and self.log_window.winfo_exists():
            self.log_window.destroy()
        self.log_window = None
        self.log_text = None

    def _append_log(self, message: str) -> None:
        self.log_lines.append(message)
        self._render_log_text()

    def _render_log_text(self) -> None:
        if self.log_text is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", "\n".join(self.log_lines) + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    @staticmethod
    def _parse_int(value: str, field_name: str) -> int:
        try:
            return int(value.strip())
        except ValueError as exc:
            raise ValueError(f"{field_name} 必须是整数。") from exc

    @staticmethod
    def _parse_float(value: str, field_name: str) -> float:
        try:
            return float(value.strip())
        except ValueError as exc:
            raise ValueError(f"{field_name} 必须是数字。") from exc

    @staticmethod
    def _split_csv_values(value: str) -> list[str] | None:
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items or None

    @staticmethod
    def _ensure_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _require_non_empty(value: str, error_message: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(error_message)
        return normalized

    @staticmethod
    def _format_number(value: float | str) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _attack_mode_label(value: str) -> str:
        return {"ranged": "远程", "melee": "近战"}.get(value.strip().lower(), value)

    @staticmethod
    def _damage_type_label(value: str) -> str:
        return {"sharp": "锐器", "blunt": "钝器", "heat": "热伤"}.get(value.strip().lower(), value)

    def _weapon_display_text(self, record: VanillaWeaponRecord) -> str:
        return (
            f"{record.label}  ·  {self._attack_mode_label(record.attack_mode)}  ·  "
            f"伤害 {self._format_number(record.damage)}  ·  {record.source_package}"
        )

    def _apparel_display_text(self, record: VanillaApparelRecord) -> str:
        return (
            f"{record.label}  ·  {','.join(record.layers) or '-'}  ·  "
            f"锐 {self._format_number(record.armor_sharp)}  ·  {record.source_package}"
        )

    def _region_display_for_value(self, value: str) -> str:
        for label, raw in BODY_REGION_OPTIONS:
            if raw == value:
                return label
        return BODY_REGION_OPTIONS[0][0]

    def _cover_display_for_value(self, value: str) -> str:
        try:
            numeric = float(value)
        except ValueError:
            return COVER_PRESET_OPTIONS[0][0]
        for label, preset in COVER_PRESET_OPTIONS:
            if abs(preset - numeric) < 0.0001:
                return label
        return f"{int(round(numeric * 100))}% 自定义"


def main() -> int:
    app = RimDataAnalysisDesktopApp()
    app.mainloop()
    return 0


from rim_data_analysis.desktop_user_app import RimDataAnalysisDesktopApp as _UserFacingDesktopApp
from rim_data_analysis.desktop_user_app import main as _user_facing_main


RimDataAnalysisDesktopApp = _UserFacingDesktopApp
main = _user_facing_main
