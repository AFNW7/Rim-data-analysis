from __future__ import annotations

from pathlib import Path

import tkinter as tk
from tkinter import font, messagebox, ttk

from rim_data_analysis import desktop_user_app_pages
from rim_data_analysis.desktop_user_app_character import CharacterEditorMixin
from rim_data_analysis.desktop_user_app_scenario import ScenarioEditorMixin
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
    SavedPawnTemplate,
    SavedScenarioTemplate,
    SpeciesOption,
    UserAppStore,
    build_analysis_for_saved_scenario,
    build_firepower_preview_for_pawn,
    describe_modifier_payload,
    describe_equipment,
    humanlike_species_ids,
)






class RimDataAnalysisDesktopApp(CharacterEditorMixin, ScenarioEditorMixin, tk.Tk):
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
        self.status_var = tk.StringVar(value="应用已就绪。第一次使用请先到“数据导入”页导入原版数据。")

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
        self.character_flow_var = tk.StringVar(value="第 2 步：导入原版数据后，在这里保存人物模板。")
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
        self.scenario_flow_var = tk.StringVar(value="第 3 步：先准备人物，再在这里保存场景。")
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
        self.compare_flow_var = tk.StringVar(value="第 4 步：在这里把已保存场景加入对比表并查看结果。")
        self.compare_summary_var = tk.StringVar(value="加入场景后，这里会直接给出最高 DPS、最高命中率和护甲衰减最明显的场景。")

        self.import_game_data_var = tk.StringVar()
        self.import_workshop_var = tk.StringVar()
        self.import_status_var = tk.StringVar(value="第一版仅支持原版游戏数据导入。")
        self.import_flow_var = tk.StringVar(value="第 1 步：先导入 RimWorld 原版数据，然后再开始创建人物。")
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


    def _build_scenario_page(self) -> None:
        ScenarioEditorMixin._build_scenario_page(self)

    def _build_compare_page(self) -> None:
        desktop_user_app_pages.build_compare_page(self)

    def _build_import_page(self) -> None:
        desktop_user_app_pages.build_import_page(self)

    def _build_resources_page(self) -> None:
        desktop_user_app_pages.build_resources_page(self)

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
            self.notebook.select(self.characters_page)
        else:
            self._refresh_import_previews()
            self.notebook.select(self.import_page)
            self.status_var.set("第一次使用请先在“数据导入”页选择 RimWorld 目录，然后点击“导入原版数据”。")
        self._refresh_workflow_guidance()

    def _auto_detect_paths(self) -> None:
        desktop_user_app_pages.auto_detect_paths(self)

    def _browse_game_data_root(self) -> None:
        desktop_user_app_pages.browse_game_data_root(self)

    def _browse_workshop_root(self) -> None:
        desktop_user_app_pages.browse_workshop_root(self)

    def _import_catalog(self) -> None:
        desktop_user_app_pages.import_catalog(self)

    def _load_catalog_from_settings(self, *, show_success: bool) -> None:
        desktop_user_app_pages.load_catalog_from_settings(self, show_success=show_success)

    def _resolve_game_data_root(self, raw_path: str) -> tuple[Path | None, str | None, str | None]:
        return desktop_user_app_pages.resolve_game_data_root(self, raw_path)

    def _update_import_summary(self) -> None:
        desktop_user_app_pages.update_import_summary(self)

    def _refresh_import_previews(self) -> None:
        desktop_user_app_pages.refresh_import_previews(self)

    def _refresh_saved_data(self) -> None:
        self.saved_pawns = self.store.list_pawns()
        self.saved_scenarios = self.store.list_scenarios()
        self._refresh_character_saved_list()
        self._refresh_scenario_saved_list()
        self._refresh_scenario_selection_lists()
        self._refresh_scenario_picker_list()
        self._refresh_compare_source_list()
        self._refresh_resource_lists()
        self._refresh_workflow_guidance()

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











    def _refresh_compare_source_list(self) -> None:
        desktop_user_app_pages.refresh_compare_source_list(self)

    def _refresh_resource_lists(self) -> None:
        desktop_user_app_pages.refresh_resource_lists(self)

    def _refresh_workflow_guidance(self) -> None:
        imported = self.catalog_index is not None
        pawn_count = len(self.saved_pawns)
        scenario_count = len(self.saved_scenarios)
        compare_count = len(self.compare_rows)

        if imported:
            self.import_flow_var.set(
                f"第 1 步已完成：已导入原版数据，共载入 {len(self.catalog_index.catalog.weapons)} 个武器、"
                f"{len(self.catalog_index.catalog.apparel)} 件衣着、{len(self.catalog_index.catalog.implants)} 个植入体。"
            )
            self.import_to_characters_button.configure(state="normal")
        else:
            self.import_flow_var.set("第 1 步：先导入 RimWorld 原版数据。完成后人物创建、场景设计和结果对比页会自动可用。")
            self.import_to_characters_button.configure(state="disabled")

        if not imported:
            self.character_flow_var.set("当前还没有导入原版数据。请先回到“数据导入”页完成第 1 步。")
            self.character_to_import_button.configure(state="normal")
            self.character_to_scenario_button.configure(state="disabled")
        elif pawn_count == 0:
            self.character_flow_var.set("第 2 步：先保存至少 1 个人物模板。保存后可以继续补更多人物，也可以前往“场景设计”开始配对测试。")
            self.character_to_import_button.configure(state="normal")
            self.character_to_scenario_button.configure(state="disabled")
        else:
            self.character_flow_var.set(
                f"第 2 步进行中：当前已保存 {pawn_count} 个人物模板。可以继续补人物，或前往“场景设计”把它们组合成测试场景。"
            )
            self.character_to_import_button.configure(state="normal")
            self.character_to_scenario_button.configure(state="normal")

        if not imported:
            self.scenario_flow_var.set("当前还没有导入原版数据。请先完成第 1 步。")
            self.scenario_to_characters_button.configure(state="normal")
            self.scenario_to_compare_button.configure(state="disabled")
        elif pawn_count == 0:
            self.scenario_flow_var.set("当前还没有已保存人物。请先去“人物创建”页保存攻击方或防守方模板。")
            self.scenario_to_characters_button.configure(state="normal")
            self.scenario_to_compare_button.configure(state="disabled")
        elif scenario_count == 0:
            self.scenario_flow_var.set("第 3 步：从已保存人物中选择攻击方和防守方，保存 1 个或多个测试场景。")
            self.scenario_to_characters_button.configure(state="normal")
            self.scenario_to_compare_button.configure(state="disabled")
        else:
            self.scenario_flow_var.set(
                f"第 3 步进行中：当前已保存 {scenario_count} 个场景。你可以继续补场景，或前往“结果对比”查看横向结果。"
            )
            self.scenario_to_characters_button.configure(state="normal")
            self.scenario_to_compare_button.configure(state="normal")

        if not imported:
            self.compare_flow_var.set("当前还没有导入原版数据。请先完成第 1 步，然后再创建人物和场景。")
            self.compare_to_scenario_button.configure(state="normal")
        elif scenario_count == 0:
            self.compare_flow_var.set("当前还没有已保存场景。请先去“场景设计”页保存至少 1 个场景。")
            self.compare_to_scenario_button.configure(state="normal")
        elif compare_count == 0:
            self.compare_flow_var.set(
                f"第 4 步：当前已保存 {scenario_count} 个场景。先从左侧加入场景到右侧对比表，再按列排序比较输出和承伤能力。"
            )
            self.compare_to_scenario_button.configure(state="normal")
        else:
            self.compare_flow_var.set(
                f"第 4 步进行中：当前对比表里有 {compare_count} 条结果，已保存场景 {scenario_count} 个。可以继续加入更多场景，或保存本次结果。"
            )
            self.compare_to_scenario_button.configure(state="normal")

    def _go_to_characters_page(self) -> None:
        if self.catalog_index is None:
            messagebox.showerror("尚未导入数据", "请先在“数据导入”页完成原版数据导入。")
            self.notebook.select(self.import_page)
            return
        self.notebook.select(self.characters_page)

    def _go_to_scenario_page(self) -> None:
        if self.catalog_index is None:
            messagebox.showerror("尚未导入数据", "请先在“数据导入”页完成原版数据导入。")
            self.notebook.select(self.import_page)
            return
        if not self.saved_pawns:
            messagebox.showerror("还没有人物", "请先在“人物创建”页保存至少 1 个人物模板。")
            self.notebook.select(self.characters_page)
            return
        self.notebook.select(self.scenario_page)

    def _go_to_compare_page(self) -> None:
        if self.catalog_index is None:
            messagebox.showerror("尚未导入数据", "请先在“数据导入”页完成原版数据导入。")
            self.notebook.select(self.import_page)
            return
        if not self.saved_scenarios:
            messagebox.showerror("还没有场景", "请先在“场景设计”页保存至少 1 个场景。")
            self.notebook.select(self.scenario_page)
            return
        self.notebook.select(self.compare_page)




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


    def _load_selected_character_from_resources(self) -> None:
        desktop_user_app_pages.load_selected_character_from_resources(self)

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

    def _load_selected_scenario_from_resources(self) -> None:
        desktop_user_app_pages.load_selected_scenario_from_resources(self)

    def _resolve_pawn_id_from_display(self, display: str) -> str | None:
        for pawn in self.saved_pawns:
            if self._pawn_display(pawn) == display:
                return pawn.id
        return None



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
        return desktop_user_app_pages.selected_compare_scenarios(self)

    def _scenario_from_compare_source_index(self, index: int) -> SavedScenarioTemplate | None:
        return desktop_user_app_pages.scenario_from_compare_source_index(self, index)

    def _merge_compare_rows(self, new_rows: list[ComparisonRow]) -> None:
        desktop_user_app_pages.merge_compare_rows(self, new_rows)

    def _analyze_selected_compare_scenarios(self) -> None:
        desktop_user_app_pages.analyze_selected_compare_scenarios(self)

    def _analyze_compare_scenario_at_index(self, index: int) -> None:
        desktop_user_app_pages.analyze_compare_scenario_at_index(self, index)

    def _analyze_all_compare_scenarios(self) -> None:
        desktop_user_app_pages.analyze_all_compare_scenarios(self)

    def _clear_compare_rows(self) -> None:
        desktop_user_app_pages.clear_compare_rows(self)

    def _save_compare_rows(self) -> None:
        desktop_user_app_pages.save_compare_rows(self)

    def _refresh_compare_table(self) -> None:
        desktop_user_app_pages.refresh_compare_table(self)

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
        desktop_user_app_pages.update_resource_pawn_preview(self)

    def _update_resource_scenario_preview(self) -> None:
        desktop_user_app_pages.update_resource_scenario_preview(self)

    def _delete_selected_pawn(self) -> None:
        desktop_user_app_pages.delete_selected_pawn(self)

    def _delete_selected_scenario(self) -> None:
        desktop_user_app_pages.delete_selected_scenario(self)

    def _rename_selected_pawn(self) -> None:
        desktop_user_app_pages.rename_selected_pawn(self)

    def _rename_selected_scenario(self) -> None:
        desktop_user_app_pages.rename_selected_scenario(self)

    def _cleanup_duplicate_scenarios(self) -> None:
        desktop_user_app_pages.cleanup_duplicate_scenarios(self)


def main() -> int:
    app = RimDataAnalysisDesktopApp()
    app.mainloop()
    return 0

