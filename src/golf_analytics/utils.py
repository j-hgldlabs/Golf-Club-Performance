from __future__ import annotations

from pathlib import Path
from typing import Optional


def project_root(start: Optional[Path] = None) -> Path:
    """Return the project root (directory containing pyproject.toml or requirements.txt).

    This works locally and on Streamlit Community Cloud.
    """
    start = (start or Path(__file__)).resolve()
    for parent in [start] + list(start.parents):
        if (parent / "pyproject.toml").exists() or (parent / "requirements.txt").exists():
            return parent
    # Fallback: package directory -> two parents up
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    return project_root() / "data"
