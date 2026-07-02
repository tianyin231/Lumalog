"""Shared upload paths."""
from __future__ import annotations

import os
from pathlib import Path

UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "../data/uploads")).resolve()


def upload_dir(kind: str) -> Path:
    path = UPLOAD_ROOT / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def upload_url(kind: str, filename: str) -> str:
    return f"/uploads/{kind}/{filename}"


def upload_path_from_url(url: str) -> Path | None:
    prefix = "/uploads/"
    if not url.startswith(prefix):
        return None
    return UPLOAD_ROOT / url[len(prefix):]
