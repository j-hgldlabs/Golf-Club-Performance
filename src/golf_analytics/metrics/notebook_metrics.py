from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().replace("\ufeff", "") for c in out.columns]
    return out


def _to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def compute_start_curve_finish(df: pd.DataFrame) -> pd.DataFrame:
    """Replicates the notebook-derived fields using data/total_merged_yds.csv columns.

    Produces:
      - start_yards: lateral start offset at carry based on Launch Direction
      - curve_yards: finish - start at carry
      - finish_x: carry deviation distance (offline at carry)
      - finish_y: carry distance
    """
    df = _clean_columns(df)
    numeric_cols = [
        "Carry Distance",
        "Carry Deviation Distance",
        "Launch Direction",
        "Spin Axis",
        "Total Distance",
        "Total Deviation Distance",
        "Carry Deviation Angle",
        "Total Deviation Angle",
    ]
    df = _to_numeric(df, numeric_cols)

    needed = ["Club Type", "Carry Distance", "Carry Deviation Distance", "Launch Direction"]
    df2 = df.dropna(subset=[c for c in needed if c in df.columns]).copy()

    rad = np.deg2rad(df2["Launch Direction"])
    df2["start_yards"] = df2["Carry Distance"] * np.tan(rad)
    df2["finish_x"] = df2["Carry Deviation Distance"]
    df2["finish_y"] = df2["Carry Distance"]
    df2["curve_yards"] = df2["finish_x"] - df2["start_yards"]

    return df2


def classify_shape(start: float, curve: float, start_tol: float = 2.0, curve_tol: float = 2.0) -> str:
    """Match the notebook's start/curve bucket labels."""
    if pd.isna(start) or pd.isna(curve):
        return "Unknown"
    if abs(start) <= start_tol and abs(curve) <= curve_tol:
        return "Straight"
    start_dir = "Pull" if start < -start_tol else "Push" if start > start_tol else "Center"
    curve_dir = "Draw" if curve < -curve_tol else "Fade" if curve > curve_tol else "Straight"
    if start_dir == "Center":
        return "Straight" if curve_dir == "Straight" else f"Center-{curve_dir}"
    return f"{start_dir}-{curve_dir}"


def add_shape_labels(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["shape"] = [classify_shape(s, c) for s, c in zip(out["start_yards"], out["curve_yards"])]
    return out


def most_common_mode(s: pd.Series):
    m = s.mode(dropna=True)
    return m.iat[0] if not m.empty else np.nan


def shape_summary_by_club(df: pd.DataFrame) -> pd.DataFrame:
    """Summary table similar to the notebook output."""
    if "shape" not in df.columns:
        df = add_shape_labels(df)

    summary = (
        df.groupby("Club Type", dropna=False)
        .agg(
            shots=("Club Type", "size"),
            most_common_shape=("shape", most_common_mode),
            avg_start_yards=("start_yards", "mean"),
            avg_curve_yards=("curve_yards", "mean"),
            avg_finish_yards=("finish_x", "mean"),
            finish_std_yards=("finish_x", "std"),
        )
        .reset_index()
        .sort_values("shots", ascending=False)
    )
    num_cols = summary.select_dtypes(include="number").columns
    summary[num_cols] = summary[num_cols].round(2)
    return summary
