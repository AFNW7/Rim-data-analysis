from pathlib import Path

from rim_data_analysis.paths import parse_steam_libraryfolders


def test_parse_steam_libraryfolders() -> None:
    libraryfolders = Path("tests/fixtures/steam/libraryfolders.vdf")

    libraries = parse_steam_libraryfolders(libraryfolders)

    assert libraries == [Path(r"C:\Program Files (x86)\Steam"), Path(r"D:\SteamLibrary")]
