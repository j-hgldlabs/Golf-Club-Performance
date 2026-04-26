from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from api.auth import get_current_user
from api.db import get_supabase
from golf_analytics.metrics.deliverables import compute_all_deliverables
from golf_analytics.metrics.notebook_metrics import (
    compute_start_curve_finish,
    add_shape_labels,
    shape_summary_by_club,
)
from golf_analytics.cleaning.normalize import normalize_avg_carry

router = APIRouter()


def _fetch_shots(user_id: str, db: Client) -> pd.DataFrame:
    """Pull all shot rows for a user from Postgres into a DataFrame."""
    result = db.table("shots").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return pd.DataFrame()

    df = pd.DataFrame(result.data)

    # Rename snake_case DB columns back to the title-case format the analytics
    # engine expects (e.g. "carry_distance" → "Carry Distance")
    col_map = {
        "club_type": "Club Type",
        "club_speed": "Club Speed",
        "attack_angle": "Attack Angle",
        "club_path": "Club Path",
        "club_face": "Club Face",
        "face_to_path": "Face to Path",
        "ball_speed": "Ball Speed",
        "smash_factor": "Smash Factor",
        "launch_angle": "Launch Angle",
        "launch_direction": "Launch Direction",
        "backspin": "Backspin",
        "sidespin": "Sidespin",
        "spin_rate": "Spin Rate",
        "spin_axis": "Spin Axis",
        "apex_height": "Apex Height",
        "carry_distance": "Carry Distance",
        "carry_deviation_angle": "Carry Deviation Angle",
        "carry_deviation_distance": "Carry Deviation Distance",
        "total_distance": "Total Distance",
        "total_deviation_angle": "Total Deviation Angle",
        "total_deviation_distance": "Total Deviation Distance",
    }
    return df.rename(columns=col_map)


@router.post("/generate")
async def generate_analytics(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Recompute all deliverables from the user's shot data and cache them in Postgres."""
    raw_df = _fetch_shots(user.id, db)
    if raw_df.empty:
        raise HTTPException(status_code=404, detail="No shot data found. Upload sessions first.")

    # Reuse the existing analytics engine — no changes to that code
    delivs = compute_all_deliverables(raw_df)

    # Map compute_club_summary columns → club_summaries schema columns
    col_map = {
        "Club Type":          "club_type",
        "shots":              "shots",
        "avg_club_speed_mph": "avg_club_speed",
        "avg_ball_speed_mph": "avg_ball_speed",
        "avg_smash":          "avg_smash",
        "avg_launch_deg":     "avg_launch_deg",
        "avg_carry_yd":       "avg_carry_yd",
        "std_carry_yd":       "std_carry_yd",
        "avg_backspin_rpm":   "avg_backspin",
    }
    # Rename and keep only columns that exist in the schema
    renamed = delivs.club_summary.rename(columns=col_map)
    schema_cols = list(col_map.values())
    keep = [c for c in schema_cols if c in renamed.columns]
    summary_df = renamed[keep].copy()
    summary_df["user_id"] = user.id

    # Replace NaN with None so Postgres accepts the payload
    summary_rows = summary_df.where(summary_df.notna(), other=None).to_dict(orient="records")

    db.table("club_summaries").delete().eq("user_id", user.id).execute()
    db.table("club_summaries").insert(summary_rows).execute()

    return {
        "status": "ok",
        "clubs_computed": len(delivs.club_summary),
    }


@router.get("/summary")
async def club_summary(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Return the cached club summary for the authenticated user."""
    result = (
        db.table("club_summaries")
        .select("*")
        .eq("user_id", user.id)
        .order("club_type")
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="No summary found. POST /analytics/generate first.",
        )
    return result.data


@router.get("/carry-averages")
async def carry_averages(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Return carry distance percentiles (p10/p50/p90) per club."""
    from golf_analytics.metrics.deliverables import compute_club_carry_averages

    raw_df = _fetch_shots(user.id, db)
    if raw_df.empty:
        raise HTTPException(status_code=404, detail="No shot data found.")

    result = compute_club_carry_averages(raw_df)
    return result.to_dict(orient="records")


@router.get("/face-variance")
async def face_variance(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Return face-to-path variance and shape bias per club."""
    from golf_analytics.metrics.deliverables import compute_face_variance_by_club

    raw_df = _fetch_shots(user.id, db)
    if raw_df.empty:
        raise HTTPException(status_code=404, detail="No shot data found.")

    result = compute_face_variance_by_club(raw_df)
    return result.to_dict(orient="records")


@router.get("/shot-shapes")
async def shot_shapes(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Return shot shape summary (draw/fade/straight classification) per club."""
    raw_df = _fetch_shots(user.id, db)
    if raw_df.empty:
        raise HTTPException(status_code=404, detail="No shot data found.")

    df_sc = compute_start_curve_finish(raw_df)
    df_sc = add_shape_labels(df_sc)
    summary = shape_summary_by_club(df_sc)
    return summary.to_dict(orient="records")


# Wind adjustment factors derived from the avg_carry_yds model.
# Headwind reduces carry; tailwind adds carry (as % of base).
_WIND_FACTORS = {
    "0 to 5 mph headwind":   -0.05,
    "5 to 10 mph headwind":  -0.10,
    "10 to 20 mph headwind": -0.20,
    "20 to 30 mph headwind": -0.30,
    "0 to 5 mph tailwind":    0.02,
    "5 to 10 mph tailwind":   0.04,
    "10 to 20 mph tailwind":  0.08,
    "20 to 30 mph tailwind":  0.12,
}


@router.get("/avg-carry")
async def avg_carry(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Compute avg_carry_yds table from the user's shots data (base carry + wind adjustments)."""
    from golf_analytics.metrics.deliverables import compute_club_carry_averages

    raw_df = _fetch_shots(user.id, db)
    if raw_df.empty:
        raise HTTPException(status_code=404, detail="No shot data found.")

    carries = compute_club_carry_averages(raw_df)[["Club Type", "avg_carry_yd"]].copy()
    carries = carries.rename(columns={"avg_carry_yd": "Base Carry"})
    carries["Base Carry"] = carries["Base Carry"].round(1)

    for col, factor in _WIND_FACTORS.items():
        carries[col] = (carries["Base Carry"] * (1 + factor)).round(1)

    return carries.to_dict(orient="records")


@router.get("/shots")
async def get_shots(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Return all raw shots for the user in title-case column format (analytics-engine ready)."""
    df = _fetch_shots(user.id, db)
    if df.empty:
        return []
    return df.where(df.notna(), other=None).to_dict(orient="records")
