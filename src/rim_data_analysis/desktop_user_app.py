from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

from rim_data_analysis.paths import discover_paths
from rim_data_analysis.user_app_data import (
    CatalogIndex,
    ComparisonRow,
    EquipmentChoice,
    FEATURE_BY_ID,
    FEATURE_OPTIONS,
    IMPLANT_BY_ID,
    IMPLANT_OPTIONS,
    MATERIAL_OPTIONS,
    QUALITY_OPTIONS,
    SPECIES_BY_ID,
    SPECIES_OPTIONS,
    SUPPORT_GEAR_BY_ID,
    SUPPORT_GEAR_OPTIONS,
    FeatureOption,
    ImportSettings,
    SavedPawnTemplate,
    SavedScenarioTemplate,
    SpeciesOption,
    UserAppStore,
    build_analysis_for_saved_scenario,
    build_firepower_preview_for_pawn,
    describe_modifier_payload,
    describe_equipment,
    humanlike_species_ids,
    load_catalog_index,
)


@dataclass(slots=True)
class CharacterOptionRecord:
    mode: str
    key: str
    title: str
    subtitle: str
    preview: str


def _join_preview_sections(*sections: tuple[str, list[str] | str | None]) -> str:
    blocks: list[str] = []
    for title, content in sections:
        if content is None:
            continue
        if isinstance(content, str):
            text = content.strip()
            if not text:
                continue
            blocks.append(f"{title}\n{text}")
            continue
        lines = [line for line in content if str(line).strip()]
        if not lines:
            continue
        blocks.append(f"{title}\n" + "\n".join(lines))
    return "\n\n".join(blocks)


class RimDataAnalysisDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Rim 数据分析")
        self._set_initial_window_size()

        self.repo_root = Path(__file__).resolve().parents[2]
        self.store = UserAppStore.for_repo(self.repo_root)
        self.discovered_paths = discover_paths()
        self.catalog_index: CatalogIndex | None = None
        self.import_settings = self.store.load_import_settings()
        self.saved_pawns: list[SavedPawnTemplate] = []
        self.saved_scenarios: list[SavedScenarioTemplate] = []
        self.current_character_id: str | None = None
        self.current_scenario_id: str | None = None
        self.character_option_records: list[CharacterOptionRecord] = []
        self.compare_rows: list[ComparisonRow] = []
        self.compare_sort_column = "scenario_name"
        self.compare_sort_reverse = False
        self.scenario_analysis_after_id: str | None = None

        self.colors = {
            "bg": "#efe6d4",
            "panel": "#fbf7ef",
            "panel_alt": "#e4d6bf",
            "hero": "#d9c1a2",
            "line": "#ccb28e",
            "ink": "#22201d",
            "muted": "#62584d",
            "accent": "#8a4d1f",
            "accent_dark": "#6a3711",
            "accent_soft": "#ecd7bf",
        }

        self._init_vars()
        self._configure_style()
        self._build_layout()
        self._load_startup_state()

    def _set_initial_window_size(self) -> None:
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        usable_width = max(920, screen_width - 64)
        usable_height = max(680, screen_height - 96)
        window_width = min(1560, int(screen_width * 0.9), usable_width)
        window_height = min(960, int(screen_height * 0.88), usable_height)

        min_width = min(window_width, max(980, min(1220, int(screen_width * 0.75))))
        min_height = min(window_height, max(680, min(820, int(screen_height * 0.72))))

        offset_x = max((screen_width - window_width) // 2, 20)
        offset_y = max((screen_height - window_height) // 2, 20)
        self.geometry(f"{window_width}x{window_height}+{offset_x}+{offset_y}")
        self.minsize(min_width, min_height)

    def _init_vars(self) -> None:
        self.status_var = tk.StringVar(value="应用已就绪。先到“数据导入”页导入原版数据，然后开始创建人物。")

        self.character_editor_title_var = tk.StringVar(value="新建人物")
        self.character_mode_title_var = tk.StringVar(value="选择基础模板")
        self.character_mode_hint_var = tk.StringVar(value="先为当前人物选择一个基础模板。")
        self.character_name_var = tk.StringVar()
        self.character_species_summary_var = tk.StringVar(value="未选择")
        self.character_shooting_skill_var = tk.StringVar(value="10")
        self.character_full_body_armor_var = tk.StringVar(value="0")
        self.character_search_var = tk.StringVar()
        self.character_search_cache = {
            "species": "",
            "features": "",
            "support_gear": "",
            "implants": "",
            "weapon": "",
            "apparel": "",
        }
        self.character_search_syncing = False
        self.character_quality_var = tk.StringVar(value=QUALITY_OPTIONS[2].label)
        self.character_material_var = tk.StringVar(value=MATERIAL_OPTIONS[1].label)
        self.character_weapon_summary_var = tk.StringVar(value="未选择武器")
        self.character_feature_status_var = tk.StringVar(value="未添加特性")
        self.character_support_gear_status_var = tk.StringVar(value="未添加特殊装备")
        self.character_implant_status_var = tk.StringVar(value="未添加植入体")
        self.character_apparel_status_var = tk.StringVar(value="未添加衣着")
        self.character_preview_title_var = tk.StringVar(value="暂无预览")
        self.character_preview_body_var = tk.StringVar(value="点击左侧分类后，在右侧选择内容。")
        self.character_import_preview_var = tk.StringVar(value="从下方已保存人物里选中一个模板后，这里会显示完整配置；可一键导入到编辑区继续微调。")
        self.character_power_status_var = tk.StringVar(value="选择基础模板和武器后，这里会显示实时输出能力。")
        self.character_power_metric_vars = {
            "distance": tk.StringVar(value="-"),
            "hit": tk.StringVar(value="-"),
            "warmup": tk.StringVar(value="-"),
            "cooldown": tk.StringVar(value="-"),
            "unarmored_dps": tk.StringVar(value="-"),
        }
        self.character_power_target_rows = [
            {
                "label": tk.StringVar(value=label),
                "dps": tk.StringVar(value="-"),
                "ratio": tk.StringVar(value="-"),
            }
            for label in (
                "0% 无甲参考",
                "20% 轻甲参考",
                "40% 中甲参考",
                "70% 重甲参考",
                "100% 极重甲参考",
            )
        ]

        self.scenario_editor_title_var = tk.StringVar(value="新建场景")
        self.scenario_name_var = tk.StringVar()
        self.scenario_name_hint_var = tk.StringVar(value="单组攻防可以自定义场景名；批量组合会自动命名为“攻击方 VS 防守方”。")
        self.scenario_distance_var = tk.StringVar(value="12")
        self.scenario_hit_chance_var = tk.StringVar(value="100")
        self.scenario_status_var = tk.StringVar(value="请选择双方人物模板。")
        self.scenario_attacker_status_var = tk.StringVar(value="未选择攻击方")
        self.scenario_defender_status_var = tk.StringVar(value="未选择防守方")
        self.scenario_picker_mode_var = tk.StringVar(value="当前添加到：攻击方")
        self.scenario_picker_preview_var = tk.StringVar(value="从下方已保存人物列表中选择一个人物，即可加入攻击方或防守方。")
        self.scenario_picker_search_var = tk.StringVar()
        self.scenario_metric_vars = {
            "weapon": tk.StringVar(value="-"),
            "hit": tk.StringVar(value="-"),
            "expected_dps": tk.StringVar(value="-"),
            "theoretical_dps": tk.StringVar(value="-"),
            "damage_on_hit": tk.StringVar(value="-"),
            "armor_reduction": tk.StringVar(value="-"),
            "taken_multiplier": tk.StringVar(value="-"),
            "distance": tk.StringVar(value="-"),
            "wearable": tk.StringVar(value="-"),
        }

        self.compare_status_var = tk.StringVar(value="从左侧选择一个或多个已保存场景，然后加入右侧对比表。")
        self.compare_filter_var = tk.StringVar()

        self.import_game_data_var = tk.StringVar()
        self.import_workshop_var = tk.StringVar()
        self.import_status_var = tk.StringVar(value="第一版仅支持原版游戏数据导入。")
        self.import_summary_vars = {
            "catalog": tk.StringVar(value="未导入"),
            "weapon_count": tk.StringVar(value="0"),
            "apparel_count": tk.StringVar(value="0"),
            "implant_count": tk.StringVar(value="0"),
            "import_time": tk.StringVar(value="-"),
        }

        self.resource_status_var = tk.StringVar(value="这里可以管理已经保存的人物和场景。")

        self.character_feature_ids: list[str] = []
        self.character_support_gear_ids: list[str] = []
        self.character_implant_ids: list[str] = []
        self.character_apparel_choices: list[EquipmentChoice] = []
        self.character_weapon_choice: EquipmentChoice | None = None
        self.character_species_id = ""
        self.character_mode = "species"
        self.scenario_attacker_ids: list[str] = []
        self.scenario_defender_ids: list[str] = []
        self.scenario_picker_mode = "attacker"
        self.last_scenario_details = "等待选择场景。"

    def _configure_style(self) -> None:
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
        style.configure("App.TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure(
            "App.TNotebook.Tab",
            padding=(22, 12),
            font=("Bahnschrift", 12, "bold"),
            background=self.colors["panel_alt"],
            foreground=self.colors["ink"],
            borderwidth=0,
        )
        style.map(
            "App.TNotebook.Tab",
            background=[("selected", self.colors["panel"]), ("active", self.colors["accent_soft"])],
            foreground=[("selected", self.colors["accent"])],
        )
        style.configure(
            "Primary.TButton",
            background=self.colors["accent"],
            foreground="#fff9f3",
            bordercolor=self.colors["accent"],
            padding=(14, 10),
            relief="flat",
        )
        style.map("Primary.TButton", background=[("active", self.colors["accent_dark"])])
        style.configure(
            "Subtle.TButton",
            background=self.colors["panel_alt"],
            foreground=self.colors["ink"],
            bordercolor=self.colors["line"],
            padding=(12, 8),
            relief="flat",
        )
        style.map("Subtle.TButton", background=[("active", "#dcc9ab")])
        style.configure(
            "App.TCombobox",
            fieldbackground="#fffdf8",
            background="#fffdf8",
            bordercolor=self.colors["line"],
            arrowcolor=self.colors["accent"],
            padding=6,
        )
        style.configure(
            "Compare.Treeview",
            background="#fffdf8",
            fieldbackground="#fffdf8",
            foreground=self.colors["ink"],
            bordercolor=self.colors["line"],
            rowheight=30,
        )
        style.configure(
            "Compare.Treeview.Heading",
            background=self.colors["panel_alt"],
            foreground=self.colors["ink"],
            font=("Bahnschrift", 10, "bold"),
            relief="flat",
        )

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        shell = tk.Frame(self, bg=self.colors["bg"], padx=18, pady=18)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(shell, style="App.TNotebook")
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.characters_page = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.scenario_page = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.compare_page = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.import_page = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.resources_page = tk.Frame(self.notebook, bg=self.colors["bg"])

        self.notebook.add(self.characters_page, text="人物创建")
        self.notebook.add(self.scenario_page, text="场景设计")
        self.notebook.add(self.compare_page, text="结果对比")
        self.notebook.add(self.import_page, text="数据导入")
        self.notebook.add(self.resources_page, text="资源管理")

        self._build_characters_page()
        self._build_scenario_page()
        self._build_compare_page()
        self._build_import_page()
        self._build_resources_page()

    def _panel(self, parent: tk.Widget, *, width: int | None = None, padx: int = 0, pady: int = 0) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=self.colors["panel"],
            padx=padx,
            pady=pady,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            width=width,
        )

    def _scrollable_sidebar(
        self,
        parent: tk.Widget,
        *,
        width: int,
        padx: int = 0,
        pady: int = 0,
    ) -> tuple[tk.Frame, tk.Frame]:
        shell = tk.Frame(
            parent,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            width=width,
        )
        shell.grid_propagate(False)

        canvas = tk.Canvas(shell, bg=self.colors["panel"], bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(canvas, bg=self.colors["panel"], padx=padx, pady=pady)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def sync_scrollregion(_event: object) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_width(event: object) -> None:
            width_value = getattr(event, "width", 1)
            canvas.itemconfigure(window_id, width=max(width_value, 1))

        content.bind("<Configure>", sync_scrollregion)
        canvas.bind("<Configure>", sync_width)

        def bind_mousewheel(_event: object) -> None:
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(_event: object) -> None:
            canvas.unbind_all("<MouseWheel>")

        def on_mousewheel(event: object) -> None:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return
            canvas.yview_scroll(int(-delta / 120), "units")

        for widget in (shell, canvas, content):
            widget.bind("<Enter>", bind_mousewheel)
            widget.bind("<Leave>", unbind_mousewheel)

        return shell, content

    def _simple_listbox(
        self,
        parent: tk.Widget,
        *,
        height: int,
        selectmode: str = tk.BROWSE,
    ) -> tk.Listbox:
        return tk.Listbox(
            parent,
            height=height,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
            selectbackground=self.colors["accent"],
            selectforeground="#fff9f3",
            activestyle="none",
            exportselection=False,
            selectmode=selectmode,
        )

    def _bind_toggle_multiselect(
        self,
        listbox: tk.Listbox,
        *,
        select_callback: object | None = None,
        double_click_callback: object | None = None,
    ) -> None:
        listbox.bind(
            "<Button-1>",
            lambda event, lb=listbox, cb=select_callback: self._toggle_multiselect_click(event, lb, cb),
        )
        if double_click_callback is not None:
            listbox.bind(
                "<Double-Button-1>",
                lambda event, lb=listbox, cb=select_callback, dc=double_click_callback: self._toggle_multiselect_double_click(event, lb, cb, dc),
            )

    def _toggle_multiselect_click(
        self,
        event: object,
        listbox: tk.Listbox,
        select_callback: object | None,
    ) -> str:
        index = listbox.nearest(getattr(event, "y", 0))
        if index < 0 or index >= listbox.size():
            return "break"
        selected = set(self._selected_indices(listbox))
        if index in selected:
            listbox.selection_clear(index)
        else:
            listbox.selection_set(index)
        listbox.activate(index)
        listbox.see(index)
        listbox.focus_set()
        if callable(select_callback):
            select_callback(None)
        return "break"

    def _toggle_multiselect_double_click(
        self,
        event: object,
        listbox: tk.Listbox,
        select_callback: object | None,
        double_click_callback: object,
    ) -> str:
        index = listbox.nearest(getattr(event, "y", 0))
        if index < 0 or index >= listbox.size():
            return "break"
        if index not in self._selected_indices(listbox):
            listbox.selection_set(index)
        listbox.activate(index)
        listbox.see(index)
        listbox.focus_set()
        if callable(select_callback):
            select_callback(None)
        if callable(double_click_callback):
            double_click_callback(index)
        return "break"

    def _labeled_entry(self, parent: tk.Widget, label: str, variable: tk.StringVar) -> None:
        tk.Label(parent, text=label, bg=self.colors["panel"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 4))
        entry = tk.Entry(
            parent,
            textvariable=variable,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
        )
        entry.pack(fill="x", pady=(0, 12))

    def _labeled_combo(self, parent: tk.Widget, label: str, variable: tk.StringVar, *, attr_name: str) -> None:
        tk.Label(parent, text=label, bg=self.colors["panel"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 4))
        combo = ttk.Combobox(parent, textvariable=variable, state="readonly", style="App.TCombobox")
        combo.pack(fill="x", pady=(0, 12))
        setattr(self, attr_name, combo)

    def _sidebar_button(
        self,
        parent: tk.Widget,
        *,
        title: str,
        summary_var: tk.StringVar,
        command: object,
    ) -> None:
        ttk.Button(parent, text=title, style="Subtle.TButton", command=command).pack(fill="x", pady=(0, 4))
        tk.Label(
            parent,
            textvariable=summary_var,
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            justify="left",
            wraplength=300,
        ).pack(anchor="w", pady=(0, 12))

    def _metric_card(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        title: str,
        variable: tk.StringVar,
        *,
        width: int | None = None,
    ) -> None:
        card = tk.Frame(
            parent,
            bg=self.colors["accent_soft"],
            padx=14,
            pady=14,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            width=width,
        )
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        if width is not None:
            card.grid_propagate(False)
        tk.Label(
            card,
            text=title,
            bg=self.colors["accent_soft"],
            fg=self.colors["muted"],
            font=("Bahnschrift", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card,
            textvariable=variable,
            bg=self.colors["accent_soft"],
            fg=self.colors["accent"],
            font=("Bahnschrift", 17, "bold"),
            wraplength=220,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    def _compact_metric_card(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        title: str,
        variable: tk.StringVar,
        *,
        width: int = 100,
    ) -> None:
        card = tk.Frame(
            parent,
            bg=self.colors["accent_soft"],
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            width=width,
        )
        card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
        card.grid_propagate(False)
        tk.Label(
            card,
            text=title,
            bg=self.colors["accent_soft"],
            fg=self.colors["muted"],
            font=("Bahnschrift", 9, "bold"),
            wraplength=width - 20,
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            card,
            textvariable=variable,
            bg=self.colors["accent_soft"],
            fg=self.colors["accent"],
            font=("Bahnschrift", 12, "bold"),
            wraplength=width - 20,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

    def _path_picker(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        browse_command: object,
    ) -> None:
        tk.Label(parent, text=label, bg=self.colors["panel"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 4))
        row = tk.Frame(parent, bg=self.colors["panel"])
        row.pack(fill="x", pady=(0, 12))
        entry = tk.Entry(
            row,
            textvariable=variable,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
        )
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="浏览", style="Subtle.TButton", command=browse_command).pack(side="left", padx=(8, 0))

    def _build_characters_page(self) -> None:
        page = self.characters_page
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)

        sidebar_shell, sidebar = self._scrollable_sidebar(page, width=350, padx=18, pady=18)
        sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=4)

        main = self._panel(page, padx=18, pady=18)
        main.grid(row=0, column=1, sticky="nsew", pady=4)
        main.grid_rowconfigure(3, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_columnconfigure(2, weight=0)

        tk.Label(sidebar, textvariable=self.character_editor_title_var, bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="左侧整理人物配置，中间选内容，右侧实时查看当前火力表现。", bg=self.colors["panel"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10), wraplength=300, justify="left").pack(anchor="w", pady=(4, 14))

        self._labeled_entry(sidebar, "小人模板名称", self.character_name_var)
        self._sidebar_button(sidebar, title="基础模板", summary_var=self.character_species_summary_var, command=lambda: self._set_character_mode("species"))
        self._sidebar_button(sidebar, title="特性", summary_var=self.character_feature_status_var, command=lambda: self._set_character_mode("features"))
        self.character_feature_listbox = self._simple_listbox(sidebar, height=6, selectmode=tk.MULTIPLE)
        self.character_feature_listbox.pack(fill="x", pady=(6, 0))
        self._bind_toggle_multiselect(self.character_feature_listbox)
        ttk.Button(sidebar, text="删除选中特性", style="Subtle.TButton", command=self._remove_selected_feature).pack(fill="x", pady=(6, 12))
        self._sidebar_button(sidebar, title="特殊装备", summary_var=self.character_support_gear_status_var, command=lambda: self._set_character_mode("support_gear"))
        self.character_support_gear_listbox = self._simple_listbox(sidebar, height=4, selectmode=tk.MULTIPLE)
        self.character_support_gear_listbox.pack(fill="x", pady=(6, 0))
        self._bind_toggle_multiselect(self.character_support_gear_listbox)
        ttk.Button(sidebar, text="删除选中特殊装备", style="Subtle.TButton", command=self._remove_selected_support_gear).pack(fill="x", pady=(6, 12))
        self._sidebar_button(sidebar, title="植入体", summary_var=self.character_implant_status_var, command=lambda: self._set_character_mode("implants"))
        self.character_implant_listbox = self._simple_listbox(sidebar, height=4, selectmode=tk.MULTIPLE)
        self.character_implant_listbox.pack(fill="x", pady=(6, 0))
        self._bind_toggle_multiselect(self.character_implant_listbox)
        ttk.Button(sidebar, text="删除选中植入体", style="Subtle.TButton", command=self._remove_selected_implant).pack(fill="x", pady=(6, 12))
        self._labeled_entry(sidebar, "射击等级", self.character_shooting_skill_var)
        self._labeled_entry(sidebar, "全身护甲%", self.character_full_body_armor_var)
        self._sidebar_button(sidebar, title="武器选择", summary_var=self.character_weapon_summary_var, command=lambda: self._set_character_mode("weapon"))
        self._sidebar_button(sidebar, title="衣着选择", summary_var=self.character_apparel_status_var, command=lambda: self._set_character_mode("apparel"))
        self.character_apparel_listbox = self._simple_listbox(sidebar, height=8, selectmode=tk.MULTIPLE)
        self.character_apparel_listbox.pack(fill="x", pady=(6, 0))
        self._bind_toggle_multiselect(self.character_apparel_listbox)
        ttk.Button(sidebar, text="删除选中衣着", style="Subtle.TButton", command=self._remove_selected_apparel).pack(fill="x", pady=(6, 18))

        button_row = tk.Frame(sidebar, bg=self.colors["panel"])
        button_row.pack(fill="x", pady=(4, 0))
        ttk.Button(button_row, text="保存为新人物", style="Primary.TButton", command=self._save_character).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(button_row, text="新建空白人物", style="Subtle.TButton", command=self._reset_character_editor).pack(side="left", fill="x", expand=True)

        header = tk.Frame(main, bg=self.colors["panel"])
        header.grid(row=0, column=0, columnspan=3, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, textvariable=self.character_mode_title_var, bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, textvariable=self.character_mode_hint_var, bg=self.colors["panel"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 0))

        search_bar = tk.Frame(main, bg=self.colors["panel"])
        search_bar.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(14, 12))
        search_bar.grid_columnconfigure(1, weight=1)
        tk.Label(search_bar, text="搜索", bg=self.colors["panel"], fg=self.colors["muted"]).grid(row=0, column=0, sticky="w", padx=(0, 10))
        search_entry = tk.Entry(search_bar, textvariable=self.character_search_var, bg="#fffdf8", fg=self.colors["ink"], relief="solid", borderwidth=1, highlightthickness=1, highlightbackground=self.colors["line"], highlightcolor=self.colors["accent"])
        search_entry.grid(row=0, column=1, sticky="ew")
        self.character_search_var.trace_add("write", lambda *_args: self._on_character_search_changed())

        self.character_equipment_frame = tk.Frame(main, bg=self.colors["panel"])
        self.character_equipment_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        tk.Label(self.character_equipment_frame, text="品质", bg=self.colors["panel"], fg=self.colors["muted"]).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.character_quality_combo = ttk.Combobox(self.character_equipment_frame, textvariable=self.character_quality_var, state="readonly", style="App.TCombobox", values=[item.label for item in QUALITY_OPTIONS], width=12)
        self.character_quality_combo.grid(row=0, column=1, sticky="w", padx=(0, 14))
        self.character_material_label = tk.Label(self.character_equipment_frame, text="材质", bg=self.colors["panel"], fg=self.colors["muted"])
        self.character_material_label.grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.character_material_combo = ttk.Combobox(self.character_equipment_frame, textvariable=self.character_material_var, state="readonly", style="App.TCombobox", values=[item.label for item in MATERIAL_OPTIONS], width=12)
        self.character_material_combo.grid(row=0, column=3, sticky="w")
        self.character_shooting_skill_var.trace_add("write", lambda *_args: self._refresh_character_firepower_preview())
        self.character_full_body_armor_var.trace_add("write", lambda *_args: self._on_character_defense_controls_changed())
        self.character_quality_var.trace_add("write", lambda *_args: self._on_character_equipment_controls_changed())
        self.character_material_var.trace_add("write", lambda *_args: self._on_character_equipment_controls_changed())

        chooser_shell = tk.Frame(main, bg=self.colors["panel"])
        chooser_shell.grid(row=3, column=0, sticky="nsew")
        chooser_shell.grid_rowconfigure(0, weight=1)
        chooser_shell.grid_columnconfigure(0, weight=1)
        self.character_option_listbox = self._simple_listbox(chooser_shell, height=18, selectmode=tk.MULTIPLE)
        self.character_option_listbox.grid(row=0, column=0, sticky="nsew")
        self.character_option_listbox.bind("<<ListboxSelect>>", self._on_character_option_selected)
        self._bind_toggle_multiselect(
            self.character_option_listbox,
            select_callback=self._on_character_option_selected,
            double_click_callback=self._apply_character_option_from_index,
        )

        action_area = tk.Frame(main, bg=self.colors["panel"], width=290)
        action_area.grid(row=3, column=1, sticky="ns", padx=(14, 0))
        action_area.grid_propagate(False)

        preview = tk.Frame(action_area, bg=self.colors["panel_alt"], padx=14, pady=14, highlightthickness=1, highlightbackground=self.colors["line"])
        preview.pack(fill="x")
        tk.Label(preview, textvariable=self.character_preview_title_var, bg=self.colors["panel_alt"], fg=self.colors["accent"], font=("Bahnschrift", 14, "bold"), justify="left", wraplength=250).pack(anchor="w")
        tk.Label(preview, textvariable=self.character_preview_body_var, bg=self.colors["panel_alt"], fg=self.colors["ink"], font=("Microsoft YaHei UI", 10), justify="left", wraplength=250).pack(anchor="w", pady=(8, 0))
        self.character_apply_button = ttk.Button(action_area, text="应用当前选择", style="Primary.TButton", command=self._apply_character_option)
        self.character_apply_button.pack(fill="x", pady=(12, 10))

        saved_panel = self._panel(action_area, padx=12, pady=12)
        saved_panel.pack(fill="both", expand=True)
        tk.Label(saved_panel, text="导入已有小人作为基础", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 14, "bold")).pack(anchor="w")
        tk.Label(saved_panel, text="选中一个已保存人物后，可把它的基础模板、特性、射击等级、武器和衣着完整导入到当前编辑区，再保存为另一个新小人。", bg=self.colors["panel"], fg=self.colors["muted"], justify="left", wraplength=240, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(4, 8))
        self.character_saved_listbox = self._simple_listbox(saved_panel, height=10)
        self.character_saved_listbox.pack(fill="both", expand=True, pady=(8, 0))
        self.character_saved_listbox.bind("<<ListboxSelect>>", lambda _event: self._update_character_import_preview())
        self.character_saved_listbox.bind("<Double-Button-1>", lambda _event: self._load_selected_character_from_character_page())
        self.character_saved_preview = tk.Label(saved_panel, textvariable=self.character_import_preview_var, bg=self.colors["panel_alt"], fg=self.colors["ink"], justify="left", anchor="nw", wraplength=240, padx=10, pady=10)
        self.character_saved_preview.pack(fill="x", pady=(10, 0))
        buttons = tk.Frame(saved_panel, bg=self.colors["panel"])
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="导入选中人物", style="Subtle.TButton", command=self._load_selected_character_from_character_page).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(buttons, text="切到资源管理", style="Subtle.TButton", command=lambda: self.notebook.select(self.resources_page)).pack(side="left", fill="x", expand=True)

        firepower_shell, firepower_panel = self._scrollable_sidebar(main, width=380, padx=14, pady=14)
        firepower_shell.grid(row=3, column=2, sticky="nsew", padx=(14, 0))
        tk.Label(firepower_panel, text="实时输出能力", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 16, "bold")).pack(anchor="w")
        tk.Label(firepower_panel, text="以下数据按当前人物配置实时刷新，命中率与 DPS 统一按最佳距离档计算；时间按“实战/基础”显示。", bg=self.colors["panel"], fg=self.colors["muted"], justify="left", wraplength=330, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(4, 10))
        tk.Label(firepower_panel, textvariable=self.character_power_status_var, bg=self.colors["panel"], fg=self.colors["accent"], justify="left", wraplength=320, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(0, 12))

        summary_grid = tk.Frame(firepower_panel, bg=self.colors["panel"])
        summary_grid.pack(fill="x")
        summary_grid.grid_columnconfigure(0, weight=1)
        summary_grid.grid_columnconfigure(1, weight=1)
        summary_grid.grid_columnconfigure(2, weight=1)
        self._compact_metric_card(summary_grid, 0, 0, "最佳距离", self.character_power_metric_vars["distance"], width=104)
        self._compact_metric_card(summary_grid, 0, 1, "最终命中率", self.character_power_metric_vars["hit"], width=104)
        self._compact_metric_card(summary_grid, 0, 2, "0%护甲DPS", self.character_power_metric_vars["unarmored_dps"], width=104)
        self._compact_metric_card(summary_grid, 1, 0, "瞄准时间", self.character_power_metric_vars["warmup"], width=104)
        self._compact_metric_card(summary_grid, 1, 1, "冷却时间", self.character_power_metric_vars["cooldown"], width=104)

        target_panel = tk.Frame(firepower_panel, bg=self.colors["panel_alt"], padx=12, pady=12, highlightthickness=1, highlightbackground=self.colors["line"])
        target_panel.pack(fill="both", expand=True, pady=(12, 0))
        target_panel.grid_columnconfigure(0, weight=1)
        target_panel.grid_columnconfigure(1, weight=0)
        target_panel.grid_columnconfigure(2, weight=0)
        tk.Label(target_panel, text="参考目标", bg=self.colors["panel_alt"], fg=self.colors["ink"], font=("Bahnschrift", 13, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(target_panel, text="期望DPS", bg=self.colors["panel_alt"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10)).grid(row=0, column=1, sticky="e", padx=(8, 12))
        tk.Label(target_panel, text="对无甲比值", bg=self.colors["panel_alt"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10)).grid(row=0, column=2, sticky="e")
        for index, row_vars in enumerate(self.character_power_target_rows, start=1):
            tk.Label(target_panel, textvariable=row_vars["label"], bg=self.colors["panel_alt"], fg=self.colors["ink"], font=("Microsoft YaHei UI", 10)).grid(row=index, column=0, sticky="w", pady=(10, 0))
            tk.Label(target_panel, textvariable=row_vars["dps"], bg=self.colors["panel_alt"], fg=self.colors["accent"], font=("Bahnschrift", 11, "bold")).grid(row=index, column=1, sticky="e", padx=(8, 12), pady=(10, 0))
            tk.Label(target_panel, textvariable=row_vars["ratio"], bg=self.colors["panel_alt"], fg=self.colors["ink"], font=("Bahnschrift", 11, "bold")).grid(row=index, column=2, sticky="e", pady=(10, 0))

    def _build_scenario_page(self) -> None:
        page = self.scenario_page
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)

        sidebar_shell, sidebar = self._scrollable_sidebar(page, width=360, padx=18, pady=18)
        sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=4)

        main = self._panel(page, padx=18, pady=18)
        main.grid(row=0, column=1, sticky="nsew", pady=4)
        main.grid_rowconfigure(2, weight=1)
        main.grid_rowconfigure(4, weight=1)
        main.grid_columnconfigure(0, weight=1)

        tk.Label(sidebar, textvariable=self.scenario_editor_title_var, bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="现在支持一次选择多名攻击方和防守方，并按两两配对自动生成场景。", bg=self.colors["panel"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10), wraplength=300, justify="left").pack(anchor="w", pady=(4, 14))
        tk.Label(sidebar, text="场景名称", bg=self.colors["panel"], fg=self.colors["muted"]).pack(anchor="w", pady=(0, 4))
        self.scenario_name_entry = tk.Entry(
            sidebar,
            textvariable=self.scenario_name_var,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
        )
        self.scenario_name_entry.pack(fill="x", pady=(0, 4))
        tk.Label(sidebar, textvariable=self.scenario_name_hint_var, bg=self.colors["panel"], fg=self.colors["muted"], justify="left", wraplength=300, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(0, 12))
        self._sidebar_button(sidebar, title="攻击方人物", summary_var=self.scenario_attacker_status_var, command=lambda: self._set_scenario_picker_mode("attacker"))
        self.scenario_attacker_listbox = self._simple_listbox(sidebar, height=5)
        self.scenario_attacker_listbox.pack(fill="x", pady=(6, 0))
        ttk.Button(sidebar, text="删除选中攻击方", style="Subtle.TButton", command=self._remove_selected_scenario_attacker).pack(fill="x", pady=(6, 12))
        self._sidebar_button(sidebar, title="防守方人物", summary_var=self.scenario_defender_status_var, command=lambda: self._set_scenario_picker_mode("defender"))
        self.scenario_defender_listbox = self._simple_listbox(sidebar, height=5)
        self.scenario_defender_listbox.pack(fill="x", pady=(6, 0))
        ttk.Button(sidebar, text="删除选中防守方", style="Subtle.TButton", command=self._remove_selected_scenario_defender).pack(fill="x", pady=(6, 12))
        self._labeled_entry(sidebar, "双方距离", self.scenario_distance_var)
        self._labeled_entry(sidebar, "最终命中率%", self.scenario_hit_chance_var)
        tk.Label(sidebar, textvariable=self.scenario_status_var, bg=self.colors["panel"], fg=self.colors["accent"], font=("Microsoft YaHei UI", 10), justify="left", wraplength=300).pack(anchor="w", pady=(8, 14))

        action_row = tk.Frame(sidebar, bg=self.colors["panel"])
        action_row.pack(fill="x")
        ttk.Button(action_row, text="保存场景", style="Primary.TButton", command=self._save_scenario).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(action_row, text="新建空白场景", style="Subtle.TButton", command=self._reset_scenario_editor).pack(side="left", fill="x", expand=True)

        tk.Label(sidebar, text="已保存场景", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 14, "bold")).pack(anchor="w", pady=(18, 8))
        self.scenario_saved_listbox = self._simple_listbox(sidebar, height=16)
        self.scenario_saved_listbox.pack(fill="both", expand=True)
        load_buttons = tk.Frame(sidebar, bg=self.colors["panel"])
        load_buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(load_buttons, text="载入选中场景", style="Subtle.TButton", command=self._load_selected_scenario_from_scenario_page).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(load_buttons, text="加入对比页", style="Subtle.TButton", command=lambda: self.notebook.select(self.compare_page)).pack(side="left", fill="x", expand=True)

        tk.Label(main, text="选择人物", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(main, text="先在下方列表选择人物，再加入攻击方或防守方。单组攻防会实时预览，批量组合会自动生成多条场景。", bg=self.colors["panel"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10), wraplength=920, justify="left").grid(row=1, column=0, sticky="w", pady=(4, 14))

        picker_shell = tk.Frame(main, bg=self.colors["panel"])
        picker_shell.grid(row=2, column=0, sticky="nsew")
        picker_shell.grid_rowconfigure(1, weight=1)
        picker_shell.grid_columnconfigure(0, weight=1)
        picker_shell.grid_columnconfigure(1, weight=0)

        picker_header = tk.Frame(picker_shell, bg=self.colors["panel"])
        picker_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        picker_header.grid_columnconfigure(1, weight=1)
        tk.Label(picker_header, textvariable=self.scenario_picker_mode_var, bg=self.colors["panel"], fg=self.colors["accent"], font=("Bahnschrift", 12, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 14))
        tk.Label(picker_header, text="搜索人物", bg=self.colors["panel"], fg=self.colors["muted"]).grid(row=0, column=1, sticky="w", padx=(0, 8))
        search_entry = tk.Entry(
            picker_header,
            textvariable=self.scenario_picker_search_var,
            bg="#fffdf8",
            fg=self.colors["ink"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["accent"],
        )
        search_entry.grid(row=0, column=2, sticky="ew")

        self.scenario_picker_listbox = self._simple_listbox(picker_shell, height=12)
        self.scenario_picker_listbox.grid(row=1, column=0, sticky="nsew")
        self.scenario_picker_listbox.bind("<<ListboxSelect>>", self._update_scenario_picker_preview)
        self.scenario_picker_listbox.bind("<Double-Button-1>", lambda _event: self._add_selected_pawn_to_scenario())

        picker_side = tk.Frame(picker_shell, bg=self.colors["panel"], width=320)
        picker_side.grid(row=1, column=1, sticky="ns", padx=(14, 0))
        picker_side.grid_propagate(False)
        preview = tk.Frame(picker_side, bg=self.colors["panel_alt"], padx=14, pady=14, highlightthickness=1, highlightbackground=self.colors["line"])
        preview.pack(fill="both", expand=True)
        tk.Label(preview, text="人物预览", bg=self.colors["panel_alt"], fg=self.colors["accent"], font=("Bahnschrift", 14, "bold")).pack(anchor="w")
        tk.Label(preview, textvariable=self.scenario_picker_preview_var, bg=self.colors["panel_alt"], fg=self.colors["ink"], justify="left", wraplength=260, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(8, 0))
        self.scenario_picker_apply_button = ttk.Button(picker_side, text="加入攻击方", style="Primary.TButton", command=self._add_selected_pawn_to_scenario)
        self.scenario_picker_apply_button.pack(fill="x", pady=(12, 0))

        cards = tk.Frame(main, bg=self.colors["panel"])
        cards.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        for idx in range(3):
            cards.grid_columnconfigure(idx, weight=1)
        metrics = [("当前武器", "weapon"), ("最终命中率", "hit"), ("期望 DPS", "expected_dps"), ("理论 DPS", "theoretical_dps"), ("每次命中期望伤害", "damage_on_hit"), ("护甲减伤率", "armor_reduction"), ("承伤倍率", "taken_multiplier"), ("距离", "distance"), ("穿戴是否合法", "wearable")]
        for index, (label, key) in enumerate(metrics):
            row = index // 3
            column = index % 3
            self._metric_card(cards, row, column, label, self.scenario_metric_vars[key])

        details_panel = self._panel(main, padx=14, pady=14)
        details_panel.grid(row=4, column=0, sticky="nsew", pady=(14, 0))
        details_panel.grid_rowconfigure(1, weight=1)
        details_panel.grid_columnconfigure(0, weight=1)
        tk.Label(details_panel, text="计算说明", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 14, "bold")).grid(row=0, column=0, sticky="w")
        self.scenario_details_text = tk.Text(details_panel, bg="#fffdf8", fg=self.colors["ink"], relief="solid", borderwidth=1, wrap="word", height=10)
        self.scenario_details_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.scenario_details_text.insert("1.0", self.last_scenario_details)
        self.scenario_details_text.configure(state="disabled")

        self.scenario_name_var.trace_add("write", lambda *_args: self._schedule_scenario_analysis())
        self.scenario_distance_var.trace_add("write", lambda *_args: self._schedule_scenario_analysis())
        self.scenario_hit_chance_var.trace_add("write", lambda *_args: self._schedule_scenario_analysis())
        self.scenario_picker_search_var.trace_add("write", lambda *_args: self._refresh_scenario_picker_list())

    def _build_compare_page(self) -> None:
        page = self.compare_page
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)

        sidebar_shell, sidebar = self._scrollable_sidebar(page, width=330, padx=18, pady=18)
        sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=4)

        main = self._panel(page, padx=18, pady=18)
        main.grid(row=0, column=1, sticky="nsew", pady=4)
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)

        tk.Label(sidebar, text="场景导入", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).pack(anchor="w")
        tk.Label(sidebar, textvariable=self.compare_status_var, bg=self.colors["panel"], fg=self.colors["muted"], justify="left", wraplength=280, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 12))
        self._labeled_entry(sidebar, "筛选场景", self.compare_filter_var)
        self.compare_filter_var.trace_add("write", lambda *_args: self._refresh_compare_source_list())
        self.compare_source_listbox = self._simple_listbox(sidebar, height=20, selectmode=tk.MULTIPLE)
        self.compare_source_listbox.pack(fill="both", expand=True, pady=(8, 0))
        self._bind_toggle_multiselect(
            self.compare_source_listbox,
            double_click_callback=self._analyze_compare_scenario_at_index,
        )

        action_column = tk.Frame(sidebar, bg=self.colors["panel"])
        action_column.pack(fill="x", pady=(10, 0))
        ttk.Button(action_column, text="加入选中场景", style="Primary.TButton", command=self._analyze_selected_compare_scenarios).pack(fill="x", pady=(0, 6))
        ttk.Button(action_column, text="分析全部场景", style="Subtle.TButton", command=self._analyze_all_compare_scenarios).pack(fill="x", pady=(0, 6))
        ttk.Button(action_column, text="清空对比表", style="Subtle.TButton", command=self._clear_compare_rows).pack(fill="x", pady=(0, 6))
        ttk.Button(action_column, text="保存本次结果", style="Subtle.TButton", command=self._save_compare_rows).pack(fill="x")

        tk.Label(main, text="结果对比表", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(main, text="点击表头即可按该列升序或降序排序。", bg=self.colors["panel"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 14))

        table_shell = tk.Frame(main, bg=self.colors["panel"])
        table_shell.grid(row=2, column=0, sticky="nsew")
        table_shell.grid_rowconfigure(0, weight=1)
        table_shell.grid_columnconfigure(0, weight=1)
        columns = [("scenario_name", "场景名称", 180), ("expected_dps", "期望DPS", 100), ("hit_chance_percent", "命中率%", 90), ("expected_damage_on_hit", "命中期望伤害", 120), ("armor_reduction_percent", "护甲减伤%", 100), ("damage_taken_multiplier", "承伤倍率", 90), ("theoretical_dps", "理论DPS", 100), ("distance_cells", "距离", 70), ("attacker_name", "攻击方", 120), ("defender_name", "防守方", 120), ("weapon_name", "武器", 180), ("outfit_valid", "穿戴合法", 90)]
        self.compare_columns = columns
        self.compare_tree = ttk.Treeview(table_shell, columns=[column[0] for column in columns], show="headings", style="Compare.Treeview")
        self.compare_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(table_shell, orient="vertical", command=self.compare_tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(table_shell, orient="horizontal", command=self.compare_tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.compare_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        for key, label, width in columns:
            self.compare_tree.heading(key, text=label, command=lambda c=key: self._sort_compare_rows(c))
            self.compare_tree.column(key, width=width, anchor="center", stretch=False)

    def _build_import_page(self) -> None:
        page = self.import_page
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)

        sidebar_shell, sidebar = self._scrollable_sidebar(page, width=380, padx=18, pady=18)
        sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=4)

        main = self._panel(page, padx=18, pady=18)
        main.grid(row=0, column=1, sticky="nsew", pady=4)
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        tk.Label(sidebar, text="数据导入", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="只需要告诉应用你的游戏本体位置。第一版先按原版数据工作。", bg=self.colors["panel"], fg=self.colors["muted"], justify="left", wraplength=320, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(4, 14))
        self._path_picker(sidebar, "游戏 Data 目录", self.import_game_data_var, self._browse_game_data_root)
        self._path_picker(sidebar, "Steam 创意工坊目录", self.import_workshop_var, self._browse_workshop_root)

        note = tk.Frame(sidebar, bg=self.colors["panel_alt"], padx=12, pady=12, highlightthickness=1, highlightbackground=self.colors["line"])
        note.pack(fill="x", pady=(8, 14))
        tk.Label(note, text="当前版本说明", bg=self.colors["panel_alt"], fg=self.colors["accent"], font=("Bahnschrift", 12, "bold")).pack(anchor="w")
        tk.Label(note, text="创意工坊路径先保留，但暂时不会参与分析。完成导入后，人物页的武器、衣着和可识别植入体搜索列表会自动更新。", bg=self.colors["panel_alt"], fg=self.colors["ink"], justify="left", wraplength=300, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 0))

        button_row = tk.Frame(sidebar, bg=self.colors["panel"])
        button_row.pack(fill="x")
        ttk.Button(button_row, text="自动检测路径", style="Subtle.TButton", command=self._auto_detect_paths).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(button_row, text="导入原版数据", style="Primary.TButton", command=self._import_catalog).pack(side="left", fill="x", expand=True)
        tk.Label(sidebar, textvariable=self.import_status_var, bg=self.colors["panel"], fg=self.colors["accent"], justify="left", wraplength=320, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(14, 0))

        summary = tk.Frame(main, bg=self.colors["panel"])
        summary.grid(row=0, column=0, columnspan=2, sticky="ew")
        for idx in range(5):
            summary.grid_columnconfigure(idx, weight=1)
        summary_cards = [
            ("当前目录", self.import_summary_vars["catalog"]),
            ("武器数量", self.import_summary_vars["weapon_count"]),
            ("衣着数量", self.import_summary_vars["apparel_count"]),
            ("植入体数量", self.import_summary_vars["implant_count"]),
            ("导入时间", self.import_summary_vars["import_time"]),
        ]
        for idx, (label, var) in enumerate(summary_cards):
            self._metric_card(summary, 0, idx, label, var, width=220)

        tk.Label(main, text="武器预览", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 16, "bold")).grid(row=1, column=0, sticky="w", pady=(16, 8))
        tk.Label(main, text="衣着预览", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 16, "bold")).grid(row=1, column=1, sticky="w", pady=(16, 8))
        self.import_weapon_preview = self._simple_listbox(main, height=20)
        self.import_weapon_preview.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        self.import_apparel_preview = self._simple_listbox(main, height=20)
        self.import_apparel_preview.grid(row=2, column=1, sticky="nsew", padx=(8, 0))

    def _build_resources_page(self) -> None:
        page = self.resources_page
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)

        pawns_panel = self._panel(page, padx=18, pady=18)
        pawns_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=4)
        pawns_panel.grid_rowconfigure(2, weight=1)
        pawns_panel.grid_columnconfigure(0, weight=1)

        scenarios_panel = self._panel(page, padx=18, pady=18)
        scenarios_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=4)
        scenarios_panel.grid_rowconfigure(2, weight=1)
        scenarios_panel.grid_columnconfigure(0, weight=1)

        tk.Label(pawns_panel, text="已保存人物", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(pawns_panel, text="支持载入编辑和删除预设。", bg=self.colors["panel"], fg=self.colors["muted"], font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.resource_pawns_listbox = self._simple_listbox(pawns_panel, height=18, selectmode=tk.MULTIPLE)
        self.resource_pawns_listbox.grid(row=2, column=0, sticky="nsew")
        self.resource_pawns_listbox.bind("<<ListboxSelect>>", lambda _event: self._update_resource_pawn_preview())
        self._bind_toggle_multiselect(
            self.resource_pawns_listbox,
            select_callback=lambda _event: self._update_resource_pawn_preview(),
        )

        self.resource_pawn_preview = tk.Label(pawns_panel, text="选择左侧人物后，这里会显示详情。", bg=self.colors["panel_alt"], fg=self.colors["ink"], justify="left", anchor="nw", wraplength=520, padx=14, pady=14)
        self.resource_pawn_preview.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        pawn_buttons = tk.Frame(pawns_panel, bg=self.colors["panel"])
        pawn_buttons.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(pawn_buttons, text="载入到人物创建页", style="Subtle.TButton", command=self._load_selected_character_from_resources).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(pawn_buttons, text="删除选中人物", style="Subtle.TButton", command=self._delete_selected_pawn).pack(side="left", fill="x", expand=True)

        tk.Label(scenarios_panel, text="已保存场景", bg=self.colors["panel"], fg=self.colors["ink"], font=("Bahnschrift", 18, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(scenarios_panel, textvariable=self.resource_status_var, bg=self.colors["panel"], fg=self.colors["muted"], justify="left", wraplength=520, font=("Microsoft YaHei UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.resource_scenarios_listbox = self._simple_listbox(scenarios_panel, height=18, selectmode=tk.MULTIPLE)
        self.resource_scenarios_listbox.grid(row=2, column=0, sticky="nsew")
        self.resource_scenarios_listbox.bind("<<ListboxSelect>>", lambda _event: self._update_resource_scenario_preview())
        self._bind_toggle_multiselect(
            self.resource_scenarios_listbox,
            select_callback=lambda _event: self._update_resource_scenario_preview(),
        )

        self.resource_scenario_preview = tk.Label(scenarios_panel, text="选择左侧场景后，这里会显示详情。", bg=self.colors["panel_alt"], fg=self.colors["ink"], justify="left", anchor="nw", wraplength=520, padx=14, pady=14)
        self.resource_scenario_preview.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        scenario_buttons = tk.Frame(scenarios_panel, bg=self.colors["panel"])
        scenario_buttons.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(scenario_buttons, text="载入到场景设计页", style="Subtle.TButton", command=self._load_selected_scenario_from_resources).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(scenario_buttons, text="删除选中场景", style="Subtle.TButton", command=self._delete_selected_scenario).pack(side="left", fill="x", expand=True)

    def _load_startup_state(self) -> None:
        if not self.import_settings.game_data_root and self.discovered_paths.game_data_root is not None:
            self.import_settings.game_data_root = str(self.discovered_paths.game_data_root)
        if not self.import_settings.workshop_root and self.discovered_paths.workshop_root is not None:
            self.import_settings.workshop_root = str(self.discovered_paths.workshop_root)
        self.import_game_data_var.set(self.import_settings.game_data_root)
        self.import_workshop_var.set(self.import_settings.workshop_root)
        self._update_import_summary()
        self._refresh_saved_data()
        self._set_character_mode("species")
        self._set_scenario_picker_mode("attacker")
        self._refresh_character_firepower_preview()
        if self.import_settings.game_data_root and Path(self.import_settings.game_data_root).exists():
            self._load_catalog_from_settings(show_success=False)
        else:
            self._refresh_import_previews()

    def _auto_detect_paths(self) -> None:
        detected = discover_paths()
        if detected.game_data_root is not None:
            self.import_game_data_var.set(str(detected.game_data_root))
        if detected.workshop_root is not None:
            self.import_workshop_var.set(str(detected.workshop_root))
        self.status_var.set("已根据本机环境自动检测路径。确认无误后点击“导入原版数据”。")

    def _browse_game_data_root(self) -> None:
        path = filedialog.askdirectory(title="选择 RimWorld Data 目录")
        if path:
            self.import_game_data_var.set(path)

    def _browse_workshop_root(self) -> None:
        path = filedialog.askdirectory(title="选择 Steam 创意工坊目录")
        if path:
            self.import_workshop_var.set(path)

    def _import_catalog(self) -> None:
        self._load_catalog_from_settings(show_success=True)

    def _load_catalog_from_settings(self, *, show_success: bool) -> None:
        root = self.import_game_data_var.get().strip()
        if not root:
            messagebox.showerror("缺少目录", "请先填写游戏 Data 目录。")
            return
        path = Path(root)
        if not path.exists():
            messagebox.showerror("目录不存在", "填写的游戏 Data 目录不存在。")
            return
        try:
            self.catalog_index = load_catalog_index(path)
        except Exception as exc:
            messagebox.showerror("导入失败", f"读取原版数据时出错：\n{exc}")
            self.import_status_var.set("导入失败，请检查路径是否直接指向 RimWorld 的 Data 目录。")
            return
        self.import_settings = self.store.save_import_settings(
            ImportSettings(
                game_data_root=root,
                workshop_root=self.import_workshop_var.get().strip(),
                catalog_weapon_count=len(self.catalog_index.catalog.weapons),
                catalog_apparel_count=len(self.catalog_index.catalog.apparel),
                catalog_implant_count=len(self.catalog_index.catalog.implants),
                last_imported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        self._update_import_summary()
        self._refresh_import_previews()
        self._refresh_character_option_list()
        self._refresh_character_firepower_preview()
        self._run_scenario_analysis()
        self.status_var.set("原版数据已导入。现在可以到人物创建页选择武器、衣着和植入体。")
        self.import_status_var.set("导入成功，人物页和场景页已可用。")
        if show_success:
            messagebox.showinfo(
                "导入完成",
                f"已载入 {len(self.catalog_index.catalog.weapons)} 个武器、"
                f"{len(self.catalog_index.catalog.apparel)} 件衣着、"
                f"{len(self.catalog_index.catalog.implants)} 个植入体。",
            )

    def _update_import_summary(self) -> None:
        current_dir = self.import_game_data_var.get().strip() or "未设置"
        self.import_summary_vars["catalog"].set(current_dir)
        self.import_summary_vars["weapon_count"].set(str(self.import_settings.catalog_weapon_count))
        self.import_summary_vars["apparel_count"].set(str(self.import_settings.catalog_apparel_count))
        self.import_summary_vars["implant_count"].set(str(self.import_settings.catalog_implant_count))
        self.import_summary_vars["import_time"].set(self.import_settings.last_imported_at or "-")

    def _refresh_import_previews(self) -> None:
        self.import_weapon_preview.delete(0, tk.END)
        self.import_apparel_preview.delete(0, tk.END)
        if self.catalog_index is None:
            self.import_weapon_preview.insert(tk.END, "尚未导入任何原版武器。")
            self.import_apparel_preview.insert(tk.END, "尚未导入任何原版衣着。")
            return
        for record in self.catalog_index.catalog.weapons[:60]:
            self.import_weapon_preview.insert(tk.END, f"{record.display_label} / {record.def_name}")
        for record in self.catalog_index.catalog.apparel[:60]:
            self.import_apparel_preview.insert(tk.END, f"{record.display_label} / {record.def_name}")

    def _refresh_saved_data(self) -> None:
        self.saved_pawns = self.store.list_pawns()
        self.saved_scenarios = self.store.list_scenarios()
        self._refresh_character_saved_list()
        self._refresh_scenario_saved_list()
        self._refresh_scenario_selection_lists()
        self._refresh_scenario_picker_list()
        self._refresh_compare_source_list()
        self._refresh_resource_lists()

    def _pawn_display(self, pawn: SavedPawnTemplate) -> str:
        suffix = pawn.id[-6:] if len(pawn.id) >= 6 else pawn.id
        return f"{pawn.name} · {suffix}"

    def _scenario_display(self, scenario: SavedScenarioTemplate) -> str:
        suffix = scenario.id[-6:] if len(scenario.id) >= 6 else scenario.id
        return f"{scenario.name} · {suffix}"

    def _refresh_character_saved_list(self) -> None:
        self.character_saved_listbox.delete(0, tk.END)
        for pawn in self.saved_pawns:
            self.character_saved_listbox.insert(tk.END, self._pawn_display(pawn))
        self._update_character_import_preview()

    def _refresh_scenario_saved_list(self) -> None:
        self.scenario_saved_listbox.delete(0, tk.END)
        for scenario in self.saved_scenarios:
            self.scenario_saved_listbox.insert(tk.END, self._scenario_display(scenario))

    def _pawn_by_id(self, pawn_id: str) -> SavedPawnTemplate | None:
        return next((pawn for pawn in self.saved_pawns if pawn.id == pawn_id), None)

    def _implant_label(self, implant_id: str) -> str:
        option = IMPLANT_BY_ID.get(implant_id)
        if option is not None:
            return option.label
        if self.catalog_index is not None:
            record = self.catalog_index.implants_by_def_name.get(implant_id)
            if record is not None:
                return record.display_label
        return implant_id

    @staticmethod
    def _weapon_button_title(record: object) -> str:
        return getattr(record, "display_label", getattr(record, "label", getattr(record, "def_name", "武器")))

    @staticmethod
    def _apparel_button_title(record: object) -> str:
        return getattr(record, "display_label", getattr(record, "label", getattr(record, "def_name", "衣着")))

    @staticmethod
    def _implant_button_title(record: object) -> str:
        return getattr(record, "display_label", getattr(record, "label", getattr(record, "def_name", "植入体")))

    def _build_pawn_preview_text(self, pawn: SavedPawnTemplate) -> str:
        species = SPECIES_BY_ID.get(pawn.species_id, SPECIES_BY_ID["human_baseliner"])
        feature_lines = [FEATURE_BY_ID.get(item, FeatureOption(item, item, "trait", item)).label for item in pawn.feature_ids]
        support_gear_lines = [
            SUPPORT_GEAR_BY_ID.get(item).label if SUPPORT_GEAR_BY_ID.get(item) is not None else item
            for item in pawn.support_gear_ids
        ]
        implant_lines = [self._implant_label(item) for item in pawn.implant_ids]
        apparel_lines = [self._describe_choice(item) for item in pawn.apparel]
        return "\n".join(
            [
                f"名称：{pawn.name}",
                f"基础模板：{species.label}",
                f"射击等级：{pawn.shooting_skill}",
                f"全身护甲：{pawn.full_body_armor_percent:.0f}%",
                f"特性：{'、'.join(feature_lines) if feature_lines else '无'}",
                f"特殊装备：{'、'.join(support_gear_lines) if support_gear_lines else '无'}",
                f"植入体：{'、'.join(implant_lines) if implant_lines else '无'}",
                f"武器：{self._describe_choice(pawn.weapon) if pawn.weapon else '无'}",
                f"衣着：{'、'.join(apparel_lines) if apparel_lines else '无'}",
            ]
        )

    def _equipment_record_supports_material(self, choice: EquipmentChoice | None) -> bool:
        if choice is None or self.catalog_index is None:
            return bool(choice is not None and choice.material_id)
        weapon = self.catalog_index.weapons_by_def_name.get(choice.def_name)
        if weapon is not None:
            return weapon.supports_material
        apparel = self.catalog_index.apparel_by_def_name.get(choice.def_name)
        if apparel is not None:
            return apparel.supports_material
        return bool(choice.material_id)

    def _describe_choice(self, choice: EquipmentChoice | None) -> str:
        if choice is None:
            return "无"
        return describe_equipment(choice, supports_material=self._equipment_record_supports_material(choice))

    def _refresh_scenario_selection_lists(self) -> None:
        valid_ids = {pawn.id for pawn in self.saved_pawns}
        self.scenario_attacker_ids = [
            pawn_id for pawn_id in dict.fromkeys(self.scenario_attacker_ids) if pawn_id in valid_ids
        ]
        self.scenario_defender_ids = [
            pawn_id for pawn_id in dict.fromkeys(self.scenario_defender_ids) if pawn_id in valid_ids
        ]
        if not hasattr(self, "scenario_attacker_listbox"):
            return
        self.scenario_attacker_listbox.delete(0, tk.END)
        self.scenario_defender_listbox.delete(0, tk.END)
        for pawn_id in self.scenario_attacker_ids:
            pawn = self._pawn_by_id(pawn_id)
            if pawn is not None:
                self.scenario_attacker_listbox.insert(tk.END, self._pawn_display(pawn))
        for pawn_id in self.scenario_defender_ids:
            pawn = self._pawn_by_id(pawn_id)
            if pawn is not None:
                self.scenario_defender_listbox.insert(tk.END, self._pawn_display(pawn))
        if not self.scenario_attacker_ids:
            self.scenario_attacker_status_var.set("未选择攻击方")
        elif len(self.scenario_attacker_ids) == 1:
            pawn = self._pawn_by_id(self.scenario_attacker_ids[0])
            self.scenario_attacker_status_var.set(f"已选择：{pawn.name if pawn else '未知人物'}")
        else:
            self.scenario_attacker_status_var.set(f"已选择 {len(self.scenario_attacker_ids)} 名攻击方")
        if not self.scenario_defender_ids:
            self.scenario_defender_status_var.set("未选择防守方")
        elif len(self.scenario_defender_ids) == 1:
            pawn = self._pawn_by_id(self.scenario_defender_ids[0])
            self.scenario_defender_status_var.set(f"已选择：{pawn.name if pawn else '未知人物'}")
        else:
            self.scenario_defender_status_var.set(f"已选择 {len(self.scenario_defender_ids)} 名防守方")
        self._sync_scenario_name_state()

    def _sync_scenario_name_state(self) -> None:
        if not hasattr(self, "scenario_name_entry"):
            return
        pair_count = len(self.scenario_attacker_ids) * len(self.scenario_defender_ids)
        placeholder_prefix = "将自动生成 "
        current_name = self.scenario_name_var.get().strip()
        if len(self.scenario_attacker_ids) == 1 and len(self.scenario_defender_ids) == 1:
            self.scenario_name_entry.configure(state="normal")
            attacker = self._pawn_by_id(self.scenario_attacker_ids[0])
            defender = self._pawn_by_id(self.scenario_defender_ids[0])
            auto_name = (
                f"{attacker.name} VS {defender.name}"
                if attacker is not None and defender is not None
                else "未命名场景"
            )
            if not current_name or current_name.startswith(placeholder_prefix):
                self.scenario_name_var.set(auto_name)
            self.scenario_name_hint_var.set("当前是单组攻防，可直接修改场景名称。")
            return
        self.scenario_name_entry.configure(state="disabled")
        if pair_count > 0:
            self.scenario_name_var.set(f"{placeholder_prefix}{pair_count} 个场景")
            self.scenario_name_hint_var.set(
                f"批量模式会自动按“攻击方 VS 防守方”命名，当前将生成 {pair_count} 个场景。"
            )
        else:
            self.scenario_name_var.set("")
            self.scenario_name_hint_var.set("单组攻防可以自定义场景名；批量组合会自动命名为“攻击方 VS 防守方”。")

    def _set_scenario_picker_mode(self, mode: str) -> None:
        self.scenario_picker_mode = mode
        if mode == "attacker":
            self.scenario_picker_mode_var.set("当前添加到：攻击方")
            self.scenario_picker_apply_button.configure(text="加入攻击方")
        else:
            self.scenario_picker_mode_var.set("当前添加到：防守方")
            self.scenario_picker_apply_button.configure(text="加入防守方")

    def _refresh_scenario_picker_list(self) -> None:
        if not hasattr(self, "scenario_picker_listbox"):
            return
        self.scenario_picker_listbox.delete(0, tk.END)
        query = self.scenario_picker_search_var.get().strip().lower()
        for pawn in self.saved_pawns:
            display = self._pawn_display(pawn)
            preview_text = self._build_pawn_preview_text(pawn).lower()
            if query and query not in display.lower() and query not in preview_text:
                continue
            self.scenario_picker_listbox.insert(tk.END, display)
        if self.scenario_picker_listbox.size() > 0:
            self.scenario_picker_listbox.selection_set(0)
            self._update_scenario_picker_preview(None)
        else:
            self.scenario_picker_preview_var.set("没有匹配的人物。先保存人物模板，或调整搜索词。")

    def _update_scenario_picker_preview(self, _event: object) -> None:
        if not hasattr(self, "scenario_picker_listbox"):
            return
        pawn = self._selected_saved_pawn_from_listbox(self.scenario_picker_listbox)
        if pawn is None:
            self.scenario_picker_preview_var.set("从下方已保存人物列表中选择一个人物，即可加入攻击方或防守方。")
            return
        self.scenario_picker_preview_var.set(self._build_pawn_preview_text(pawn))

    def _selected_scenario_editor_pawn(self, listbox: tk.Listbox, pawn_ids: list[str]) -> SavedPawnTemplate | None:
        index = self._single_selected_index(listbox)
        if index is None or index >= len(pawn_ids):
            return None
        return self._pawn_by_id(pawn_ids[index])

    def _add_selected_pawn_to_scenario(self) -> None:
        pawn = self._selected_saved_pawn_from_listbox(self.scenario_picker_listbox)
        if pawn is None:
            messagebox.showerror("没有选择人物", "请先在人物列表中选中一个人物。")
            return
        target_ids = self.scenario_attacker_ids if self.scenario_picker_mode == "attacker" else self.scenario_defender_ids
        if pawn.id in target_ids:
            self.scenario_status_var.set(f"{pawn.name} 已经在当前列表中，无需重复加入。")
            return
        target_ids.append(pawn.id)
        self._refresh_scenario_selection_lists()
        self.scenario_status_var.set(f"已将 {pawn.name} 加入{ '攻击方' if self.scenario_picker_mode == 'attacker' else '防守方' }。")
        self._schedule_scenario_analysis()

    def _remove_selected_scenario_attacker(self) -> None:
        pawn = self._selected_scenario_editor_pawn(self.scenario_attacker_listbox, self.scenario_attacker_ids)
        if pawn is None:
            return
        self.scenario_attacker_ids = [pawn_id for pawn_id in self.scenario_attacker_ids if pawn_id != pawn.id]
        self._refresh_scenario_selection_lists()
        self.scenario_status_var.set(f"已从攻击方移除 {pawn.name}。")
        self._schedule_scenario_analysis()

    def _remove_selected_scenario_defender(self) -> None:
        pawn = self._selected_scenario_editor_pawn(self.scenario_defender_listbox, self.scenario_defender_ids)
        if pawn is None:
            return
        self.scenario_defender_ids = [pawn_id for pawn_id in self.scenario_defender_ids if pawn_id != pawn.id]
        self._refresh_scenario_selection_lists()
        self.scenario_status_var.set(f"已从防守方移除 {pawn.name}。")
        self._schedule_scenario_analysis()

    def _on_character_search_changed(self) -> None:
        if self.character_search_syncing:
            return
        self.character_search_cache[self.character_mode] = self.character_search_var.get()
        self._refresh_character_option_list()

    def _sync_character_equipment_controls(self, choice: EquipmentChoice | None) -> None:
        if choice is None:
            self.character_quality_var.set(QUALITY_OPTIONS[2].label)
            self.character_material_var.set("")
            self._refresh_material_controls()
            return
        supports_material = self._equipment_record_supports_material(choice)
        quality = next((item for item in QUALITY_OPTIONS if item.id == choice.quality_id), QUALITY_OPTIONS[2])
        self.character_quality_var.set(quality.label)
        if supports_material:
            material = next((item for item in MATERIAL_OPTIONS if item.id == choice.material_id), MATERIAL_OPTIONS[1])
            self.character_material_var.set(material.label)
        else:
            self.character_material_var.set("")
        self._refresh_material_controls()

    def _on_character_equipment_controls_changed(self) -> None:
        if self.character_mode == "weapon" and self.character_weapon_choice is not None:
            self.character_weapon_choice = self._choice_from_equipment_controls(
                self.character_weapon_choice.def_name,
                self.character_weapon_choice.label,
            )
            self.character_weapon_summary_var.set(self._describe_choice(self.character_weapon_choice))
        self._refresh_character_firepower_preview()

    def _on_character_defense_controls_changed(self) -> None:
        self._refresh_character_firepower_preview()

    def _set_character_firepower_defaults(self, message: str) -> None:
        self.character_power_status_var.set(message)
        for var in self.character_power_metric_vars.values():
            var.set("-")
        for row_vars in self.character_power_target_rows:
            row_vars["label"].set("-")
            row_vars["dps"].set("-")
            row_vars["ratio"].set("-")

    def _parse_character_shooting_skill(self) -> int | None:
        try:
            return max(0, min(int(self.character_shooting_skill_var.get().strip()), 20))
        except ValueError:
            return None

    def _parse_character_full_body_armor_percent(self) -> float | None:
        raw_value = self.character_full_body_armor_var.get().strip()
        if not raw_value:
            return 0.0
        try:
            return max(0.0, min(float(raw_value), 200.0))
        except ValueError:
            return None

    def _format_character_full_body_armor_percent(self, value: float) -> str:
        numeric = float(value)
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.2f}".rstrip("0").rstrip(".")

    def _current_character_template(self) -> SavedPawnTemplate | None:
        if not self.character_species_id:
            return None
        shooting_skill = self._parse_character_shooting_skill()
        full_body_armor_percent = self._parse_character_full_body_armor_percent()
        if shooting_skill is None or full_body_armor_percent is None:
            return None
        return SavedPawnTemplate(
            id=self.current_character_id or "preview-pawn",
            name=self.character_name_var.get().strip() or "当前人物",
            species_id=self.character_species_id,
            feature_ids=list(self.character_feature_ids),
            support_gear_ids=list(self.character_support_gear_ids),
            implant_ids=list(self.character_implant_ids),
            shooting_skill=shooting_skill,
            full_body_armor_percent=full_body_armor_percent,
            weapon=self.character_weapon_choice,
            apparel=list(self.character_apparel_choices),
        )

    def _refresh_character_firepower_preview(self) -> None:
        if self.catalog_index is None:
            self._set_character_firepower_defaults("请先导入原版数据，人物页才能计算实时输出能力。")
            return
        if not self.character_species_id:
            self._set_character_firepower_defaults("先选择基础模板，右侧才会生成实时输出能力。")
            return
        current_species = self._current_species_option()
        if not current_species.can_use_weapons:
            self._set_character_firepower_defaults("当前种族不使用武器，因此不显示射击输出预览。")
            return
        if self.character_weapon_choice is None:
            self._set_character_firepower_defaults("请先为当前人物选择武器。")
            return
        if self._parse_character_shooting_skill() is None:
            self._set_character_firepower_defaults("\u5c04\u51fb\u7b49\u7ea7\u9700\u8981\u586b\u5199 0 \u5230 20 \u7684\u6574\u6570\u3002")
            return
        if self._parse_character_full_body_armor_percent() is None:
            self._set_character_firepower_defaults("\u5168\u8eab\u62a4\u7532\u9700\u8981\u586b\u5199\u6570\u5b57\u767e\u5206\u6bd4\u3002")
            return
        pawn = self._current_character_template()
        if pawn is None:
            self._set_character_firepower_defaults("\u8f93\u5165\u5185\u5bb9\u65e0\u6548\uff0c\u8bf7\u68c0\u67e5\u5c04\u51fb\u7b49\u7ea7\u548c\u5168\u8eab\u62a4\u7532\u3002")
            return
        try:
            preview = build_firepower_preview_for_pawn(pawn, self.catalog_index)
        except Exception as exc:
            self._set_character_firepower_defaults(str(exc))
            return
        self.character_power_status_var.set(f"当前武器：{preview.weapon_name}")
        self.character_power_metric_vars["distance"].set(preview.best_distance_label)
        self.character_power_metric_vars["hit"].set(f"{preview.final_hit_percent:.2f}%")
        self.character_power_metric_vars["warmup"].set(
            f"{preview.actual_warmup_seconds:.2f}/{preview.base_warmup_seconds:.2f}"
        )
        self.character_power_metric_vars["cooldown"].set(
            f"{preview.actual_cooldown_seconds:.2f}/{preview.base_cooldown_seconds:.2f}"
        )
        if preview.targets:
            self.character_power_metric_vars["unarmored_dps"].set(f"{preview.targets[0].expected_dps:.4f}")
        else:
            self.character_power_metric_vars["unarmored_dps"].set("-")
        for index, row_vars in enumerate(self.character_power_target_rows):
            if index >= len(preview.targets):
                row_vars["dps"].set("-")
                row_vars["ratio"].set("-")
                continue
            target = preview.targets[index]
            row_vars["label"].set(target.label)
            row_vars["dps"].set(f"{target.expected_dps:.4f}")
            row_vars["ratio"].set(f"{target.ratio_to_unarmored * 100.0:.1f}%")

    def _refresh_compare_source_list(self) -> None:
        self.compare_source_listbox.delete(0, tk.END)
        query = self.compare_filter_var.get().strip().lower()
        for scenario in self.saved_scenarios:
            display = self._scenario_display(scenario)
            if query and query not in display.lower():
                continue
            self.compare_source_listbox.insert(tk.END, display)

    def _refresh_resource_lists(self) -> None:
        self.resource_pawns_listbox.delete(0, tk.END)
        self.resource_scenarios_listbox.delete(0, tk.END)
        for pawn in self.saved_pawns:
            self.resource_pawns_listbox.insert(tk.END, self._pawn_display(pawn))
        for scenario in self.saved_scenarios:
            self.resource_scenarios_listbox.insert(tk.END, self._scenario_display(scenario))
        self._update_resource_pawn_preview()
        self._update_resource_scenario_preview()

    def _set_character_mode(self, mode: str) -> None:
        self.character_mode = mode
        if mode == "species":
            self.character_mode_title_var.set("选择基础模板")
            self.character_mode_hint_var.set("用基础模板决定当前小人的大类。")
            self.character_apply_button.configure(text="设为当前基础模板")
        elif mode == "features":
            self.character_mode_title_var.set("选择特性")
            self.character_mode_hint_var.set("特性可重复添加，不设上限。")
            self.character_apply_button.configure(text="添加到特性列表")
        elif mode == "support_gear":
            self.character_mode_title_var.set("选择特殊装备")
            self.character_mode_hint_var.set("这里放会影响射击的额外装备，比如弹药带、目镜和稳定组件。")
            self.character_apply_button.configure(text="添加到特殊装备列表")
        elif mode == "implants":
            self.character_mode_title_var.set("选择植入体")
            self.character_mode_hint_var.set("植入体会影响视力、操作能力，并联动命中、瞄准和冷却；导入原版目录后会出现可识别的原版植入体。")
            self.character_apply_button.configure(text="添加到植入体列表")
        elif mode == "weapon":
            self.character_mode_title_var.set("选择武器")
            self.character_mode_hint_var.set("选择武器后，再通过品质和材质完成配置。")
            self.character_apply_button.configure(text="设为当前武器")
        elif mode == "apparel":
            self.character_mode_title_var.set("选择衣着")
            self.character_mode_hint_var.set("衣着可以多次加入，只要最终穿戴合法即可。")
            self.character_apply_button.configure(text="加入当前衣着")
        else:
            self.character_mode_title_var.set("选择内容")
            self.character_mode_hint_var.set("从中间列表里选择一个项目。")
            self.character_apply_button.configure(text="应用当前选择")
        if mode in {"weapon", "apparel"}:
            self.character_equipment_frame.grid()
        else:
            self.character_equipment_frame.grid_remove()
        if mode == "weapon":
            self._sync_character_equipment_controls(self.character_weapon_choice)
        elif mode != "apparel":
            self._sync_character_equipment_controls(None)
        self._refresh_material_controls()
        self.character_search_syncing = True
        self.character_search_var.set(self.character_search_cache.get(mode, ""))
        self.character_search_syncing = False
        self._refresh_character_option_list()

    def _current_species_option(self) -> SpeciesOption:
        return SPECIES_BY_ID.get(self.character_species_id, SPECIES_BY_ID["human_baseliner"])

    def _refresh_character_option_list(self) -> None:
        self.character_option_records = []
        self.character_option_listbox.delete(0, tk.END)
        query = self.character_search_cache.get(self.character_mode, self.character_search_var.get()).strip().lower()
        if self.character_mode == "species":
            for item in SPECIES_OPTIONS:
                text = f"{item.label} {item.group} {item.description}".lower()
                if query and query not in text:
                    continue
                self.character_option_records.append(
                    CharacterOptionRecord("species", item.id, item.label, item.group, item.description)
                )
        elif self.character_mode == "features":
            current_species = self._current_species_option()
            if not current_species.can_use_features:
                self.character_preview_title_var.set("当前种族不支持特性")
                self.character_preview_body_var.set("先改回类人模板，再添加特性。")
                return
            for item in FEATURE_OPTIONS:
                text = f"{item.label} {item.description}".lower()
                if query and query not in text:
                    continue
                impact_lines = describe_modifier_payload(item.modifier_payload)
                preview = _join_preview_sections(
                    ("简介", item.description),
                    ("实际影响", impact_lines),
                )
                self.character_option_records.append(
                    CharacterOptionRecord(
                        "features",
                        item.id,
                        item.label,
                        "特性" if item.kind == "trait" else "增益",
                        preview or item.description,
                    )
                )
        elif self.character_mode == "support_gear":
            current_species = self._current_species_option()
            if not current_species.can_use_weapons:
                self.character_preview_title_var.set("当前种族不支持特殊装备")
                self.character_preview_body_var.set("先改回可使用武器的类人模板，再添加特殊装备。")
                return
            for item in SUPPORT_GEAR_OPTIONS:
                text = f"{item.label} {item.description}".lower()
                if query and query not in text:
                    continue
                impact_lines = describe_modifier_payload(item.modifier_payload)
                preview = _join_preview_sections(
                    ("来源", "原版条目" if item.source == "vanilla" else "自定义条目"),
                    ("简介", item.description),
                    ("实际影响", impact_lines),
                )
                self.character_option_records.append(
                    CharacterOptionRecord(
                        "support_gear",
                        item.id,
                        item.label,
                        "射击修正",
                        preview or item.description,
                    )
                )
        elif self.character_mode == "implants":
            current_species = self._current_species_option()
            if not current_species.can_use_weapons:
                self.character_preview_title_var.set("当前种族不支持植入体")
                self.character_preview_body_var.set("先改回可使用武器的类人模板，再添加植入体。")
                return
            if self.catalog_index is not None:
                for item in self.catalog_index.search_implants(query):
                    modifier_lines = describe_modifier_payload(item.modifier.to_dict() if item.modifier is not None else None)
                    preview = (
                        _join_preview_sections(
                            ("来源", f"{item.source_package} / {item.source_tag}"),
                            (
                                "基础信息",
                                [
                                    f"DefName: {item.def_name}",
                                    f"部位: {item.body_part_hint}",
                                    f"部位效率: {item.part_efficiency:.2f}",
                                ],
                            ),
                            ("实际影响", modifier_lines),
                        )
                    )
                    self.character_option_records.append(
                        CharacterOptionRecord(
                            "implants",
                            item.def_name,
                            self._implant_button_title(item),
                            item.body_part_hint,
                            preview,
                        )
                    )
            for item in IMPLANT_OPTIONS:
                text = f"{item.label} {item.description}".lower()
                if query and query not in text:
                    continue
                impact_lines = describe_modifier_payload(item.modifier_payload)
                preview = _join_preview_sections(
                    ("来源", "原版近似模板" if item.source == "vanilla" else "自定义条目"),
                    ("简介", item.description),
                    ("实际影响", impact_lines),
                )
                self.character_option_records.append(
                    CharacterOptionRecord(
                        "implants",
                        item.id,
                        item.label,
                        "能力修正",
                        preview or item.description,
                    )
                )
        elif self.character_mode == "weapon":
            current_species = self._current_species_option()
            if not current_species.can_use_weapons:
                self.character_preview_title_var.set("当前种族不支持武器")
                self.character_preview_body_var.set("先改回类人模板，再选择武器。")
                return
            if self.catalog_index is None:
                self.character_preview_title_var.set("还没有原版目录")
                self.character_preview_body_var.set("先到“数据导入”页导入原版数据，然后回来选择武器。")
                return
            for record in self.catalog_index.search_weapons(query):
                preview = (
                    f"DefName: {record.def_name}\n"
                    f"伤害类型: {record.damage_type}\n"
                    f"伤害: {record.damage:.2f}\n"
                    f"护甲穿透: {record.armor_penetration:.2f}\n"
                    f"暖机: {record.warmup_seconds:.2f}s / 冷却: {record.cooldown_seconds:.2f}s"
                )
                self.character_option_records.append(
                    CharacterOptionRecord(
                        "weapon",
                        record.def_name,
                        self._weapon_button_title(record),
                        f"伤害 {record.damage:.2f}",
                        preview,
                    )
                )
        elif self.character_mode == "apparel":
            current_species = self._current_species_option()
            if not current_species.can_wear_apparel:
                self.character_preview_title_var.set("当前种族不支持衣着")
                self.character_preview_body_var.set("先改回类人模板，再选择衣着。")
                return
            if self.catalog_index is None:
                self.character_preview_title_var.set("还没有原版目录")
                self.character_preview_body_var.set("先到“数据导入”页导入原版数据，然后回来选择衣着。")
                return
            for record in self.catalog_index.search_apparel(query):
                preview = (
                    f"DefName: {record.def_name}\n"
                    f"层级: {', '.join(record.layers) or '-'}\n"
                    f"覆盖: {', '.join(record.body_part_groups) or '-'}\n"
                    f"锋利护甲: {record.armor_sharp:.2f}\n"
                    f"钝击护甲: {record.armor_blunt:.2f}\n"
                    f"高温护甲: {record.armor_heat:.2f}"
                )
                self.character_option_records.append(
                    CharacterOptionRecord(
                        "apparel",
                        record.def_name,
                        self._apparel_button_title(record),
                        f"锋 {record.armor_sharp:.2f}",
                        preview,
                    )
                )
        for item in self.character_option_records:
            self.character_option_listbox.insert(tk.END, f"{item.title}  |  {item.subtitle}")
        if not self.character_option_records:
            self.character_preview_title_var.set("没有匹配结果")
            self.character_preview_body_var.set("改一下搜索词，或者先导入原版目录。")
        else:
            self.character_option_listbox.selection_clear(0, tk.END)
            self.character_option_listbox.activate(0)
            self._on_character_option_selected(None)

    def _selected_indices(self, listbox: tk.Listbox) -> list[int]:
        return [int(index) for index in listbox.curselection()]

    def _active_selected_index(self, listbox: tk.Listbox) -> int | None:
        selection = self._selected_indices(listbox)
        if not selection:
            return None
        try:
            active_index = int(listbox.index("active"))
        except tk.TclError:
            active_index = selection[-1]
        if active_index in selection:
            return active_index
        return selection[-1]

    def _single_selected_index(self, listbox: tk.Listbox) -> int | None:
        selection = self._selected_indices(listbox)
        if not selection:
            return None
        return selection[0]

    def _only_selected_index(self, listbox: tk.Listbox) -> int | None:
        selection = self._selected_indices(listbox)
        if len(selection) != 1:
            return None
        return selection[0]

    def _on_character_option_selected(self, _event: object) -> None:
        index = self._active_selected_index(self.character_option_listbox)
        if index is None or index >= len(self.character_option_records):
            if not self.character_option_records:
                self.character_preview_title_var.set("暂无预览")
                self.character_preview_body_var.set("点击左侧分类后，在右侧选择内容。")
            self._refresh_material_controls()
            return
        item = self.character_option_records[index]
        self.character_preview_title_var.set(item.title)
        self.character_preview_body_var.set(item.preview)
        self._refresh_material_controls()

    def _choice_from_equipment_controls(
        self,
        def_name: str,
        label: str,
        *,
        supports_material: bool | None = None,
    ) -> EquipmentChoice:
        quality = next((item for item in QUALITY_OPTIONS if item.label == self.character_quality_var.get()), QUALITY_OPTIONS[2])
        if supports_material is None:
            supports_material = self._current_record_supports_material_for_mode()
        material_id: str | None = None
        if supports_material:
            material = next((item for item in MATERIAL_OPTIONS if item.label == self.character_material_var.get()), MATERIAL_OPTIONS[1])
            material_id = material.id
        return EquipmentChoice(def_name=def_name, label=label, quality_id=quality.id, material_id=material_id)

    def _selected_character_option_indices(self) -> list[int]:
        return [index for index in self._selected_indices(self.character_option_listbox) if index < len(self.character_option_records)]

    def _apply_character_option_from_index(self, index: int) -> None:
        if index < 0 or index >= len(self.character_option_records):
            return
        self._apply_character_option(indices=[index])

    def _apply_character_option(self, indices: list[int] | None = None) -> None:
        selected_indices = self._selected_character_option_indices() if indices is None else indices
        valid_indices = [index for index in selected_indices if 0 <= index < len(self.character_option_records)]
        if not valid_indices:
            messagebox.showerror("没有选择内容", "请先在右侧列表中选择一项。")
            return
        items = [self.character_option_records[index] for index in valid_indices]
        primary = items[0]
        if primary.mode == "species":
            if len(items) > 1:
                messagebox.showerror("无法批量设置", "基础模板一次只能选择一个。")
                return
            item = primary
            self.character_species_id = item.key
            species = SPECIES_BY_ID[item.key]
            self.character_species_summary_var.set(f"{species.label} / {species.group}")
            self.character_full_body_armor_var.set(
                self._format_character_full_body_armor_percent(species.default_full_body_armor_percent)
            )
            if species.id not in humanlike_species_ids():
                self.character_feature_ids = []
                self.character_support_gear_ids = []
                self.character_implant_ids = []
                self.character_weapon_choice = None
                self.character_apparel_choices = []
                self.character_feature_listbox.delete(0, tk.END)
                self.character_support_gear_listbox.delete(0, tk.END)
                self.character_implant_listbox.delete(0, tk.END)
                self.character_apparel_listbox.delete(0, tk.END)
                self._sync_character_equipment_controls(None)
                self.character_weapon_summary_var.set("该种族不使用武器")
                self.character_feature_status_var.set("该种族不支持特性")
                self.character_support_gear_status_var.set("该种族不支持特殊装备")
                self.character_implant_status_var.set("该种族不支持植入体")
                self.character_apparel_status_var.set("该种族不支持衣着")
            else:
                self._update_character_feature_status()
                self._update_character_support_gear_status()
                self._update_character_implant_status()
                self._update_character_apparel_status()
                if self.character_weapon_choice is None:
                    self.character_weapon_summary_var.set("未选择武器")
            self.status_var.set(f"当前人物基础模板已切换为“{species.label}”。")
            self._refresh_character_option_list()
            self._refresh_character_firepower_preview()
            return
        if primary.mode == "features":
            for item in items:
                self.character_feature_ids.append(item.key)
                self.character_feature_listbox.insert(tk.END, FEATURE_BY_ID[item.key].label)
            self._update_character_feature_status()
            if len(items) == 1:
                self.status_var.set(f"已添加特性：{FEATURE_BY_ID[primary.key].label}")
            else:
                self.status_var.set(f"已批量添加 {len(items)} 个特性。")
            self._refresh_character_firepower_preview()
            return
        if primary.mode == "support_gear":
            for item in items:
                self.character_support_gear_ids.append(item.key)
                self.character_support_gear_listbox.insert(tk.END, SUPPORT_GEAR_BY_ID[item.key].label)
            self._update_character_support_gear_status()
            if len(items) == 1:
                self.status_var.set(f"已添加特殊装备：{SUPPORT_GEAR_BY_ID[primary.key].label}")
            else:
                self.status_var.set(f"已批量添加 {len(items)} 件特殊装备。")
            self._refresh_character_firepower_preview()
            return
        if primary.mode == "implants":
            for item in items:
                self.character_implant_ids.append(item.key)
                self.character_implant_listbox.insert(tk.END, self._implant_label(item.key))
            self._update_character_implant_status()
            if len(items) == 1:
                self.status_var.set(f"已添加植入体：{self._implant_label(primary.key)}")
            else:
                self.status_var.set(f"已批量添加 {len(items)} 个植入体。")
            self._refresh_character_firepower_preview()
            return
        if primary.mode == "weapon":
            if len(items) > 1:
                messagebox.showerror("无法批量设置", "武器一次只能选择一把。")
                return
            item = primary
            supports_material = False
            if self.catalog_index is not None:
                weapon_record = self.catalog_index.weapons_by_def_name.get(item.key)
                supports_material = bool(weapon_record is not None and weapon_record.supports_material)
            self.character_weapon_choice = self._choice_from_equipment_controls(
                item.key,
                item.title,
                supports_material=supports_material,
            )
            self.character_weapon_summary_var.set(self._describe_choice(self.character_weapon_choice))
            self.status_var.set("当前人物武器已更新。")
            self._sync_character_equipment_controls(self.character_weapon_choice)
            self._refresh_character_firepower_preview()
            return
        for item in items:
            supports_material = False
            if self.catalog_index is not None:
                apparel_record = self.catalog_index.apparel_by_def_name.get(item.key)
                supports_material = bool(apparel_record is not None and apparel_record.supports_material)
            self.character_apparel_choices.append(
                self._choice_from_equipment_controls(
                    item.key,
                    item.title,
                    supports_material=supports_material,
                )
            )
            self.character_apparel_listbox.insert(tk.END, self._describe_choice(self.character_apparel_choices[-1]))
        self._update_character_apparel_status()
        if len(items) == 1:
            self.status_var.set("已将衣着加入当前人物。")
        else:
            self.status_var.set(f"已批量加入 {len(items)} 件衣着。")
        self._refresh_character_firepower_preview()

    def _update_character_feature_status(self) -> None:
        self.character_feature_status_var.set("未添加特性" if not self.character_feature_ids else f"已添加 {len(self.character_feature_ids)} 个特性")

    def _update_character_support_gear_status(self) -> None:
        self.character_support_gear_status_var.set(
            "未添加特殊装备"
            if not self.character_support_gear_ids
            else f"已添加 {len(self.character_support_gear_ids)} 件特殊装备"
        )

    def _update_character_implant_status(self) -> None:
        self.character_implant_status_var.set(
            "未添加植入体"
            if not self.character_implant_ids
            else f"已添加 {len(self.character_implant_ids)} 个植入体"
        )

    def _update_character_apparel_status(self) -> None:
        self.character_apparel_status_var.set("未添加衣着" if not self.character_apparel_choices else f"已添加 {len(self.character_apparel_choices)} 件衣着")

    def _remove_selected_feature(self) -> None:
        indices = self._selected_indices(self.character_feature_listbox)
        if not indices:
            return
        for index in sorted(indices, reverse=True):
            del self.character_feature_ids[index]
            self.character_feature_listbox.delete(index)
        self._update_character_feature_status()
        self.status_var.set(f"已删除 {len(indices)} 个特性。")
        self._refresh_character_firepower_preview()

    def _remove_selected_support_gear(self) -> None:
        indices = self._selected_indices(self.character_support_gear_listbox)
        if not indices:
            return
        for index in sorted(indices, reverse=True):
            del self.character_support_gear_ids[index]
            self.character_support_gear_listbox.delete(index)
        self._update_character_support_gear_status()
        self.status_var.set(f"已删除 {len(indices)} 件特殊装备。")
        self._refresh_character_firepower_preview()

    def _remove_selected_implant(self) -> None:
        indices = self._selected_indices(self.character_implant_listbox)
        if not indices:
            return
        for index in sorted(indices, reverse=True):
            del self.character_implant_ids[index]
            self.character_implant_listbox.delete(index)
        self._update_character_implant_status()
        self.status_var.set(f"已删除 {len(indices)} 个植入体。")
        self._refresh_character_firepower_preview()

    def _remove_selected_apparel(self) -> None:
        indices = self._selected_indices(self.character_apparel_listbox)
        if not indices:
            return
        for index in sorted(indices, reverse=True):
            del self.character_apparel_choices[index]
            self.character_apparel_listbox.delete(index)
        self._update_character_apparel_status()
        self.status_var.set(f"已删除 {len(indices)} 件衣着。")
        self._refresh_character_firepower_preview()

    def _save_character(self) -> None:
        name = self.character_name_var.get().strip()
        if not name:
            messagebox.showerror("缺少名称", "请输入人物模板名称。")
            return
        if not self.character_species_id:
            messagebox.showerror("缺少基础模板", "请先选择人物基础模板。")
            return
        try:
            shooting_skill = max(0, min(int(self.character_shooting_skill_var.get().strip()), 20))
        except ValueError:
            messagebox.showerror("\u8f93\u5165\u9519\u8bef", "\u5c04\u51fb\u7b49\u7ea7\u5fc5\u987b\u662f 0 \u5230 20 \u7684\u6574\u6570\u3002")
            return
        full_body_armor_percent = self._parse_character_full_body_armor_percent()
        if full_body_armor_percent is None:
            messagebox.showerror("\u8f93\u5165\u9519\u8bef", "\u5168\u8eab\u62a4\u7532\u9700\u8981\u586b\u5199\u6570\u5b57\u767e\u5206\u6bd4\u3002")
            return
        pawn = SavedPawnTemplate(
            id=self.store.make_id(name),
            name=name,
            species_id=self.character_species_id,
            feature_ids=list(self.character_feature_ids),
            support_gear_ids=list(self.character_support_gear_ids),
            implant_ids=list(self.character_implant_ids),
            shooting_skill=shooting_skill,
            full_body_armor_percent=full_body_armor_percent,
            weapon=self.character_weapon_choice,
            apparel=list(self.character_apparel_choices),
        )
        saved = self.store.save_pawn(pawn)
        self.current_character_id = None
        self.character_editor_title_var.set(f"继续基于当前配置新建：{saved.name}")
        self._refresh_saved_data()
        self.status_var.set(f"人物“{saved.name}”已保存为新记录，继续微调后再次保存也不会覆盖旧记录。")
        self._refresh_character_firepower_preview()
        self._schedule_scenario_analysis()

    def _reset_character_editor(self) -> None:
        self.current_character_id = None
        self.character_editor_title_var.set("新建人物")
        self.character_name_var.set("")
        self.character_species_id = ""
        self.character_species_summary_var.set("未选择")
        self.character_shooting_skill_var.set("10")
        self.character_full_body_armor_var.set("0")
        self.character_feature_ids = []
        self.character_support_gear_ids = []
        self.character_implant_ids = []
        self.character_weapon_choice = None
        self.character_apparel_choices = []
        self.character_feature_listbox.delete(0, tk.END)
        self.character_support_gear_listbox.delete(0, tk.END)
        self.character_implant_listbox.delete(0, tk.END)
        self.character_apparel_listbox.delete(0, tk.END)
        self.character_weapon_summary_var.set("未选择武器")
        self.character_feature_status_var.set("未添加特性")
        self.character_support_gear_status_var.set("未添加特殊装备")
        self.character_implant_status_var.set("未添加植入体")
        self.character_apparel_status_var.set("未添加衣着")
        self.status_var.set("人物编辑器已重置。")
        self._sync_character_equipment_controls(None)
        self._set_character_mode("species")
        self._refresh_character_firepower_preview()

    def _load_character_into_editor(self, pawn: SavedPawnTemplate) -> None:
        self.current_character_id = None
        self.character_editor_title_var.set(f"基于人物微调：{pawn.name}")
        self.character_name_var.set(pawn.name)
        self.character_species_id = pawn.species_id
        species = SPECIES_BY_ID.get(pawn.species_id, SPECIES_BY_ID["human_baseliner"])
        self.character_species_summary_var.set(f"{species.label} / {species.group}")
        self.character_shooting_skill_var.set(str(pawn.shooting_skill))
        self.character_full_body_armor_var.set(
            self._format_character_full_body_armor_percent(pawn.full_body_armor_percent)
        )
        self.character_feature_ids = list(pawn.feature_ids)
        self.character_support_gear_ids = list(pawn.support_gear_ids)
        self.character_implant_ids = list(pawn.implant_ids)
        self.character_feature_listbox.delete(0, tk.END)
        for feature_id in self.character_feature_ids:
            feature = FEATURE_BY_ID.get(feature_id)
            self.character_feature_listbox.insert(tk.END, feature.label if feature is not None else feature_id)
        self.character_support_gear_listbox.delete(0, tk.END)
        for support_gear_id in self.character_support_gear_ids:
            option = SUPPORT_GEAR_BY_ID.get(support_gear_id)
            self.character_support_gear_listbox.insert(tk.END, option.label if option is not None else support_gear_id)
        self.character_implant_listbox.delete(0, tk.END)
        for implant_id in self.character_implant_ids:
            self.character_implant_listbox.insert(tk.END, self._implant_label(implant_id))
        self.character_weapon_choice = pawn.weapon
        self.character_apparel_choices = list(pawn.apparel)
        self.character_apparel_listbox.delete(0, tk.END)
        for item in self.character_apparel_choices:
            self.character_apparel_listbox.insert(tk.END, self._describe_choice(item))
        self.character_weapon_summary_var.set(self._describe_choice(self.character_weapon_choice) if self.character_weapon_choice else "未选择武器")
        self._update_character_feature_status()
        self._update_character_support_gear_status()
        self._update_character_implant_status()
        self._update_character_apparel_status()
        self._sync_character_equipment_controls(self.character_weapon_choice)
        self._update_character_import_preview()
        self.status_var.set(f"已导入人物“{pawn.name}”作为新模板起点；点击“保存为新人物”时不会覆盖原记录。")
        self._refresh_character_option_list()
        self._refresh_character_firepower_preview()

    def _update_character_import_preview(self) -> None:
        if not hasattr(self, "character_saved_listbox"):
            return
        pawn = self._selected_saved_pawn_from_listbox(self.character_saved_listbox)
        if pawn is None:
            self.character_import_preview_var.set("从下方已保存人物里选中一个模板后，这里会显示完整配置；可一键导入到编辑区继续微调。")
            return
        self.character_import_preview_var.set(self._build_pawn_preview_text(pawn))

    def _selected_saved_pawns_from_listbox(self, listbox: tk.Listbox) -> list[SavedPawnTemplate]:
        displays = [listbox.get(index) for index in self._selected_indices(listbox)]
        pawns: list[SavedPawnTemplate] = []
        for display in displays:
            for pawn in self.saved_pawns:
                if self._pawn_display(pawn) == display:
                    pawns.append(pawn)
                    break
        return pawns

    def _selected_saved_pawn_from_listbox(self, listbox: tk.Listbox) -> SavedPawnTemplate | None:
        index = self._active_selected_index(listbox)
        if index is None or index >= len(listbox.get(0, tk.END)):
            return None
        display = listbox.get(index)
        for pawn in self.saved_pawns:
            if self._pawn_display(pawn) == display:
                return pawn
        return None

    def _require_single_saved_pawn(self, listbox: tk.Listbox, *, action_label: str) -> SavedPawnTemplate | None:
        pawns = self._selected_saved_pawns_from_listbox(listbox)
        if not pawns:
            messagebox.showerror("没有选择人物", f"请先选择 1 个人物，再执行“{action_label}”。")
            return None
        if len(pawns) > 1:
            messagebox.showerror("选择过多", f"“{action_label}”一次只能处理 1 个人物。")
            return None
        return pawns[0]

    def _load_selected_character_from_character_page(self) -> None:
        pawn = self._require_single_saved_pawn(self.character_saved_listbox, action_label="导入选中人物")
        if pawn is not None:
            self._load_character_into_editor(pawn)

    def _load_selected_character_from_resources(self) -> None:
        pawn = self._require_single_saved_pawn(self.resource_pawns_listbox, action_label="载入到人物创建页")
        if pawn is not None:
            self._load_character_into_editor(pawn)
            self.notebook.select(self.characters_page)

    def _selected_saved_scenarios_from_listbox(self, listbox: tk.Listbox) -> list[SavedScenarioTemplate]:
        displays = [listbox.get(index) for index in self._selected_indices(listbox)]
        scenarios: list[SavedScenarioTemplate] = []
        for display in displays:
            for scenario in self.saved_scenarios:
                if self._scenario_display(scenario) == display:
                    scenarios.append(scenario)
                    break
        return scenarios

    def _selected_saved_scenario_from_listbox(self, listbox: tk.Listbox) -> SavedScenarioTemplate | None:
        index = self._active_selected_index(listbox)
        if index is None or index >= len(listbox.get(0, tk.END)):
            return None
        display = listbox.get(index)
        for scenario in self.saved_scenarios:
            if self._scenario_display(scenario) == display:
                return scenario
        return None

    def _require_single_saved_scenario(self, listbox: tk.Listbox, *, action_label: str) -> SavedScenarioTemplate | None:
        scenarios = self._selected_saved_scenarios_from_listbox(listbox)
        if not scenarios:
            messagebox.showerror("没有选择场景", f"请先选择 1 个场景，再执行“{action_label}”。")
            return None
        if len(scenarios) > 1:
            messagebox.showerror("选择过多", f"“{action_label}”一次只能处理 1 个场景。")
            return None
        return scenarios[0]

    def _load_scenario_into_editor(self, scenario: SavedScenarioTemplate) -> None:
        self.current_scenario_id = scenario.id
        self.scenario_editor_title_var.set(f"编辑场景：{scenario.name}")
        self.scenario_name_var.set(scenario.name)
        self.scenario_attacker_ids = [scenario.attacker_pawn_id]
        self.scenario_defender_ids = [scenario.defender_pawn_id]
        self._refresh_scenario_selection_lists()
        self.scenario_distance_var.set(str(scenario.distance_cells))
        self.scenario_hit_chance_var.set(f"{scenario.hit_chance_percent:.0f}")
        self.status_var.set(f"已载入场景“{scenario.name}”。")
        self._schedule_scenario_analysis()

    def _load_selected_scenario_from_scenario_page(self) -> None:
        scenario = self._require_single_saved_scenario(self.scenario_saved_listbox, action_label="载入选中场景")
        if scenario is not None:
            self._load_scenario_into_editor(scenario)

    def _load_selected_scenario_from_resources(self) -> None:
        scenario = self._require_single_saved_scenario(self.resource_scenarios_listbox, action_label="载入到场景设计页")
        if scenario is not None:
            self._load_scenario_into_editor(scenario)
            self.notebook.select(self.scenario_page)

    def _resolve_pawn_id_from_display(self, display: str) -> str | None:
        for pawn in self.saved_pawns:
            if self._pawn_display(pawn) == display:
                return pawn.id
        return None

    def _current_record_supports_material_for_mode(self) -> bool:
        if self.catalog_index is None or self.character_mode not in {"weapon", "apparel"}:
            return False
        index = self._active_selected_index(self.character_option_listbox)
        if index is not None and index < len(self.character_option_records):
            item = self.character_option_records[index]
            if item.mode == "weapon":
                record = self.catalog_index.weapons_by_def_name.get(item.key)
                if record is not None:
                    return record.supports_material
            if item.mode == "apparel":
                record = self.catalog_index.apparel_by_def_name.get(item.key)
                if record is not None:
                    return record.supports_material
        current_choice = self.character_weapon_choice if self.character_mode == "weapon" else None
        if self.character_mode == "apparel" and self.character_apparel_choices:
            current_choice = self.character_apparel_choices[-1]
        return self._equipment_record_supports_material(current_choice)

    def _refresh_material_controls(self) -> None:
        if not hasattr(self, "character_material_label"):
            return
        show_material = self.character_mode in {"weapon", "apparel"} and self._current_record_supports_material_for_mode()
        if self.character_mode in {"weapon", "apparel"}:
            self.character_equipment_frame.grid()
        if show_material:
            self.character_material_label.grid()
            self.character_material_combo.grid()
            if not self.character_material_var.get().strip():
                self.character_material_var.set(MATERIAL_OPTIONS[1].label)
        else:
            self.character_material_label.grid_remove()
            self.character_material_combo.grid_remove()
            self.character_material_var.set("")

    def _current_scenario_pairs(self) -> list[tuple[SavedPawnTemplate, SavedPawnTemplate]]:
        pairs: list[tuple[SavedPawnTemplate, SavedPawnTemplate]] = []
        seen_pair_ids: set[tuple[str, str]] = set()
        for attacker_id in dict.fromkeys(self.scenario_attacker_ids):
            attacker = self._pawn_by_id(attacker_id)
            if attacker is None:
                continue
            for defender_id in dict.fromkeys(self.scenario_defender_ids):
                pair_ids = (attacker_id, defender_id)
                if pair_ids in seen_pair_ids:
                    continue
                defender = self._pawn_by_id(defender_id)
                if defender is None:
                    continue
                seen_pair_ids.add(pair_ids)
                pairs.append((attacker, defender))
        return pairs

    def _schedule_scenario_analysis(self) -> None:
        if self.scenario_analysis_after_id is not None:
            self.after_cancel(self.scenario_analysis_after_id)
        self.scenario_analysis_after_id = self.after(220, self._run_scenario_analysis)

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def _set_scenario_metric_defaults(self) -> None:
        for var in self.scenario_metric_vars.values():
            var.set("-")
        self.last_scenario_details = "等待有效场景。"
        self._set_text(self.scenario_details_text, self.last_scenario_details)

    def _run_scenario_analysis(self) -> None:
        self.scenario_analysis_after_id = None
        if self.catalog_index is None:
            self.scenario_status_var.set("请先去“数据导入”页导入原版数据。")
            self._set_scenario_metric_defaults()
            return
        pairs = self._current_scenario_pairs()
        if not pairs:
            self.scenario_status_var.set("请至少选择 1 名攻击方和 1 名防守方。")
            self._set_scenario_metric_defaults()
            return
        try:
            distance = max(1, int(self.scenario_distance_var.get().strip()))
            hit = float(self.scenario_hit_chance_var.get().strip())
        except ValueError:
            self.scenario_status_var.set("距离必须是整数，命中率必须是数字。")
            self._set_scenario_metric_defaults()
            return
        attacker, defender = pairs[0]
        if len(pairs) == 1:
            scenario_name = self.scenario_name_var.get().strip() or f"{attacker.name} VS {defender.name}"
        else:
            scenario_name = f"{attacker.name} VS {defender.name}"
        scenario = SavedScenarioTemplate(
            id=self.current_scenario_id or "preview-scenario",
            name=scenario_name,
            attacker_pawn_id=attacker.id,
            defender_pawn_id=defender.id,
            distance_cells=distance,
            hit_chance_percent=hit,
        )
        try:
            analysis, row = build_analysis_for_saved_scenario(scenario, {pawn.id: pawn for pawn in self.saved_pawns}, self.catalog_index)
        except Exception as exc:
            self.scenario_status_var.set(str(exc))
            self._set_scenario_metric_defaults()
            return
        if len(pairs) == 1:
            self.scenario_status_var.set("结果已按当前场景实时刷新。")
        else:
            self.scenario_status_var.set(
                f"当前共 {len(self.scenario_attacker_ids)} × {len(self.scenario_defender_ids)} 个组合，右侧先预览第一组：{attacker.name} VS {defender.name}。"
            )
        self.scenario_metric_vars["weapon"].set(row.weapon_name)
        self.scenario_metric_vars["hit"].set(f"{row.hit_chance_percent:.2f}%")
        self.scenario_metric_vars["expected_dps"].set(f"{row.expected_dps:.4f}")
        self.scenario_metric_vars["theoretical_dps"].set(f"{row.theoretical_dps:.4f}")
        self.scenario_metric_vars["damage_on_hit"].set(f"{row.expected_damage_on_hit:.4f}")
        self.scenario_metric_vars["armor_reduction"].set(f"{row.armor_reduction_percent:.2f}%")
        self.scenario_metric_vars["taken_multiplier"].set(f"{row.damage_taken_multiplier:.4f}")
        self.scenario_metric_vars["distance"].set(str(row.distance_cells))
        self.scenario_metric_vars["wearable"].set("合法" if row.outfit_valid else "冲突")
        self.last_scenario_details = (
            f"攻击方：{row.attacker_name}\n防守方：{row.defender_name}\n武器：{row.weapon_name}\n"
            f"最终命中率：{row.hit_chance_percent:.2f}%\n期望DPS：{row.expected_dps:.4f}\n理论DPS：{row.theoretical_dps:.4f}\n"
            f"命中期望伤害：{row.expected_damage_on_hit:.4f}\n护甲减伤率：{row.armor_reduction_percent:.2f}%\n"
            f"承伤倍率：{row.damage_taken_multiplier:.4f}\n穿戴合法：{'是' if row.outfit_valid else '否'}"
        )
        self._set_text(self.scenario_details_text, self.last_scenario_details)

    def _save_scenario(self) -> None:
        pairs = self._current_scenario_pairs()
        if not pairs:
            messagebox.showerror("缺少人物", "请至少选择 1 名攻击方和 1 名防守方。")
            return
        try:
            distance = max(1, int(self.scenario_distance_var.get().strip()))
            hit = float(self.scenario_hit_chance_var.get().strip())
        except ValueError:
            messagebox.showerror("输入错误", "距离必须是整数，命中率必须是数字。")
            return
        if len(pairs) == 1:
            attacker, defender = pairs[0]
            name = self.scenario_name_var.get().strip() or f"{attacker.name} VS {defender.name}"
            existing = self.store.find_scenario_by_signature(
                attacker_pawn_id=attacker.id,
                defender_pawn_id=defender.id,
                distance_cells=distance,
                hit_chance_percent=hit,
                exclude_id=self.current_scenario_id,
            )
            if existing is not None and self.current_scenario_id is None:
                self.current_scenario_id = existing.id
                self.scenario_editor_title_var.set(f"编辑场景：{existing.name}")
                self._refresh_saved_data()
                self.scenario_status_var.set(f"同条件场景“{existing.name}”已存在，未重复保存。")
                self.status_var.set(f"检测到已存在场景“{existing.name}”，本次未重复生成。")
                return
            if existing is not None and self.current_scenario_id is not None:
                messagebox.showerror(
                    "场景重复",
                    "已存在另一条相同攻防组合且距离、命中率相同的场景。请直接使用已有场景，或修改参数后再保存。",
                )
                return
            scenario = SavedScenarioTemplate(
                id=self.current_scenario_id or self.store.make_id(name),
                name=name,
                attacker_pawn_id=attacker.id,
                defender_pawn_id=defender.id,
                distance_cells=distance,
                hit_chance_percent=hit,
            )
            saved = self.store.save_scenario(scenario)
            self.current_scenario_id = saved.id
            self.scenario_editor_title_var.set(f"编辑场景：{saved.name}")
            self._refresh_saved_data()
            self.scenario_status_var.set(f"场景“{saved.name}”已保存。")
            self.status_var.set(f"场景“{saved.name}”已保存。")
            return
        saved_count = 0
        skipped_count = 0
        for attacker, defender in pairs:
            existing = self.store.find_scenario_by_signature(
                attacker_pawn_id=attacker.id,
                defender_pawn_id=defender.id,
                distance_cells=distance,
                hit_chance_percent=hit,
            )
            if existing is not None:
                skipped_count += 1
                continue
            auto_name = f"{attacker.name} VS {defender.name}"
            scenario = SavedScenarioTemplate(
                id=self.store.make_id(auto_name),
                name=auto_name,
                attacker_pawn_id=attacker.id,
                defender_pawn_id=defender.id,
                distance_cells=distance,
                hit_chance_percent=hit,
            )
            self.store.save_scenario(scenario)
            saved_count += 1
        self.current_scenario_id = None
        self.scenario_editor_title_var.set("新建场景")
        self._refresh_saved_data()
        if skipped_count > 0 and saved_count > 0:
            self.scenario_status_var.set(f"已新增 {saved_count} 个唯一场景，跳过 {skipped_count} 个重复组合。")
            self.status_var.set(f"批量场景已生成：新增 {saved_count}，跳过重复 {skipped_count}。")
        elif skipped_count > 0:
            self.scenario_status_var.set(f"当前这组攻防场景已全部存在，未重复生成。共跳过 {skipped_count} 个组合。")
            self.status_var.set(f"未生成新场景：{skipped_count} 个组合已存在。")
        else:
            self.scenario_status_var.set(f"已批量保存 {saved_count} 个唯一场景。")
            self.status_var.set(f"已批量保存 {saved_count} 个唯一场景。")

    def _reset_scenario_editor(self) -> None:
        self.current_scenario_id = None
        self.scenario_editor_title_var.set("新建场景")
        self.scenario_name_var.set("")
        self.scenario_attacker_ids = []
        self.scenario_defender_ids = []
        self.scenario_distance_var.set("12")
        self.scenario_hit_chance_var.set("100")
        self._refresh_scenario_selection_lists()
        self._set_scenario_picker_mode("attacker")
        self.scenario_status_var.set("请选择双方人物模板。")
        self._set_scenario_metric_defaults()
        self.status_var.set("场景编辑器已重置。")

    def _comparison_rows_for_scenarios(self, scenarios: list[SavedScenarioTemplate]) -> list[ComparisonRow]:
        if self.catalog_index is None:
            raise ValueError("请先导入原版数据。")
        pawn_map = {pawn.id: pawn for pawn in self.saved_pawns}
        rows: list[ComparisonRow] = []
        for scenario in scenarios:
            _analysis, row = build_analysis_for_saved_scenario(scenario, pawn_map, self.catalog_index)
            rows.append(row)
        return rows

    def _selected_compare_scenarios(self) -> list[SavedScenarioTemplate]:
        displays = [self.compare_source_listbox.get(index) for index in self.compare_source_listbox.curselection()]
        scenarios: list[SavedScenarioTemplate] = []
        for display in displays:
            for scenario in self.saved_scenarios:
                if self._scenario_display(scenario) == display:
                    scenarios.append(scenario)
                    break
        return scenarios

    def _scenario_from_compare_source_index(self, index: int) -> SavedScenarioTemplate | None:
        if index < 0 or index >= self.compare_source_listbox.size():
            return None
        display = self.compare_source_listbox.get(index)
        for scenario in self.saved_scenarios:
            if self._scenario_display(scenario) == display:
                return scenario
        return None

    def _merge_compare_rows(self, new_rows: list[ComparisonRow]) -> None:
        by_id = {row.scenario_id: row for row in self.compare_rows}
        for row in new_rows:
            by_id[row.scenario_id] = row
        self.compare_rows = list(by_id.values())
        self._apply_compare_sort()
        self._refresh_compare_table()

    def _analyze_selected_compare_scenarios(self) -> None:
        scenarios = self._selected_compare_scenarios()
        if not scenarios:
            messagebox.showerror("没有选择场景", "请先在左侧场景列表中选择至少一个场景。")
            return
        try:
            rows = self._comparison_rows_for_scenarios(scenarios)
        except Exception as exc:
            messagebox.showerror("计算失败", str(exc))
            return
        self._merge_compare_rows(rows)
        self.compare_status_var.set(f"已将 {len(rows)} 个场景加入对比表。")
        self.status_var.set("结果对比表已刷新。")

    def _analyze_compare_scenario_at_index(self, index: int) -> None:
        scenario = self._scenario_from_compare_source_index(index)
        if scenario is None:
            return
        try:
            rows = self._comparison_rows_for_scenarios([scenario])
        except Exception as exc:
            messagebox.showerror("计算失败", str(exc))
            return
        self._merge_compare_rows(rows)
        self.compare_status_var.set(f"已将场景“{scenario.name}”加入对比表。")
        self.status_var.set("结果对比表已刷新。")

    def _analyze_all_compare_scenarios(self) -> None:
        if not self.saved_scenarios:
            messagebox.showerror("没有场景", "当前还没有任何已保存场景。")
            return
        try:
            rows = self._comparison_rows_for_scenarios(self.saved_scenarios)
        except Exception as exc:
            messagebox.showerror("计算失败", str(exc))
            return
        self.compare_rows = rows
        self._apply_compare_sort()
        self._refresh_compare_table()
        self.compare_status_var.set(f"已分析全部 {len(rows)} 个场景。")
        self.status_var.set("全部场景的对比结果已生成。")

    def _clear_compare_rows(self) -> None:
        self.compare_rows = []
        self._refresh_compare_table()
        self.compare_status_var.set("对比表已清空。")

    def _save_compare_rows(self) -> None:
        if not self.compare_rows:
            messagebox.showerror("没有结果", "请先生成至少一条对比结果。")
            return
        output = self.store.save_result_rows(self.compare_rows, label="comparison-results")
        self.status_var.set("对比结果已自动保存到应用数据目录。")
        messagebox.showinfo("保存完成", f"本次结果已保存。\n{output}")

    def _refresh_compare_table(self) -> None:
        self.compare_tree.delete(*self.compare_tree.get_children())
        for row in self.compare_rows:
            values = []
            for key, _label, _width in self.compare_columns:
                raw = getattr(row, key)
                if key == "outfit_valid":
                    values.append("是" if raw else "否")
                elif isinstance(raw, float):
                    values.append(f"{raw:.2f}" if key.endswith("percent") else f"{raw:.4f}")
                else:
                    values.append(raw)
            self.compare_tree.insert("", tk.END, values=values)

    def _sort_compare_rows(self, column: str) -> None:
        if self.compare_sort_column == column:
            self.compare_sort_reverse = not self.compare_sort_reverse
        else:
            self.compare_sort_column = column
            self.compare_sort_reverse = False
        self._apply_compare_sort()
        self._refresh_compare_table()

    def _apply_compare_sort(self) -> None:
        key = self.compare_sort_column
        self.compare_rows.sort(key=lambda row: getattr(row, key), reverse=self.compare_sort_reverse)

    def _update_resource_pawn_preview(self) -> None:
        pawn = self._selected_saved_pawn_from_listbox(self.resource_pawns_listbox)
        if pawn is None:
            self.resource_pawn_preview.configure(text="选择左侧人物后，这里会显示详情。")
            return
        self.resource_pawn_preview.configure(text=self._build_pawn_preview_text(pawn))

    def _update_resource_scenario_preview(self) -> None:
        scenario = self._selected_saved_scenario_from_listbox(self.resource_scenarios_listbox)
        if scenario is None:
            self.resource_scenario_preview.configure(text="选择左侧场景后，这里会显示详情。")
            return
        attacker = next((pawn for pawn in self.saved_pawns if pawn.id == scenario.attacker_pawn_id), None)
        defender = next((pawn for pawn in self.saved_pawns if pawn.id == scenario.defender_pawn_id), None)
        preview = [f"场景名称：{scenario.name}", f"攻击方：{attacker.name if attacker else scenario.attacker_pawn_id}", f"防守方：{defender.name if defender else scenario.defender_pawn_id}", f"距离：{scenario.distance_cells}", f"最终命中率%：{scenario.hit_chance_percent:.0f}"]
        self.resource_scenario_preview.configure(text="\n".join(preview))

    def _delete_selected_pawn(self) -> None:
        pawns = self._selected_saved_pawns_from_listbox(self.resource_pawns_listbox)
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
                self.store.delete_pawn(pawn.id)
                deleted_count += 1
            except Exception as exc:
                failures.append(f"{pawn.name}：{exc}")
        self._refresh_saved_data()
        if deleted_count > 0:
            self.status_var.set(f"已删除 {deleted_count} 个人物。")
        if failures:
            messagebox.showerror("部分人物无法删除", "\n".join(failures))

    def _delete_selected_scenario(self) -> None:
        scenarios = self._selected_saved_scenarios_from_listbox(self.resource_scenarios_listbox)
        if not scenarios:
            return
        if len(scenarios) == 1:
            prompt = f"要删除场景“{scenarios[0].name}”吗？"
        else:
            prompt = f"要删除选中的 {len(scenarios)} 个场景吗？"
        if not messagebox.askyesno("确认删除", prompt):
            return
        for scenario in scenarios:
            self.store.delete_scenario(scenario.id)
        self._refresh_saved_data()
        self.status_var.set(f"已删除 {len(scenarios)} 个场景。")


def main() -> int:
    app = RimDataAnalysisDesktopApp()
    app.mainloop()
    return 0

