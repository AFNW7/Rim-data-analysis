from __future__ import annotations

from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from rim_data_analysis.models import PackageMetadata, PackageScanResult, ScanInventory


def _iter_named_dirs(package_root: Path, dir_name: str) -> list[Path]:
    return [path for path in package_root.rglob(dir_name) if path.is_dir()]


def _text_of(root: ElementTree.Element, tag: str) -> str | None:
    node = root.find(tag)
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def _list_of(root: ElementTree.Element, tag: str) -> list[str]:
    parent = root.find(tag)
    if parent is None:
        return []
    values: list[str] = []
    for child in list(parent):
        direct_text = (child.text or "").strip()
        if direct_text:
            values.append(direct_text)
            continue

        package_id = child.find("packageId")
        if package_id is not None and package_id.text:
            text = package_id.text.strip()
            if text:
                values.append(text)
    return values


def parse_about_metadata(package_root: Path) -> PackageMetadata:
    about_path = package_root / "About" / "About.xml"
    if not about_path.exists():
        return PackageMetadata()

    try:
        root = ElementTree.parse(about_path).getroot()
    except ElementTree.ParseError:
        return PackageMetadata()

    dependencies = _list_of(root, "modDependencies")
    if not dependencies:
        dependencies = _list_of(root, "moddependencies")

    return PackageMetadata(
        name=_text_of(root, "name"),
        package_id=_text_of(root, "packageId"),
        author=_text_of(root, "author"),
        description=_text_of(root, "description"),
        supported_versions=_list_of(root, "supportedVersions"),
        load_before=_list_of(root, "loadBefore"),
        load_after=_list_of(root, "loadAfter"),
        mod_dependencies=dependencies,
    )


def _count_files(root: Path, suffixes: tuple[str, ...]) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def _count_files_in_named_dirs(package_root: Path, dir_name: str, suffixes: tuple[str, ...]) -> int:
    count = 0
    for directory in _iter_named_dirs(package_root, dir_name):
        count += _count_files(directory, suffixes)
    return count


def _count_all_xml(package_root: Path) -> int:
    return sum(1 for path in package_root.rglob("*.xml") if path.is_file())


def _scan_defs(package_root: Path) -> tuple[int, dict[str, int]]:
    def_file_count = 0
    def_type_counts: Counter[str] = Counter()

    for defs_root in _iter_named_dirs(package_root, "Defs"):
        for xml_path in defs_root.rglob("*.xml"):
            if not xml_path.is_file():
                continue
            def_file_count += 1
            try:
                root = ElementTree.parse(xml_path).getroot()
            except ElementTree.ParseError:
                continue

            for child in list(root):
                tag = child.tag
                if not isinstance(tag, str):
                    continue
                normalized = tag.rsplit("}", 1)[-1]
                def_type_counts[normalized] += 1

    return def_file_count, dict(sorted(def_type_counts.items()))


def scan_package(package_root: Path, source_type: str) -> PackageScanResult:
    metadata = parse_about_metadata(package_root)
    def_xml_file_count, def_type_counts = _scan_defs(package_root)

    folder_name = package_root.name
    workshop_id = folder_name if source_type == "workshop_mod" and folder_name.isdigit() else None

    return PackageScanResult(
        source_type=source_type,
        root_path=str(package_root),
        folder_name=folder_name,
        workshop_id=workshop_id,
        metadata=metadata,
        xml_file_count=_count_all_xml(package_root),
        def_xml_file_count=def_xml_file_count,
        patch_xml_file_count=_count_files_in_named_dirs(package_root, "Patches", (".xml",)),
        language_file_count=_count_files_in_named_dirs(package_root, "Languages", (".xml", ".txt")),
        assembly_file_count=_count_files_in_named_dirs(package_root, "Assemblies", (".dll",)),
        texture_file_count=_count_files_in_named_dirs(
            package_root, "Textures", (".png", ".jpg", ".jpeg", ".dds")
        ),
        sound_file_count=_count_files_in_named_dirs(package_root, "Sounds", (".wav", ".ogg", ".mp3")),
        has_about_xml=(package_root / "About" / "About.xml").exists(),
        has_load_folders_xml=(package_root / "LoadFolders.xml").exists(),
        def_type_counts=def_type_counts,
    )


def _child_package_dirs(root: Path) -> list[Path]:
    if not root or not root.exists():
        return []
    return sorted([path for path in root.iterdir() if path.is_dir()], key=lambda path: path.name.lower())


def build_inventory(
    game_data_root: Path | None,
    local_mods_root: Path | None,
    workshop_root: Path | None,
    save_data_root: Path | None,
) -> ScanInventory:
    packages: list[PackageScanResult] = []

    for package_root in _child_package_dirs(game_data_root) if game_data_root else []:
        packages.append(scan_package(package_root, "game_data"))

    for package_root in _child_package_dirs(local_mods_root) if local_mods_root else []:
        packages.append(scan_package(package_root, "local_mod"))

    for package_root in _child_package_dirs(workshop_root) if workshop_root else []:
        packages.append(scan_package(package_root, "workshop_mod"))

    return ScanInventory(
        game_data_root=str(game_data_root) if game_data_root else None,
        local_mods_root=str(local_mods_root) if local_mods_root else None,
        workshop_root=str(workshop_root) if workshop_root else None,
        save_data_root=str(save_data_root) if save_data_root else None,
        packages=packages,
    )
