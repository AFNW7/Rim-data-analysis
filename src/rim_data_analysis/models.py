from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class PackageMetadata:
    name: str | None = None
    package_id: str | None = None
    author: str | None = None
    description: str | None = None
    supported_versions: list[str] = field(default_factory=list)
    load_before: list[str] = field(default_factory=list)
    load_after: list[str] = field(default_factory=list)
    mod_dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class PackageScanResult:
    source_type: str
    root_path: str
    folder_name: str
    workshop_id: str | None
    metadata: PackageMetadata
    xml_file_count: int
    def_xml_file_count: int
    patch_xml_file_count: int
    language_file_count: int
    assembly_file_count: int
    texture_file_count: int
    sound_file_count: int
    has_about_xml: bool
    has_load_folders_xml: bool
    def_type_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_type": self.source_type,
            "root_path": self.root_path,
            "folder_name": self.folder_name,
            "workshop_id": self.workshop_id,
            "metadata": self.metadata.to_dict(),
            "xml_file_count": self.xml_file_count,
            "def_xml_file_count": self.def_xml_file_count,
            "patch_xml_file_count": self.patch_xml_file_count,
            "language_file_count": self.language_file_count,
            "assembly_file_count": self.assembly_file_count,
            "texture_file_count": self.texture_file_count,
            "sound_file_count": self.sound_file_count,
            "has_about_xml": self.has_about_xml,
            "has_load_folders_xml": self.has_load_folders_xml,
            "def_type_counts": self.def_type_counts,
        }


@dataclass(slots=True)
class ScanInventory:
    game_data_root: str | None
    local_mods_root: str | None
    workshop_root: str | None
    save_data_root: str | None
    packages: list[PackageScanResult]

    def to_dict(self) -> dict[str, object]:
        return {
            "game_data_root": self.game_data_root,
            "local_mods_root": self.local_mods_root,
            "workshop_root": self.workshop_root,
            "save_data_root": self.save_data_root,
            "packages": [package.to_dict() for package in self.packages],
        }

