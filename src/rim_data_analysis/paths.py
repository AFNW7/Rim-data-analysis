from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


RIMWORLD_APP_ID = "294100"


@dataclass(slots=True)
class DiscoveredPaths:
    game_data_root: Path | None
    local_mods_root: Path | None
    workshop_root: Path | None
    save_data_root: Path | None
    checked_steam_libraries: list[Path]


def _existing_path(raw_value: str | None) -> Path | None:
    if not raw_value:
        return None

    path = Path(raw_value).expanduser()
    return path if path.exists() else None


def _candidate_steam_roots() -> list[Path]:
    roots: list[Path] = []
    for env_name in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        base = os.environ.get(env_name)
        if base:
            roots.append(Path(base) / "Steam")
    return roots


def parse_steam_libraryfolders(libraryfolders_path: Path) -> list[Path]:
    if not libraryfolders_path.exists():
        return []

    text = libraryfolders_path.read_text(encoding="utf-8", errors="ignore")
    libraries: list[Path] = []
    for match in re.finditer(r'"path"\s+"([^"]+)"', text):
        raw_path = match.group(1).replace("\\\\", "\\")
        libraries.append(Path(raw_path))
    return libraries


def discover_paths() -> DiscoveredPaths:
    env_game_data_root = _existing_path(os.getenv("RIMWORLD_GAME_DATA_ROOT"))
    env_local_mods_root = _existing_path(os.getenv("RIMWORLD_LOCAL_MODS_ROOT"))
    env_workshop_root = _existing_path(os.getenv("RIMWORLD_WORKSHOP_ROOT"))
    env_save_data_root = _existing_path(os.getenv("RIMWORLD_SAVE_DATA_ROOT"))

    if all((env_game_data_root, env_local_mods_root, env_workshop_root, env_save_data_root)):
        return DiscoveredPaths(
            game_data_root=env_game_data_root,
            local_mods_root=env_local_mods_root,
            workshop_root=env_workshop_root,
            save_data_root=env_save_data_root,
            checked_steam_libraries=[],
        )

    steam_libraries: list[Path] = []
    for steam_root in _candidate_steam_roots():
        libraryfolders_path = steam_root / "steamapps" / "libraryfolders.vdf"
        if libraryfolders_path.exists():
            steam_libraries.extend(parse_steam_libraryfolders(libraryfolders_path))
            default_library = steam_root
            if default_library not in steam_libraries:
                steam_libraries.insert(0, default_library)

    unique_libraries: list[Path] = []
    seen: set[str] = set()
    for path in steam_libraries:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique_libraries.append(path)

    game_data_root = env_game_data_root
    local_mods_root = env_local_mods_root
    workshop_root = env_workshop_root

    for library in unique_libraries:
        if game_data_root is None:
            candidate = library / "steamapps" / "common" / "RimWorld" / "Data"
            if candidate.exists():
                game_data_root = candidate
        if local_mods_root is None:
            candidate = library / "steamapps" / "common" / "RimWorld" / "Mods"
            if candidate.exists():
                local_mods_root = candidate
        if workshop_root is None:
            candidate = library / "steamapps" / "workshop" / "content" / RIMWORLD_APP_ID
            if candidate.exists():
                workshop_root = candidate

    save_data_root = env_save_data_root
    if save_data_root is None:
        local_low = Path.home() / "AppData" / "LocalLow" / "Ludeon Studios" / "RimWorld by Ludeon Studios"
        if local_low.exists():
            save_data_root = local_low

    return DiscoveredPaths(
        game_data_root=game_data_root,
        local_mods_root=local_mods_root,
        workshop_root=workshop_root,
        save_data_root=save_data_root,
        checked_steam_libraries=unique_libraries,
    )

