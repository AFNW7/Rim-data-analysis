from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from rim_data_analysis.user_app_data import (
    SavedPawnTemplate,
    SavedScenarioTemplate,
    build_analysis_for_saved_scenario,
)


class ScenarioEditorMixin:
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

        flow_card = tk.Frame(sidebar, bg=self.colors["panel_alt"], padx=12, pady=12, highlightthickness=1, highlightbackground=self.colors["line"])
        flow_card.pack(fill="x", pady=(14, 0))
        tk.Label(flow_card, text="当前步骤", bg=self.colors["panel_alt"], fg=self.colors["accent"], font=("Bahnschrift", 12, "bold")).pack(anchor="w")
        tk.Label(flow_card, textvariable=self.scenario_flow_var, bg=self.colors["panel_alt"], fg=self.colors["ink"], justify="left", wraplength=300, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(6, 10))
        self.scenario_to_characters_button = ttk.Button(flow_card, text="返回人物创建", style="Subtle.TButton", command=lambda: self.notebook.select(self.characters_page))
        self.scenario_to_characters_button.pack(fill="x", pady=(0, 6))
        self.scenario_to_compare_button = ttk.Button(flow_card, text="下一步：去结果对比", style="Primary.TButton", command=self._go_to_compare_page)
        self.scenario_to_compare_button.pack(fill="x")

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
