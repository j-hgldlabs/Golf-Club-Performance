from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from golf_analytics.utils import data_dir


NUMERIC_COLS = [
    "Club Speed",
    "Attack Angle",
    "Club Path",
    "Club Face",
    "Face to Path",
    "Ball Speed",
    "Smash Factor",
    "Launch Angle",
    "Launch Direction",
    "Backspin",
    "Sidespin",
    "Spin Rate",
    "Spin Axis",
    "Apex Height",
    "Carry Distance",
    "Carry Deviation Angle",
    "Carry Deviation Distance",
    "Total Distance",
    "Total Deviation Angle",
    "Total Deviation Distance",
]


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in NUMERIC_COLS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def compute_club_summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = _coerce_numeric(raw_df)
    if "Club Type" not in df.columns:
        raise ValueError("Expected column 'Club Type' in raw session data.")
    gb = df.groupby("Club Type", dropna=False)
    summary = pd.DataFrame({
        "shots": gb.size(),
        "avg_club_speed_mph": gb["Club Speed"].mean() if "Club Speed" in df.columns else None,
        "avg_ball_speed_mph": gb["Ball Speed"].mean() if "Ball Speed" in df.columns else None,
        "avg_smash": gb["Smash Factor"].mean() if "Smash Factor" in df.columns else None,
        "avg_launch_deg": gb["Launch Angle"].mean() if "Launch Angle" in df.columns else None,
        "avg_launch_dir_deg": gb["Launch Direction"].mean() if "Launch Direction" in df.columns else None,
        "avg_carry_yd": gb["Carry Distance"].mean() if "Carry Distance" in df.columns else None,
        "std_carry_yd": gb["Carry Distance"].std() if "Carry Distance" in df.columns else None,
        "avg_total_yd": gb["Total Distance"].mean() if "Total Distance" in df.columns else None,
        "std_total_yd": gb["Total Distance"].std() if "Total Distance" in df.columns else None,
        "avg_backspin_rpm": gb["Backspin"].mean() if "Backspin" in df.columns else None,
        "avg_spin_axis_deg": gb["Spin Axis"].mean() if "Spin Axis" in df.columns else None,
    }).reset_index()
    # Drop columns that ended up as None (if missing in source)
    summary = summary.dropna(axis=1, how="all")
    return summary


def compute_face_variance_by_club(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = _coerce_numeric(raw_df)
    if "Club Type" not in df.columns:
        raise ValueError("Expected column 'Club Type' in raw session data.")
    if "Face to Path" not in df.columns and ("Club Face" in df.columns and "Club Path" in df.columns):
        df["Face to Path"] = df["Club Face"] - df["Club Path"]

    gb = df.groupby("Club Type", dropna=False)

    out = pd.DataFrame({
        "shots": gb.size(),
        "avg_club_path_deg": gb["Club Path"].mean() if "Club Path" in df.columns else None,
        "avg_club_face_deg": gb["Club Face"].mean() if "Club Face" in df.columns else None,
        "avg_face_to_path_deg": gb["Face to Path"].mean() if "Face to Path" in df.columns else None,
        "std_face_to_path_deg": gb["Face to Path"].std() if "Face to Path" in df.columns else None,
    }).reset_index()

    # Simple shot-shape labels from face-to-path sign
    if "avg_face_to_path_deg" in out.columns:
        out["shape_bias"] = out["avg_face_to_path_deg"].apply(
            lambda x: "Draw bias" if pd.notna(x) and x < -0.5 else ("Fade bias" if pd.notna(x) and x > 0.5 else "Neutral")
        )

    out = out.dropna(axis=1, how="all")
    return out


def compute_club_carry_averages(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = _coerce_numeric(raw_df)
    if "Club Type" not in df.columns or "Carry Distance" not in df.columns:
        raise ValueError("Expected columns 'Club Type' and 'Carry Distance' in raw session data.")
    gb = df.groupby("Club Type", dropna=False)
    out = pd.DataFrame({
        "shots": gb.size(),
        "avg_carry_yd": gb["Carry Distance"].mean(),
        "std_carry_yd": gb["Carry Distance"].std(),
        "p10_carry_yd": gb["Carry Distance"].quantile(0.10),
        "p50_carry_yd": gb["Carry Distance"].quantile(0.50),
        "p90_carry_yd": gb["Carry Distance"].quantile(0.90),
    }).reset_index()
    return out


@dataclass(frozen=True)
class Deliverables:
    club_summary: pd.DataFrame
    face_variance_by_club: pd.DataFrame
    club_carry_averages: pd.DataFrame


def compute_all_deliverables(raw_df: pd.DataFrame) -> Deliverables:
    return Deliverables(
        club_summary=compute_club_summary(raw_df),
        face_variance_by_club=compute_face_variance_by_club(raw_df),
        club_carry_averages=compute_club_carry_averages(raw_df),
    )


def save_deliverables(delivs: Deliverables, out_dir: Optional[Path] = None) -> dict[str, Path]:
    if out_dir is None:
        out_dir = data_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "club_summary": out_dir / "club_summary.csv",
        "face_variance_by_club": out_dir / "face_variance_by_club.csv",
        "club_carry_averages": out_dir / "club_carry_averages.csv",
    }
    delivs.club_summary.to_csv(paths["club_summary"], index=False)
    delivs.face_variance_by_club.to_csv(paths["face_variance_by_club"], index=False)
    delivs.club_carry_averages.to_csv(paths["club_carry_averages"], index=False)
    return paths
