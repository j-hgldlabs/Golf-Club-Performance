from __future__ import annotations

import uuid
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from supabase import Client

from api.auth import get_current_user
from api.db import get_supabase
from golf_analytics.io.raw_sessions import read_raw_session

router = APIRouter()

STORAGE_BUCKET = "raw-sessions"

# Columns from the raw CSV that map to the shots table
SHOT_COLUMNS = [
    "Club Type",
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


@router.post("/upload")
async def upload_session(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Upload a raw Garmin R10 session CSV. Stores the file and imports shot rows."""
    raw_bytes = await file.read()

    # 1. Store raw CSV in Supabase Storage
    storage_path = f"{user.id}/{file.filename}"
    try:
        db.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            raw_bytes,
            file_options={"content-type": "text/csv", "upsert": "true"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    # 2. Parse with the existing analytics function
    try:
        df = read_raw_session(BytesIO(raw_bytes))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {e}")

    if df.empty:
        raise HTTPException(status_code=422, detail="No shot rows found in uploaded file.")

    # 3. Record the session in Postgres
    session_id = str(uuid.uuid4())
    db.table("sessions").insert({
        "id": session_id,
        "user_id": user.id,
        "filename": file.filename,
        "storage_path": storage_path,
    }).execute()

    # 4. Insert shot rows, keeping only columns that exist in this CSV
    present_cols = [c for c in SHOT_COLUMNS if c in df.columns]
    shots_df = df[present_cols].copy()

    # Coerce to float where possible so Postgres accepts the values
    for col in present_cols:
        if col != "Club Type":
            shots_df[col] = pd.to_numeric(shots_df[col], errors="coerce")

    shots_df["session_id"] = session_id
    shots_df["user_id"] = user.id

    # Replace NaN with None for JSON serialization
    shot_rows = shots_df.where(shots_df.notna(), other=None).to_dict(orient="records")

    # Rename columns to match Postgres snake_case schema
    col_map = {
        "Club Type": "club_type",
        "Club Speed": "club_speed",
        "Attack Angle": "attack_angle",
        "Club Path": "club_path",
        "Club Face": "club_face",
        "Face to Path": "face_to_path",
        "Ball Speed": "ball_speed",
        "Smash Factor": "smash_factor",
        "Launch Angle": "launch_angle",
        "Launch Direction": "launch_direction",
        "Backspin": "backspin",
        "Sidespin": "sidespin",
        "Spin Rate": "spin_rate",
        "Spin Axis": "spin_axis",
        "Apex Height": "apex_height",
        "Carry Distance": "carry_distance",
        "Carry Deviation Angle": "carry_deviation_angle",
        "Carry Deviation Distance": "carry_deviation_distance",
        "Total Distance": "total_distance",
        "Total Deviation Angle": "total_deviation_angle",
        "Total Deviation Distance": "total_deviation_distance",
    }
    shot_rows = [{col_map.get(k, k): v for k, v in row.items()} for row in shot_rows]

    db.table("shots").insert(shot_rows).execute()

    return {
        "session_id": session_id,
        "filename": file.filename,
        "rows_imported": len(shot_rows),
    }


@router.get("/")
async def list_sessions(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Return all sessions for the authenticated user."""
    result = (
        db.table("sessions")
        .select("id, filename, uploaded_at")
        .eq("user_id", user.id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Delete a session and its associated shots. User can only delete their own."""
    # Verify ownership
    row = (
        db.table("sessions")
        .select("id, storage_path")
        .eq("id", session_id)
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Remove from storage
    try:
        db.storage.from_(STORAGE_BUCKET).remove([row.data["storage_path"]])
    except Exception:
        pass  # Storage delete is best-effort; DB rows are authoritative

    db.table("shots").delete().eq("session_id", session_id).execute()
    db.table("sessions").delete().eq("id", session_id).execute()

    return {"deleted": session_id}
