from __future__ import annotations

from dataclasses import dataclass

import tkinter as tk
from tkinter import messagebox, ttk

from rim_data_analysis.user_app_data import (
    EquipmentChoice,
    FEATURE_BY_ID,
    FEATURE_OPTIONS,
    IMPLANT_OPTIONS,
    MATERIAL_OPTIONS,
    QUALITY_OPTIONS,
    SPECIES_BY_ID,
    SPECIES_OPTIONS,
    SUPPORT_GEAR_BY_ID,
    SUPPORT_GEAR_OPTIONS,
    SavedPawnTemplate,
    SpeciesOption,
    build_firepower_preview_for_pawn,
    describe_modifier_payload,
    humanlike_species_ids,
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


class CharacterEditorMixin:
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

        flow_card = tk.Frame(sidebar, bg=self.colors["panel_alt"], padx=12, pady=12, highlightthickness=1, highlightbackground=self.colors["line"])
        flow_card.pack(fill="x", pady=(14, 0))
        tk.Label(flow_card, text="当前步骤", bg=self.colors["panel_alt"], fg=self.colors["accent"], font=("Bahnschrift", 12, "bold")).pack(anchor="w")
        tk.Label(flow_card, textvariable=self.character_flow_var, bg=self.colors["panel_alt"], fg=self.colors["ink"], justify="left", wraplength=300, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 10))
        self.character_to_import_button = ttk.Button(flow_card, text="返回数据导入", style="Subtle.TButton", command=lambda: self.notebook.select(self.import_page))
        self.character_to_import_button.pack(fill="x", pady=(0, 6))
        self.character_to_scenario_button = ttk.Button(flow_card, text="下一步：去场景设计", style="Primary.TButton", command=self._go_to_scenario_page)
        self.character_to_scenario_button.pack(fill="x")

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

    def _load_selected_character_from_character_page(self) -> None:
        pawn = self._require_single_saved_pawn(self.character_saved_listbox, action_label="导入选中人物")
        if pawn is not None:
            self._load_character_into_editor(pawn)

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
