from __future__ import annotations

import pandas as pd


def normalize_avg_carry(df: pd.DataFrame) -> pd.DataFrame:
    """Clean column names + coerce numeric fields for avg carry dataset."""
    out = df.copy()
    out.columns = out.columns.str.strip()

    # Common column in your current file
    if "Base Carry" in out.columns:
        out["Base Carry"] = pd.to_numeric(out["Base Carry"], errors="coerce")

    return out
