from pathlib import Path

from rim_data_analysis.scanner import build_inventory, parse_about_metadata, scan_package


def test_parse_about_metadata_reads_common_fields() -> None:
    package_root = Path("tests/fixtures/local_mods/SampleLocalMod")

    metadata = parse_about_metadata(package_root)

    assert metadata.name == "Sample Local Mod"
    assert metadata.package_id == "tester.sample.local"
    assert metadata.author == "Tester"
    assert metadata.supported_versions == ["1.6"]
    assert metadata.load_after == ["ludeon.rimworld"]


def test_scan_package_counts_defs_and_assemblies() -> None:
    package_root = Path("tests/fixtures/workshop_mods/1234567890")

    result = scan_package(package_root, "workshop_mod")

    assert result.workshop_id == "1234567890"
    assert result.metadata.name == "Workshop Example"
    assert result.def_xml_file_count == 1
    assert result.def_type_counts == {"IncidentDef": 1, "ThingDef": 1}


def test_build_inventory_collects_multiple_sources() -> None:
    inventory = build_inventory(
        game_data_root=Path("tests/fixtures/game_data"),
        local_mods_root=Path("tests/fixtures/local_mods"),
        workshop_root=Path("tests/fixtures/workshop_mods"),
        save_data_root=Path("tests/fixtures/save_data"),
    )

    assert len(inventory.packages) == 4
    assert {package.source_type for package in inventory.packages} == {
        "game_data",
        "local_mod",
        "workshop_mod",
    }


def test_scan_package_supports_versioned_content_and_nested_dependencies() -> None:
    package_root = Path("tests/fixtures/local_mods/VersionedMod")

    result = scan_package(package_root, "local_mod")

    assert result.metadata.mod_dependencies == ["brrainz.harmony"]
    assert result.def_xml_file_count == 1
    assert result.assembly_file_count == 1
    assert result.def_type_counts == {"ThingDef": 1}
