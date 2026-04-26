from __future__ import annotations

from pathlib import Path
from typing import Iterable, IO, Optional, Union

import pandas as pd

from golf_analytics.utils import data_dir


RAW_DIR = "raw_data"


def _drop_units_row(df: pd.DataFrame) -> pd.DataFrame:
    # In your CSVs, row 0 contains units like [mph], [deg], etc.
    # It also has Player=NaN. Drop rows where 'Player' is missing.
    if "Player" in df.columns:
        df = df[df["Player"].notna()].copy()
    return df


def read_raw_session(source: Union[str, Path, IO[bytes]]) -> pd.DataFrame:
    df = pd.read_csv(source)
    df = _drop_units_row(df)
    return df


def load_raw_sessions_from_data_dir(limit: Optional[int] = None) -> list[pd.DataFrame]:
    raw_path = data_dir() / RAW_DIR
    if not raw_path.exists():
        return []
    paths = sorted(raw_path.glob("*.csv"))
    if limit is not None:
        paths = paths[:limit]
    return [read_raw_session(p) for p in paths]


def concat_sessions(dfs: Iterable[pd.DataFrame]) -> pd.DataFrame:
    dfs = [d for d in dfs if d is not None and len(d) > 0]
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    return df
