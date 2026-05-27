from __future__ import annotations

from pathlib import Path

import pytest

from ds160_agent.materials import list_materials, load_material


def test_list_and_load_material_text_file(tmp_path: Path) -> None:
    materials = tmp_path / "materials"
    materials.mkdir()
    (materials / "passport.txt").write_text("Passport Number: E12345678", encoding="utf-8")

    listing = list_materials(tmp_path)
    loaded = load_material(tmp_path, "passport.txt")

    assert listing["files"][0]["relativePath"] == "passport.txt"
    assert loaded["filename"] == "passport.txt"
    assert loaded["text"] == "Passport Number: E12345678"
    assert loaded["dataBase64"]


def test_material_load_blocks_path_escape(tmp_path: Path) -> None:
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")

    with pytest.raises(ValueError):
        load_material(tmp_path, "../secret.txt")
