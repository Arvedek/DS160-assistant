from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

MAX_MATERIAL_BYTES = 8 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".log"}
ALLOWED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".txt",
    ".md",
    ".csv",
    ".json",
}


def ensure_materials_dir(workspace_root: Path) -> Path:
    root = workspace_root / "materials"
    root.mkdir(parents=True, exist_ok=True)
    gitkeep = root / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")
    return root


def list_materials(workspace_root: Path) -> dict[str, Any]:
    root = ensure_materials_dir(workspace_root)
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        stat = path.stat()
        rel = path.relative_to(root).as_posix()
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        files.append(
            {
                "id": rel,
                "name": path.name,
                "relativePath": rel,
                "sizeBytes": stat.st_size,
                "mimeType": mime_type,
                "tooLarge": stat.st_size > MAX_MATERIAL_BYTES,
                "isText": _is_text_path(path, mime_type),
            }
        )
    return {
        "root": str(root),
        "maxFileBytes": MAX_MATERIAL_BYTES,
        "files": files,
    }


def load_material(workspace_root: Path, relative_path: str) -> dict[str, Any]:
    root = ensure_materials_dir(workspace_root).resolve()
    path = (root / relative_path).resolve()
    if not _is_within(path, root) or not path.is_file():
        raise ValueError("Material file not found.")
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Unsupported material file type.")
    raw = path.read_bytes()
    if len(raw) > MAX_MATERIAL_BYTES:
        raise ValueError("Material file is too large for this MVP. Limit is 8 MB.")
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    text = ""
    if _is_text_path(path, mime_type):
        text = raw.decode("utf-8", errors="replace")
    return {
        "filename": path.name,
        "relativePath": path.relative_to(root).as_posix(),
        "mimeType": mime_type,
        "sizeBytes": len(raw),
        "dataBase64": base64.b64encode(raw).decode("ascii"),
        "text": text,
    }


def _is_text_path(path: Path, mime_type: str) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or mime_type.startswith("text/")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
