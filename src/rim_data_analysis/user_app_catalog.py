from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rim_data_analysis.vanilla_models import (
    VanillaApparelRecord,
    VanillaCatalog,
    VanillaImplantRecord,
    VanillaWeaponRecord,
)
from rim_data_analysis.vanilla_parser import build_vanilla_catalog


@dataclass(slots=True)
class CatalogIndex:
    catalog: VanillaCatalog
    weapons_by_def_name: dict[str, VanillaWeaponRecord]
    apparel_by_def_name: dict[str, VanillaApparelRecord]
    implants_by_def_name: dict[str, VanillaImplantRecord]

    @classmethod
    def from_catalog(cls, catalog: VanillaCatalog) -> "CatalogIndex":
        return cls(
            catalog=catalog,
            weapons_by_def_name={item.def_name: item for item in catalog.weapons},
            apparel_by_def_name={item.def_name: item for item in catalog.apparel},
            implants_by_def_name={item.def_name: item for item in catalog.implants},
        )

    def search_weapons(self, query: str, *, attack_mode: str | None = None) -> list[VanillaWeaponRecord]:
        normalized = query.strip().lower()
        records = self.catalog.weapons
        if attack_mode and attack_mode != "all":
            records = [item for item in records if item.attack_mode == attack_mode]
        if not normalized:
            return records
        return [
            item
            for item in records
            if normalized in item.label.lower()
            or normalized in item.display_label.lower()
            or normalized in item.def_name.lower()
        ]

    def search_apparel(self, query: str) -> list[VanillaApparelRecord]:
        normalized = query.strip().lower()
        if not normalized:
            return self.catalog.apparel
        return [
            item
            for item in self.catalog.apparel
            if normalized in item.label.lower()
            or normalized in item.display_label.lower()
            or normalized in item.def_name.lower()
        ]

    def search_implants(self, query: str) -> list[VanillaImplantRecord]:
        normalized = query.strip().lower()
        if not normalized:
            return self.catalog.implants
        return [
            item
            for item in self.catalog.implants
            if normalized in item.label.lower()
            or normalized in item.display_label.lower()
            or normalized in item.def_name.lower()
        ]


def load_catalog_index(game_data_root: Path) -> CatalogIndex:
    return CatalogIndex.from_catalog(build_vanilla_catalog(game_data_root))
