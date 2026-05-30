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
from rim_data_analysis.desktop_app_ui import RimDataAnalysisDesktopApp as _NewRimDataAnalysisDesktopApp
from rim_data_analysis.desktop_app_ui import main as _new_main


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
        self.title("Rim 数据分析工作台")
        self.geometry("1440x940")
        self.minsize(1220, 820)

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
            "value": ("Bahnschrift", 26, "bold"),
        }
        self.status_var = tk.StringVar(value="桌面工作台已就绪")
        self.log_queue: queue.Queue[tuple[str, str, object]] = queue.Queue()
        self._busy = False
        self._result_widgets: dict[str, ResultWidgets] = {}
        self.scenario_apparel_state = ScenarioApparelEditorState(items=[])

        self.repo_root = Path(__file__).resolve().parents[2]
        self.discovered_paths = discover_paths()

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

        self.scenario_path_var = tk.StringVar()
        self.scenario_output_var = tk.StringVar(value=str(Path("artifacts") / "gui-scenario" / "current-scenario.json"))
        self.scenario_name_var = tk.StringVar()
        self.attacker_name_var = tk.StringVar()
        self.attacker_shooting_skill_var = tk.StringVar(value="10")
        self.attacker_melee_skill_var = tk.StringVar(value="10")
        self.attacker_traits_var = tk.StringVar()
        self.defender_name_var = tk.StringVar()
        self.defender_shooting_skill_var = tk.StringVar(value="10")
        self.defender_melee_skill_var = tk.StringVar(value="10")
        self.defender_traits_var = tk.StringVar()
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
        self.context_cover_block_var = tk.StringVar(value="0")
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

    def _configure_window(self) -> None:
        self.configure(bg=self.colors["bg"])
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI Variable Text", size=10)
        text_font = font.nametofont("TkTextFont")
        text_font.configure(family="Segoe UI Variable Text", size=10)
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
            padding=(18, 12),
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

        header = tk.Frame(self, bg=self.colors["bg"], padx=24, pady=20)
        header.grid(row=0, column=0, sticky="nsew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        hero = tk.Frame(
            header,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=24,
            pady=20,
        )
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        tk.Label(
            hero,
            text="Rim 数据分析工作台",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 28, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            hero,
            text="桌面工作台把 CLI 分析流程包装成软件界面，适合直接做原版目录分析、单场景编辑分析，以及场景库批量对比。",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Segoe UI Variable Text", 11),
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        status_card = tk.Frame(
            header,
            bg=self.colors["panel_alt"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=22,
            pady=20,
            width=250,
        )
        status_card.grid(row=0, column=1, sticky="nsew")
        status_card.grid_propagate(False)
        tk.Label(
            status_card,
            text="桌面版 V1",
            bg=self.colors["panel_alt"],
            fg=self.colors["accent"],
            font=("Bahnschrift", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            status_card,
            text="核心分析流程\n已进入桌面界面",
            bg=self.colors["panel_alt"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 18, "bold"),
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 6))

        content = tk.Frame(self, bg=self.colors["bg"], padx=24)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(content, style="Workbench.TNotebook")
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self._build_inventory_tab()
        self._build_vanilla_tab()
        self._build_scenario_tab()
        self._build_library_tab()

        footer = tk.Frame(self, bg=self.colors["bg"], padx=24, pady=8)
        footer.grid(row=2, column=0, sticky="nsew")
        footer.grid_columnconfigure(0, weight=1)

        log_shell = tk.Frame(
            footer,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=18,
            pady=16,
        )
        log_shell.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            log_shell,
            text="工作日志",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.log_text = tk.Text(
            log_shell,
            height=7,
            bg=self.colors["log_bg"],
            fg=self.colors["ink"],
            relief="flat",
            wrap="word",
            padx=12,
            pady=10,
            insertbackground=self.colors["accent"],
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        log_shell.grid_rowconfigure(1, weight=1)
        log_shell.grid_columnconfigure(0, weight=1)
        self.log_text.insert("1.0", "工作台已启动。\n")
        self.log_text.configure(state="disabled")

        status_bar = tk.Frame(self, bg=self.colors["accent"], padx=24, pady=8)
        status_bar.grid(row=3, column=0, sticky="ew")
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg=self.colors["accent"],
            fg="#fff6ec",
            font=("Segoe UI Variable Text", 10),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)

    def _build_inventory_tab(self) -> None:
        frame = self._create_tab_shell("包扫描", "扫描 Core、DLC、本地 Mods 和 Workshop 的元数据。")
        control, result = self._split_tab(frame)

        self._path_row(control, "游戏 Data 路径", self.inventory_game_data_var, mode="directory")
        self._path_row(control, "本地 Mods 路径", self.inventory_local_mods_var, mode="directory")
        self._path_row(control, "Workshop 路径", self.inventory_workshop_var, mode="directory")
        self._path_row(control, "存档路径", self.inventory_save_var, mode="directory")
        self._path_row(control, "输出目录", self.inventory_output_var, mode="directory")
        self._button_bar(
            control,
            [
                ("加载自动发现", self._load_discovered_inventory_paths, "Subtle.TButton"),
                ("载入仓库样例", self._load_inventory_fixture_paths, "Subtle.TButton"),
                ("开始扫描", self._submit_inventory_workflow, "Primary.TButton"),
            ],
        )
        self._result_widgets["inventory"] = self._create_result_panel(result)

    def _build_vanilla_tab(self) -> None:
        frame = self._create_tab_shell("原版分析", "从原版 Core + DLC 提取武器和护具，并生成基础 matchup 表。")
        control, result = self._split_tab(frame)

        self._path_row(control, "游戏 Data 路径", self.vanilla_game_data_var, mode="directory")
        self._path_row(control, "输出目录", self.vanilla_output_var, mode="directory")
        self._entry_row(control, "远程分析距离", self.vanilla_distance_var)
        self._entry_row(control, "射击技能", self.vanilla_shooting_skill_var)
        self._entry_row(control, "近战技能", self.vanilla_melee_skill_var)
        self._button_bar(
            control,
            [
                ("加载自动发现", self._load_discovered_vanilla_paths, "Subtle.TButton"),
                ("载入仓库样例", self._load_vanilla_fixture_paths, "Subtle.TButton"),
                ("生成原版目录", self._submit_vanilla_workflow, "Primary.TButton"),
            ],
        )
        self._result_widgets["vanilla"] = self._create_result_panel(result)

    def _build_scenario_tab(self) -> None:
        frame = self._create_tab_shell("场景编辑器", "在表单里编辑单场景，支持从 JSON 载入、保存并直接分析。")
        control, result = self._split_tab(frame)
        form = self._create_scrollable_form(control, bg=self.colors["panel_alt"])

        self._path_row(
            form,
            "场景文件",
            self.scenario_path_var,
            mode="file",
            file_types=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        self._path_row(
            form,
            "输出 JSON",
            self.scenario_output_var,
            mode="save",
            file_types=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        self._button_bar(
            form,
            [
                ("载入样例", self._load_scenario_fixture_paths, "Subtle.TButton"),
                ("从文件载入", self._load_scenario_from_selected_file, "Subtle.TButton"),
            ],
        )
        self._button_bar(
            form,
            [
                ("保存当前场景", self._save_current_scenario, "Subtle.TButton"),
                ("分析当前表单", self._submit_scenario_workflow, "Primary.TButton"),
            ],
        )
        self._build_scenario_editor_fields(form)
        self._result_widgets["scenario"] = self._create_result_panel(result)

    def _build_library_tab(self) -> None:
        frame = self._create_tab_shell("场景库", "批量分析模板化场景，并生成 CSV、JSON 和 HTML 对比输出。")
        control, result = self._split_tab(frame)

        self._path_row(
            control,
            "场景库文件",
            self.library_path_var,
            mode="file",
            file_types=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        self._path_row(control, "游戏 Data 路径", self.library_game_data_var, mode="directory")
        self._path_row(control, "输出目录", self.library_output_var, mode="directory")
        self._entry_row(control, "标签过滤", self.library_tags_var, hint="多个标签用英文逗号分隔")
        self._entry_row(control, "场景 ID 过滤", self.library_ids_var, hint="多个 ID 用英文逗号分隔")
        self._entry_row(control, "名称包含", self.library_name_contains_var)
        self._button_bar(
            control,
            [
                ("加载自动发现", self._load_discovered_library_paths, "Subtle.TButton"),
                ("载入仓库样例", self._load_library_fixture_paths, "Subtle.TButton"),
                ("批量分析", self._submit_library_workflow, "Primary.TButton"),
            ],
        )
        self._result_widgets["library"] = self._create_result_panel(result, report_key="comparison_report_html")

    def _create_tab_shell(self, title: str, description: str) -> ttk.Frame:
        shell = ttk.Frame(self.notebook, padding=18)
        shell.grid_rowconfigure(1, weight=1)
        shell.grid_columnconfigure(0, weight=1)
        self.notebook.add(shell, text=title)

        header = tk.Frame(shell, bg=self.colors["panel"], padx=8, pady=8)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(
            header,
            text=title,
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 20, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text=description,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=("Segoe UI Variable Text", 10),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        return shell

    def _split_tab(self, shell: ttk.Frame) -> tuple[tk.Frame, tk.Frame]:
        body = tk.Frame(shell, bg=self.colors["panel"])
        body.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)

        control = tk.Frame(
            body,
            bg=self.colors["panel_alt"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            padx=18,
            pady=18,
            width=430,
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

        canvas = tk.Canvas(
            shell,
            bg=bg,
            highlightthickness=0,
            relief="flat",
            bd=0,
        )
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        inner = tk.Frame(canvas, bg=bg)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )
        return inner

    def _section_label(self, parent: tk.Frame, title: str, description: str | None = None) -> None:
        shell = tk.Frame(parent, bg=self.colors["panel_alt"])
        shell.pack(fill="x", pady=(14, 10))
        tk.Label(
            shell,
            text=title,
            bg=self.colors["panel_alt"],
            fg=self.colors["accent"],
            font=("Bahnschrift", 13, "bold"),
            anchor="w",
        ).pack(anchor="w")
        if description:
            tk.Label(
                shell,
                text=description,
                bg=self.colors["panel_alt"],
                fg=self.colors["muted"],
                font=("Segoe UI Variable Text", 9),
                anchor="w",
                justify="left",
                wraplength=360,
            ).pack(anchor="w", pady=(4, 0))

    def _combobox_row(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        *,
        values: list[str],
    ) -> ttk.Combobox:
        row = tk.Frame(parent, bg=self.colors["panel_alt"])
        row.pack(fill="x", pady=(0, 12))
        tk.Label(
            row,
            text=label,
            bg=self.colors["panel_alt"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
            anchor="w",
        ).pack(anchor="w")
        combo = ttk.Combobox(row, textvariable=variable, values=values, state="readonly")
        combo.pack(fill="x", pady=(6, 0), ipady=4)
        return combo

    def _checkbox_row(self, parent: tk.Frame, label: str, variable: tk.BooleanVar) -> None:
        row = tk.Frame(parent, bg=self.colors["panel_alt"])
        row.pack(fill="x", pady=(0, 12))
        checkbox = tk.Checkbutton(
            row,
            text=label,
            variable=variable,
            bg=self.colors["panel_alt"],
            fg=self.colors["ink"],
            activebackground=self.colors["panel_alt"],
            activeforeground=self.colors["ink"],
            selectcolor="#fffdf8",
            anchor="w",
            justify="left",
            font=("Segoe UI Variable Text", 10),
        )
        checkbox.pack(anchor="w")

    def _build_scenario_editor_fields(self, parent: tk.Frame) -> None:
        self._section_label(parent, "场景基本信息", "这里编辑一个完整的单场景，不需要手写 JSON。")
        self._entry_row(parent, "场景名称", self.scenario_name_var)

        self._section_label(parent, "攻击方", "用逗号分隔多个特性，例如 careful_shooter,brawler。")
        self._entry_row(parent, "攻击方名称", self.attacker_name_var)
        self._entry_row(parent, "射击技能", self.attacker_shooting_skill_var)
        self._entry_row(parent, "近战技能", self.attacker_melee_skill_var)
        self._entry_row(parent, "特性", self.attacker_traits_var, hint="多个特性用英文逗号分隔")

        self._section_label(parent, "防守方", "防守方护具通过下面的护具列表维护。")
        self._entry_row(parent, "防守方名称", self.defender_name_var)
        self._entry_row(parent, "射击技能", self.defender_shooting_skill_var)
        self._entry_row(parent, "近战技能", self.defender_melee_skill_var)
        self._entry_row(parent, "特性", self.defender_traits_var, hint="多个特性用英文逗号分隔")

        self._section_label(parent, "防守方护具", "先选中护具再修改；不选中时会新增一件。")
        self._build_apparel_editor(parent)

        self._section_label(parent, "武器", "近战武器可忽略精度字段；远程武器建议填写完整。")
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

        self._section_label(parent, "战斗上下文", "控制距离、目标部位和掩体影响。")
        self._entry_row(parent, "距离（格）", self.context_distance_var)
        self._entry_row(parent, "目标部位", self.context_region_var)
        self._entry_row(parent, "掩体挡住概率", self.context_cover_block_var)
        self._entry_row(parent, "命中倍率", self.context_hit_multiplier_var)
        self._checkbox_row(parent, "目标正在瞄准或开火（用于近战闪避）", self.context_target_aiming_var)

    def _build_apparel_editor(self, parent: tk.Frame) -> None:
        listbox_shell = tk.Frame(parent, bg=self.colors["panel_alt"])
        listbox_shell.pack(fill="x", pady=(0, 12))

        self.scenario_apparel_state.listbox = tk.Listbox(
            listbox_shell,
            height=5,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff8f0",
        )
        self.scenario_apparel_state.listbox.pack(fill="x")
        self.scenario_apparel_state.listbox.bind("<<ListboxSelect>>", self._on_apparel_selected)

        self._entry_row(parent, "护具名称", self.apparel_name_var)
        self._entry_row(parent, "来源", self.apparel_source_var)
        self._entry_row(parent, "层级", self.apparel_layers_var, hint="多个层级用英文逗号分隔，例如 Shell,Middle")
        self._entry_row(parent, "覆盖部位", self.apparel_covers_var, hint="多个部位用英文逗号分隔，例如 Torso,Arms")
        self._entry_row(parent, "锐器护甲", self.apparel_armor_sharp_var)
        self._entry_row(parent, "钝器护甲", self.apparel_armor_blunt_var)
        self._entry_row(parent, "热护甲", self.apparel_armor_heat_var)
        self._button_bar(
            parent,
            [
                ("新增/更新护具", self._upsert_current_apparel, "Subtle.TButton"),
                ("删除选中护具", self._remove_selected_apparel, "Subtle.TButton"),
            ],
        )
        self._button_bar(
            parent,
            [
                ("清空护具输入", self._clear_current_apparel_fields, "Subtle.TButton"),
            ],
        )

    def _path_row(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        *,
        mode: str,
        file_types: list[tuple[str, str]] | None = None,
    ) -> None:
        row = tk.Frame(parent, bg=self.colors["panel_alt"])
        row.pack(fill="x", pady=(0, 12))
        tk.Label(
            row,
            text=label,
            bg=self.colors["panel_alt"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 11, "bold"),
            anchor="w",
        ).pack(anchor="w")
        entry_shell = tk.Frame(row, bg=self.colors["panel_alt"])
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

    def _entry_row(self, parent: tk.Frame, label: str, variable: tk.StringVar, hint: str | None = None) -> None:
        row = tk.Frame(parent, bg=self.colors["panel_alt"])
        row.pack(fill="x", pady=(0, 12))
        tk.Label(
            row,
            text=label,
            bg=self.colors["panel_alt"],
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
                bg=self.colors["panel_alt"],
                fg=self.colors["muted"],
                font=("Segoe UI Variable Text", 9),
                anchor="w",
            ).pack(anchor="w", pady=(4, 0))

    def _button_bar(self, parent: tk.Frame, buttons: list[tuple[str, object, str]]) -> None:
        row = tk.Frame(parent, bg=self.colors["panel_alt"])
        row.pack(fill="x", pady=(8, 0))
        for text, command, style_name in buttons:
            ttk.Button(row, text=text, command=command, style=style_name).pack(side="left", padx=(0, 10))

    def _create_result_panel(self, parent: tk.Frame, report_key: str | None = None) -> ResultWidgets:
        tk.Label(
            parent,
            text="结果概览",
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
            text="执行摘要",
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
        details_text.insert("1.0", "尚未运行。\n")
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
            text="输出文件",
            bg=self.colors["panel"],
            fg=self.colors["ink"],
            font=("Bahnschrift", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        outputs_listbox = tk.Listbox(
            outputs_shell,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff8f0",
        )
        outputs_listbox.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        outputs_listbox.insert("end", "尚无输出文件")

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
        self._load_scenario_fixture_paths()

    def _load_discovered_inventory_paths(self) -> None:
        self.inventory_game_data_var.set(str(self.discovered_paths.game_data_root or ""))
        self.inventory_local_mods_var.set(str(self.discovered_paths.local_mods_root or ""))
        self.inventory_workshop_var.set(str(self.discovered_paths.workshop_root or ""))
        self.inventory_save_var.set(str(self.discovered_paths.save_data_root or ""))
        self._append_log("已载入自动发现的路径到包扫描页。")

    def _load_inventory_fixture_paths(self) -> None:
        self.inventory_game_data_var.set(str(self.repo_root / "tests" / "fixtures" / "game_data"))
        self.inventory_local_mods_var.set(str(self.repo_root / "tests" / "fixtures" / "local_mods"))
        self.inventory_workshop_var.set(str(self.repo_root / "tests" / "fixtures" / "workshop_mods"))
        self.inventory_save_var.set("")
        self.inventory_output_var.set(str(self.repo_root / "artifacts" / "gui-inventory-fixture"))
        self._append_log("已载入仓库自带的扫描样例路径。")

    def _load_discovered_vanilla_paths(self) -> None:
        self.vanilla_game_data_var.set(str(self.discovered_paths.game_data_root or ""))
        self._append_log("已载入自动发现的原版 Data 路径。")

    def _load_vanilla_fixture_paths(self) -> None:
        self.vanilla_game_data_var.set(str(self.repo_root / "tests" / "fixtures" / "vanilla_game_data"))
        self.vanilla_output_var.set(str(self.repo_root / "artifacts" / "gui-vanilla-fixture"))
        self._append_log("已载入仓库自带的原版分析样例路径。")

    def _load_scenario_fixture_paths(self) -> None:
        scenario_path = self.repo_root / "assets" / "scenarios" / "sample-ranged-vs-armor.json"
        self.scenario_path_var.set(str(scenario_path))
        self.scenario_output_var.set(str(self.repo_root / "artifacts" / "gui-scenario" / "sample-ranged-vs-armor.scenario.json"))
        self._load_scenario_payload_into_form(load_scenario_payload(scenario_path))
        self._append_log("已载入仓库自带的单场景样例。")

    def _load_discovered_library_paths(self) -> None:
        self.library_game_data_var.set(str(self.discovered_paths.game_data_root or ""))
        self._append_log("已载入自动发现的场景库原版 Data 路径。")

    def _load_library_fixture_paths(self) -> None:
        self.library_path_var.set(str(self.repo_root / "assets" / "scenario-libraries" / "sample-library.json"))
        self.library_game_data_var.set(str(self.repo_root / "tests" / "fixtures" / "vanilla_game_data"))
        self.library_output_var.set(str(self.repo_root / "artifacts" / "gui-library-fixture"))
        self._append_log("已载入仓库自带的场景库样例。")

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
            output_path = self._require_non_empty(self.scenario_output_var.get(), "请指定场景保存路径。")
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
        self.attacker_traits_var.set(",".join(self._ensure_string_list(attacker.get("traits", []))))

        self.defender_name_var.set(str(defender.get("name", "")))
        self.defender_shooting_skill_var.set(str(defender.get("shooting_skill", 10)))
        self.defender_melee_skill_var.set(str(defender.get("melee_skill", 10)))
        self.defender_traits_var.set(",".join(self._ensure_string_list(defender.get("traits", []))))

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

        apparel_items = defender.get("apparel", [])
        self.scenario_apparel_state.items = []
        if isinstance(apparel_items, list):
            for item in apparel_items:
                if isinstance(item, dict):
                    self.scenario_apparel_state.items.append(dict(item))
        self._refresh_apparel_listbox()
        self._clear_current_apparel_fields()

    def _build_scenario_payload_from_form(self) -> dict[str, object]:
        scenario_name = self._require_non_empty(self.scenario_name_var.get(), "场景名称不能为空。")
        attacker_name = self._require_non_empty(self.attacker_name_var.get(), "攻击方名称不能为空。")
        defender_name = self._require_non_empty(self.defender_name_var.get(), "防守方名称不能为空。")
        weapon_name = self._require_non_empty(self.weapon_name_var.get(), "武器名称不能为空。")

        payload: dict[str, object] = {
            "name": scenario_name,
            "attacker": {
                "name": attacker_name,
                "shooting_skill": self._parse_int(self.attacker_shooting_skill_var.get(), "攻击方射击技能"),
                "melee_skill": self._parse_int(self.attacker_melee_skill_var.get(), "攻击方近战技能"),
                "traits": self._split_csv_values(self.attacker_traits_var.get()) or [],
            },
            "defender": {
                "name": defender_name,
                "shooting_skill": self._parse_int(self.defender_shooting_skill_var.get(), "防守方射击技能"),
                "melee_skill": self._parse_int(self.defender_melee_skill_var.get(), "防守方近战技能"),
                "traits": self._split_csv_values(self.defender_traits_var.get()) or [],
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
                "target_body_region": self._require_non_empty(self.context_region_var.get(), "目标部位不能为空。"),
                "cover_block_chance": self._parse_float(self.context_cover_block_var.get(), "掩体挡住概率"),
                "hit_chance_multiplier": self._parse_float(self.context_hit_multiplier_var.get(), "命中倍率"),
                "target_is_aiming_or_firing": self.context_target_aiming_var.get(),
            },
        }
        return payload

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
            if selected_index is None:
                self.scenario_apparel_state.items.append(apparel_item)
                self._append_log(f"已新增护具: {apparel_name}")
            else:
                self.scenario_apparel_state.items[selected_index] = apparel_item
                self._append_log(f"已更新护具: {apparel_name}")
            self._refresh_apparel_listbox(select_index=selected_index if selected_index is not None else len(self.scenario_apparel_state.items) - 1)
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))

    def _remove_selected_apparel(self) -> None:
        selected_index = self._selected_apparel_index()
        if selected_index is None:
            messagebox.showinfo("未选择护具", "请先在护具列表里选中一件护具。")
            return
        removed = self.scenario_apparel_state.items.pop(selected_index)
        self._refresh_apparel_listbox()
        self._clear_current_apparel_fields()
        self._append_log(f"已删除护具: {removed.get('name', 'unnamed')}")

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
            listbox.insert("end", "暂无护具，点击下方新增/更新护具")
            return
        for item in self.scenario_apparel_state.items:
            layers = ",".join(self._ensure_string_list(item.get("layers", [])))
            covers = ",".join(self._ensure_string_list(item.get("covers", [])))
            listbox.insert("end", f"{item.get('name', 'unnamed')}  [{layers}]  ->  {covers}")
        if select_index is not None and 0 <= select_index < len(self.scenario_apparel_state.items):
            listbox.selection_set(select_index)
            listbox.see(select_index)

    def _on_apparel_selected(self, _event: object) -> None:
        selected_index = self._selected_apparel_index()
        if selected_index is None:
            return
        item = self.scenario_apparel_state.items[selected_index]
        self.apparel_name_var.set(str(item.get("name", "")))
        self.apparel_source_var.set(str(item.get("source", "manual")))
        self.apparel_layers_var.set(",".join(self._ensure_string_list(item.get("layers", []))))
        self.apparel_covers_var.set(",".join(self._ensure_string_list(item.get("covers", []))))
        self.apparel_armor_sharp_var.set(str(item.get("armor_sharp", 0)))
        self.apparel_armor_blunt_var.set(str(item.get("armor_blunt", 0)))
        self.apparel_armor_heat_var.set(str(item.get("armor_heat", 0)))

    def _selected_apparel_index(self) -> int | None:
        listbox = self.scenario_apparel_state.listbox
        if listbox is None:
            return None
        selection = listbox.curselection()
        if not selection:
            return None
        if not self.scenario_apparel_state.items:
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
                "开始生成原版武器 / 护具目录",
                run_vanilla_workflow,
                {
                    "game_data_root": game_data_root,
                    "output_dir": self.vanilla_output_var.get(),
                    "ranged_distance_cells": self._parse_int(self.vanilla_distance_var.get(), "远程分析距离"),
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
                "正在分析当前场景表单",
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
            self._run_background_workflow(
                "library",
                "开始批量分析场景库",
                run_library_workflow,
                {
                    "library_path": library_path,
                    "game_data_root": game_data_root,
                    "output_dir": self.library_output_var.get(),
                    "tags": self._split_csv_values(self.library_tags_var.get()),
                    "scenario_ids": self._split_csv_values(self.library_ids_var.get()),
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
                elif event_type == "error":
                    self._busy = False
                    message, tb = payload
                    self.status_var.set("任务失败")
                    self._append_log(tb)
                    messagebox.showerror("任务失败", message)
        except queue.Empty:
            pass
        self.after(120, self._poll_worker_events)

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
            widgets.outputs_listbox.insert("end", "本次任务没有生成输出文件")
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
        if not widgets.outputs:
            return
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

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
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


def main() -> int:
    app = RimDataAnalysisDesktopApp()
    app.mainloop()
    return 0


RimDataAnalysisDesktopApp = _NewRimDataAnalysisDesktopApp
main = _new_main
