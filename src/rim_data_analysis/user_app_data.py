from __future__ import annotations

from rim_data_analysis.user_app_analysis import (
    build_analysis_for_saved_scenario,
    build_firepower_preview_for_pawn,
    build_pawn_profile,
    describe_equipment,
    describe_modifier_payload,
)
from rim_data_analysis.user_app_catalog import CatalogIndex, load_catalog_index
from rim_data_analysis.user_app_models import (
    ComparisonRow,
    EquipmentChoice,
    FirepowerPreview,
    FirepowerPreviewTarget,
    ImportSettings,
    SavedPawnTemplate,
    SavedScenarioTemplate,
)
from rim_data_analysis.user_app_options import (
    FEATURE_BY_ID,
    FEATURE_OPTIONS,
    FULL_BODY_ARMOR_COVERS,
    IMPLANT_BY_ID,
    IMPLANT_OPTIONS,
    MATERIAL_BY_ID,
    MATERIAL_OPTIONS,
    QUALITY_BY_ID,
    QUALITY_OPTIONS,
    REFERENCE_ARMOR_TARGETS,
    RANGED_PREVIEW_DISTANCE_CHOICES,
    SPECIES_BY_ID,
    SPECIES_OPTIONS,
    SUPPORT_GEAR_BY_ID,
    SUPPORT_GEAR_OPTIONS,
    WEAPON_QUALITY_RULES_BY_ID,
    EnhancementOption,
    FeatureOption,
    MaterialOption,
    QualityOption,
    SpeciesOption,
    WeaponQualityRule,
    humanlike_species_ids,
)
from rim_data_analysis.user_app_store import (
    UserAppStore as _UserAppStore,
    _nonce_slug as _store_nonce_slug,
    _slugify,
    _timestamp_slug as _store_timestamp_slug,
)


def _timestamp_slug() -> str:
    return _store_timestamp_slug()


def _nonce_slug() -> str:
    return _store_nonce_slug()


class UserAppStore(_UserAppStore):
    def make_id(self, name: str) -> str:
        base = _slugify(name)
        return f"{base}-{_timestamp_slug()}-{_nonce_slug()}"
