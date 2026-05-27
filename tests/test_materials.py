from __future__ import annotations

from pathlib import Path

import pytest

from ds160_agent.document_intake import build_codex_materials_handoff
from ds160_agent.materials import build_materials_review_bundle, list_materials, load_material


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


def test_build_materials_review_bundle_includes_text_preview(tmp_path: Path) -> None:
    materials = tmp_path / "materials"
    materials.mkdir()
    (materials / "passport.txt").write_text("Passport Number: E12345678", encoding="utf-8")

    bundle = build_materials_review_bundle(tmp_path)

    assert bundle["counts"]["included"] == 1
    assert bundle["included"][0]["relativePath"] == "passport.txt"
    assert "Passport Number" in bundle["included"][0]["textPreview"]


def test_codex_materials_handoff_uses_folder_manifest(tmp_path: Path) -> None:
    materials = tmp_path / "materials"
    materials.mkdir()
    (materials / "i20.txt").write_text("SEVIS ID: N0012345678", encoding="utf-8")
    bundle = build_materials_review_bundle(tmp_path)

    handoff = build_codex_materials_handoff({"currentData": {"surname": "Li"}}, bundle)

    assert handoff["mode"] == "codex_materials_handoff"
    assert "materialsRoot" in handoff["handoff"]
    assert "i20.txt" in handoff["prompt"]
    assert "Step 3: Cross-check documents" in handoff["prompt"]
    assert "Assign confidence based on source quality" in handoff["prompt"]
