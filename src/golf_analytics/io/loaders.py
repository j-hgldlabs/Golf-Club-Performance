from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO, Optional, Union

import pandas as pd

from golf_analytics.utils import data_dir


@dataclass(frozen=True)
class DataPaths:
    avg_carry_yds: Path
    total_merged_yds: Path
    club_summary: Path
    face_variance_by_club: Path
    club_carry_averages: Path
    club_combined_shots_gained: Path


def default_paths() -> DataPaths:
    d = data_dir()
    return DataPaths(
        avg_carry_yds=d / "avg_carry_yds.csv",
        total_merged_yds=d / "total_merged_yds.csv",
        club_summary=d / "club_summary.csv",
        face_variance_by_club=d / "face_variance_by_club.csv",
        club_carry_averages=d / "club_carry_averages.csv",
        club_combined_shots_gained=d / "club_combined_shots_gained.csv",
    )


def _read_csv(source: Optional[Union[str, Path, IO[bytes]]], default_path: Path) -> pd.DataFrame:
    if source is None:
        if not default_path.exists():
            raise FileNotFoundError(f"Expected {default_path} to exist. Put the CSV under data/ or pass a source.")
        return pd.read_csv(default_path)

    # Streamlit's UploadedFile behaves like a file-like object
    if hasattr(source, "read") and not isinstance(source, (str, Path)):
        return pd.read_csv(source)

    return pd.read_csv(Path(source))


def load_avg_carry_yds(source: Optional[Union[str, Path, IO[bytes]]] = None) -> pd.DataFrame:
    return _read_csv(source, default_paths().avg_carry_yds)


def load_club_summary(source: Optional[Union[str, Path, IO[bytes]]] = None) -> pd.DataFrame:
    return _read_csv(source, default_paths().club_summary)


def load_face_variance_by_club(source: Optional[Union[str, Path, IO[bytes]]] = None) -> pd.DataFrame:
    return _read_csv(source, default_paths().face_variance_by_club)


def load_club_carry_averages(source: Optional[Union[str, Path, IO[bytes]]] = None) -> pd.DataFrame:
    return _read_csv(source, default_paths().club_carry_averages)


def load_club_combined_shots_gained(source: Optional[Union[str, Path, IO[bytes]]] = None) -> pd.DataFrame:
    return _read_csv(source, default_paths().club_combined_shots_gained)


def load_total_merged_yds() -> pd.DataFrame:
    """Load the merged shot-level dataset used by the notebooks (data/total_merged_yds.csv)."""
    paths = default_paths()
    if not paths.total_merged_yds.exists():
        raise FileNotFoundError(f"Missing file: {paths.total_merged_yds}")
    return pd.read_csv(paths.total_merged_yds)
