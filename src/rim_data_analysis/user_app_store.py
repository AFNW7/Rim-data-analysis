from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from rim_data_analysis.user_app_models import (
    ComparisonRow,
    ImportSettings,
    SavedPawnTemplate,
    SavedScenarioTemplate,
)


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    ascii_only = lowered.encode("ascii", errors="ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return normalized or "preset"


def _timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _nonce_slug() -> str:
    return uuid4().hex[:8]


def _normalize_distance_cells(value: int | float) -> int:
    return max(1, int(value))


def _normalize_hit_chance_percent(value: int | float) -> float:
    return round(max(0.0, min(float(value), 200.0)), 6)


def _scenario_signature(
    attacker_pawn_id: str,
    defender_pawn_id: str,
    distance_cells: int | float,
    hit_chance_percent: int | float,
) -> tuple[str, str, int, float]:
    return (
        str(attacker_pawn_id),
        str(defender_pawn_id),
        _normalize_distance_cells(distance_cells),
        _normalize_hit_chance_percent(hit_chance_percent),
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 根节点必须是对象: {path}")
    return payload


def default_app_data_root() -> Path:
    override = os.getenv("RIM_DATA_ANALYSIS_APP_STATE_DIR")
    if override:
        return Path(override).expanduser()
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "RimDataAnalysis"
    return Path.home() / ".rim-data-analysis"


def _migrate_legacy_state(legacy_root: Path, target_root: Path) -> None:
    if target_root.exists() or not legacy_root.exists():
        return
    target_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(legacy_root, target_root)


class UserAppStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.pawns_dir = self.root / "pawns"
        self.scenarios_dir = self.root / "scenarios"
        self.results_dir = self.root / "results"
        self.settings_dir = self.root / "settings"
        for path in (
            self.root,
            self.pawns_dir,
            self.scenarios_dir,
            self.results_dir,
            self.settings_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def for_repo(cls, repo_root: Path) -> "UserAppStore":
        root = default_app_data_root()
        _migrate_legacy_state(repo_root / "artifacts" / "app-state", root)
        return cls(root)

    def _pawn_path(self, template_id: str) -> Path:
        return self.pawns_dir / f"{template_id}.json"

    def _scenario_path(self, template_id: str) -> Path:
        return self.scenarios_dir / f"{template_id}.json"

    def _settings_path(self) -> Path:
        return self.settings_dir / "import-settings.json"

    def list_pawns(self) -> list[SavedPawnTemplate]:
        return sorted(
            [SavedPawnTemplate.from_dict(_read_json(path)) for path in self.pawns_dir.glob("*.json")],
            key=lambda item: item.name.lower(),
        )

    def load_pawn(self, template_id: str) -> SavedPawnTemplate:
        return SavedPawnTemplate.from_dict(_read_json(self._pawn_path(template_id)))

    def save_pawn(self, pawn: SavedPawnTemplate) -> SavedPawnTemplate:
        normalized = SavedPawnTemplate(
            id=pawn.id or self.make_id(pawn.name),
            name=pawn.name.strip() or "未命名人物",
            species_id=pawn.species_id,
            feature_ids=list(pawn.feature_ids),
            support_gear_ids=list(pawn.support_gear_ids),
            implant_ids=list(pawn.implant_ids),
            shooting_skill=max(0, min(int(pawn.shooting_skill), 20)),
            melee_skill=max(0, min(int(pawn.melee_skill), 20)),
            full_body_armor_percent=max(0.0, min(float(pawn.full_body_armor_percent), 200.0)),
            weapon=pawn.weapon,
            apparel=list(pawn.apparel),
        )
        _write_json(self._pawn_path(normalized.id), normalized.to_dict())
        return normalized

    def delete_pawn(self, template_id: str) -> None:
        dependencies = [item for item in self.list_scenarios() if template_id in {item.attacker_pawn_id, item.defender_pawn_id}]
        if dependencies:
            names = "、".join(item.name for item in dependencies[:3])
            raise ValueError(f"该人物已被场景使用：{names}")
        self._pawn_path(template_id).unlink(missing_ok=True)

    def rename_pawn(self, template_id: str, new_name: str) -> SavedPawnTemplate:
        pawn = self.load_pawn(template_id)
        renamed = SavedPawnTemplate(
            id=pawn.id,
            name=new_name.strip() or pawn.name,
            species_id=pawn.species_id,
            feature_ids=list(pawn.feature_ids),
            support_gear_ids=list(pawn.support_gear_ids),
            implant_ids=list(pawn.implant_ids),
            shooting_skill=pawn.shooting_skill,
            melee_skill=pawn.melee_skill,
            full_body_armor_percent=pawn.full_body_armor_percent,
            weapon=pawn.weapon,
            apparel=list(pawn.apparel),
        )
        return self.save_pawn(renamed)

    def list_scenarios(self) -> list[SavedScenarioTemplate]:
        return sorted(
            [SavedScenarioTemplate.from_dict(_read_json(path)) for path in self.scenarios_dir.glob("*.json")],
            key=lambda item: item.name.lower(),
        )

    def load_scenario(self, template_id: str) -> SavedScenarioTemplate:
        return SavedScenarioTemplate.from_dict(_read_json(self._scenario_path(template_id)))

    def scenario_signature(self, scenario: SavedScenarioTemplate) -> tuple[str, str, int, float]:
        return _scenario_signature(
            scenario.attacker_pawn_id,
            scenario.defender_pawn_id,
            scenario.distance_cells,
            scenario.hit_chance_percent,
        )

    def find_scenario_by_signature(
        self,
        *,
        attacker_pawn_id: str,
        defender_pawn_id: str,
        distance_cells: int | float,
        hit_chance_percent: int | float,
        exclude_id: str | None = None,
    ) -> SavedScenarioTemplate | None:
        expected = _scenario_signature(
            attacker_pawn_id,
            defender_pawn_id,
            distance_cells,
            hit_chance_percent,
        )
        for item in self.list_scenarios():
            if exclude_id is not None and item.id == exclude_id:
                continue
            if self.scenario_signature(item) == expected:
                return item
        return None

    def save_scenario(self, scenario: SavedScenarioTemplate) -> SavedScenarioTemplate:
        normalized = SavedScenarioTemplate(
            id=scenario.id or self.make_id(scenario.name),
            name=scenario.name.strip() or "未命名场景",
            attacker_pawn_id=scenario.attacker_pawn_id,
            defender_pawn_id=scenario.defender_pawn_id,
            distance_cells=_normalize_distance_cells(scenario.distance_cells),
            hit_chance_percent=_normalize_hit_chance_percent(scenario.hit_chance_percent),
        )
        _write_json(self._scenario_path(normalized.id), normalized.to_dict())
        return normalized

    def delete_scenario(self, template_id: str) -> None:
        self._scenario_path(template_id).unlink(missing_ok=True)

    def rename_scenario(self, template_id: str, new_name: str) -> SavedScenarioTemplate:
        scenario = self.load_scenario(template_id)
        renamed = SavedScenarioTemplate(
            id=scenario.id,
            name=new_name.strip() or scenario.name,
            attacker_pawn_id=scenario.attacker_pawn_id,
            defender_pawn_id=scenario.defender_pawn_id,
            distance_cells=scenario.distance_cells,
            hit_chance_percent=scenario.hit_chance_percent,
        )
        return self.save_scenario(renamed)

    def delete_duplicate_scenarios(self) -> int:
        seen_signatures: set[tuple[str, str, int, float]] = set()
        deleted_count = 0
        for scenario in self.list_scenarios():
            signature = self.scenario_signature(scenario)
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                continue
            self.delete_scenario(scenario.id)
            deleted_count += 1
        return deleted_count

    def load_import_settings(self) -> ImportSettings:
        path = self._settings_path()
        if not path.exists():
            return ImportSettings()
        return ImportSettings.from_dict(_read_json(path))

    def save_import_settings(self, settings: ImportSettings) -> ImportSettings:
        normalized = ImportSettings(
            game_data_root=settings.game_data_root.strip(),
            workshop_root=settings.workshop_root.strip(),
            catalog_weapon_count=max(0, int(settings.catalog_weapon_count)),
            catalog_apparel_count=max(0, int(settings.catalog_apparel_count)),
            catalog_implant_count=max(0, int(settings.catalog_implant_count)),
            last_imported_at=settings.last_imported_at.strip(),
        )
        _write_json(self._settings_path(), normalized.to_dict())
        return normalized

    def save_result_rows(self, rows: list[ComparisonRow], *, label: str) -> Path:
        payload = {
            "label": label,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "rows": [row.to_dict() for row in rows],
        }
        output_path = self.results_dir / f"{_timestamp_slug()}-{_slugify(label)}-{_nonce_slug()}.json"
        _write_json(output_path, payload)
        return output_path

    def make_id(self, name: str) -> str:
        base = _slugify(name)
        candidate = f"{base}-{_timestamp_slug()}-{_nonce_slug()}"
        return candidate
