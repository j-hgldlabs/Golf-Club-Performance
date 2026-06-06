from __future__ import annotations

import numpy as np
import pandas as pd
import altair as alt

# -----------------------------
# Shared styling / helpers
# -----------------------------
TITLE_FONTSIZE = 16
LABEL_FONTSIZE = 12
LEGEND_FONTSIZE = 11


def _require_cols(df: pd.DataFrame, cols: list[str], fn_name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{fn_name}: missing required columns: {missing}")


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def corridor(series: pd.Series, level: float = 0.95) -> tuple[float, float, float]:
    s = _safe_numeric(series).dropna()
    if s.empty:
        return float("nan"), float("nan"), float("nan")
    lower = float(s.quantile((1 - level) / 2))
    upper = float(s.quantile(1 - (1 - level) / 2))
    return lower, upper, upper - lower


# -----------------------------
# Plots (Altair for hover interactivity)
# -----------------------------
def plot_finish_dispersion(
    df: pd.DataFrame,
    title: str = "Finish Position Dispersion (Carry)",
    wide: bool = False,
) -> alt.Chart:
    """
    Scatter: finish_x vs finish_y, colored by Club Type, plus 2σ ellipse and 95% corridor.
    If wide=True, uses a taller aspect ratio to better fill Streamlit left column.
    """
    fn = "plot_finish_dispersion"
    _require_cols(df, ["Club Type", "finish_x", "finish_y"], fn)

    df = df.copy()
    df["finish_x"] = _safe_numeric(df["finish_x"])
    df["finish_y"] = _safe_numeric(df["finish_y"])

    lower, upper, width = corridor(df["finish_x"], level=0.95)
    mean_x = float(np.nanmean(df["finish_x"].values)) if df["finish_x"].notna().any() else float("nan")

    scatter = (
        alt.Chart(df)
        .mark_circle(size=55, opacity=0.62)
        .encode(
            x=alt.X("finish_x:Q", title="Carry Deviation (yds, -left / +right)"),
            y=alt.Y("finish_y:Q", title="Carry Distance (yds)"),
            color=alt.Color("Club Type:N", legend=alt.Legend(title="Club")),
            tooltip=[
                alt.Tooltip("Club Type:N"),
                alt.Tooltip("finish_x:Q", format=".1f", title="Carry Deviation (yds)"),
                alt.Tooltip("finish_y:Q", format=".1f", title="Carry Distance (yds)"),
            ],
        )
    )

    # 2σ ellipse (approximated with 200-point path)
    ellipse = None
    x = df["finish_x"].to_numpy(dtype=float)
    y = df["finish_y"].to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size >= 3:
        cov = np.cov(x, y)
        vals, vecs = np.linalg.eigh(cov)
        order = vals.argsort()[::-1]
        vals, vecs = vals[order], vecs[:, order]
        width_e, height_e = 2 * 2.0 * np.sqrt(np.maximum(vals, 0))
        theta = np.arctan2(*vecs[:, 0][::-1])
        t = np.linspace(0, 2 * np.pi, 200)
        ellipse_pts = pd.DataFrame(
            {
                "x": np.mean(x)
                + (width_e / 2) * np.cos(t) * np.cos(theta)
                - (height_e / 2) * np.sin(t) * np.sin(theta),
                "y": np.mean(y)
                + (width_e / 2) * np.cos(t) * np.sin(theta)
                + (height_e / 2) * np.sin(t) * np.cos(theta),
                "t": t,
            }
        )
        # Order by angle and disable fill so we only see the outline
        ellipse = (
            alt.Chart(ellipse_pts)
            .mark_line(color="black", strokeWidth=2, fill=None)
            .encode(x="x:Q", y="y:Q", order="t:Q")
        )

    corridor_chart = None
    if np.isfinite(lower) and np.isfinite(upper):
        corridor_chart = (
            alt.Chart(pd.DataFrame({"lower": [lower], "upper": [upper], "width": [width]}))
            .mark_rect(color="gray", opacity=0.12)
            .encode(x=alt.X("lower:Q"), x2="upper:Q"))

    mean_line = None
    if np.isfinite(mean_x):
        mean_line = alt.Chart(pd.DataFrame({"mean": [mean_x]})).mark_rule(color="black", strokeDash=[6, 4]).encode(x="mean:Q")

    layers: list[alt.Chart] = [scatter]
    if corridor_chart is not None:
        layers.append(corridor_chart)
    if mean_line is not None:
        layers.append(mean_line)
    if ellipse is not None:
        layers.append(ellipse)

    chart = alt.layer(*layers).properties(
        title=alt.TitleParams(text=title, fontSize=TITLE_FONTSIZE, anchor="start", dy=-10),
        height=760 if wide else 560,
        width=520,
    ).configure_legend(
        titleFontSize=LEGEND_FONTSIZE,
        labelFontSize=LEGEND_FONTSIZE - 1,
    )

    return chart.interactive()


def plot_start_vs_curve(df: pd.DataFrame, title: str = "Start vs Curve (yards)") -> alt.Chart:
    """
    Scatter: start_yards vs curve_yards, colored by club.
    Designed for Streamlit 50/50 column layout.
    """
    fn = "plot_start_vs_curve"
    _require_cols(df, ["Club Type", "start_yards", "curve_yards"], fn)

    df = df.copy()
    df["start_yards"] = _safe_numeric(df["start_yards"])
    df["curve_yards"] = _safe_numeric(df["curve_yards"])

    base = (
        alt.Chart(df)
        .mark_circle(size=55, opacity=0.65)
        .encode(
            x=alt.X("start_yards:Q", title="Start (yds): negative = starts left"),
            y=alt.Y("curve_yards:Q", title="Curve (yds): negative = curves left"),
            color=alt.Color("Club Type:N", legend=alt.Legend(title="Club")),
            tooltip=[
                alt.Tooltip("Club Type:N"),
                alt.Tooltip("start_yards:Q", format=".1f", title="Start (yds)"),
                alt.Tooltip("curve_yards:Q", format=".1f", title="Curve (yds)"),
            ],
        )
    )

    axes = alt.layer(
        alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="gray").encode(x="x:Q"),
        alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="gray").encode(y="y:Q"),
    )

    chart = alt.layer(base, axes).properties(
        title=alt.TitleParams(text=title, fontSize=TITLE_FONTSIZE, anchor="start", dy=-10),
        height=520,
        width=520,
    ).configure_legend(
        titleFontSize=LEGEND_FONTSIZE,
        labelFontSize=LEGEND_FONTSIZE - 1,
    )

    return chart.interactive()


def plot_club_dispersion(df: pd.DataFrame, club: str) -> alt.Chart:
    """
    Single-club dispersion scatter.
    Intended for the right column under the Start vs Curve plot, slightly shorter.
    """
    fn = "plot_club_dispersion"
    _require_cols(df, ["Club Type", "Carry Deviation Distance", "Carry Distance"], fn)

    subset = df[df["Club Type"] == club].copy()
    subset["Carry Deviation Distance"] = _safe_numeric(subset["Carry Deviation Distance"])
    subset["Carry Distance"] = _safe_numeric(subset["Carry Distance"])

    mean_carry = float(subset["Carry Distance"].mean()) if subset["Carry Distance"].notna().any() else float("nan")

    scatter = (
        alt.Chart(subset)
        .mark_circle(size=55, opacity=0.7)
        .encode(
            x=alt.X("Carry Deviation Distance:Q", title="Carry Deviation (yds)"),
            y=alt.Y("Carry Distance:Q", title="Carry Distance (yds)"),
            tooltip=[
                alt.Tooltip("Carry Deviation Distance:Q", format=".1f", title="Carry Deviation (yds)"),
                alt.Tooltip("Carry Distance:Q", format=".1f", title="Carry Distance (yds)"),
            ],
        )
    )

    vline = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="gray", strokeDash=[6, 4]).encode(x="x:Q")
    hline = None
    if np.isfinite(mean_carry):
        hline = alt.Chart(pd.DataFrame({"y": [mean_carry]})).mark_rule(color="gray", strokeDash=[6, 4]).encode(y="y:Q")

    layers = [scatter, vline]
    if hline is not None:
        layers.append(hline)

    chart = alt.layer(*layers).properties(
        title=alt.TitleParams(text=f"Shot Dispersion — {club}", fontSize=TITLE_FONTSIZE, anchor="start", dy=-10),
        height=360,
        width=520,
    )

    return chart.interactive()


def plot_shot_trajectory(df: pd.DataFrame) -> alt.Chart:
    """
    Ball flight trajectory per club: asymmetric two-segment parabola + decaying roll.
    Launch angle positions the apex along the flight path:
      x_apex = carry × clamp(0.38 + 0.004 × launch_angle_deg, 0.38, 0.55)
    Low-launch clubs (driver) peak early with a long shallow descent;
    high-launch clubs (wedges) peak closer to mid-flight.
    Each club is a separate colored arc. X = distance (yds), Y = height (ft).
    """
    fn = "plot_shot_trajectory"
    _require_cols(df, ["Club Type", "Apex Height", "Carry Distance"], fn)

    dfc = df[["Club Type", "Apex Height", "Carry Distance"]].copy()
    dfc["Apex Height"] = _safe_numeric(dfc["Apex Height"])
    dfc["Carry Distance"] = _safe_numeric(dfc["Carry Distance"])

    has_launch = "Launch Angle" in df.columns
    if has_launch:
        dfc["Launch Angle"] = _safe_numeric(df["Launch Angle"])

    has_total = "Total Distance" in df.columns
    if has_total:
        dfc["Total Distance"] = _safe_numeric(df["Total Distance"])

    grouped = (
        dfc.groupby("Club Type", dropna=True)
        .mean(numeric_only=True)
        .reset_index()
        .sort_values("Carry Distance")
    )

    records: list[dict] = []
    for _, row in grouped.iterrows():
        club = row["Club Type"]
        carry = float(row["Carry Distance"])
        apex = float(row["Apex Height"])
        launch = (
            float(row["Launch Angle"])
            if has_launch and pd.notna(row.get("Launch Angle"))
            else 20.0
        )
        total = (
            float(row["Total Distance"])
            if has_total and pd.notna(row.get("Total Distance"))
            else carry * 1.08
        )

        if carry <= 0 or apex <= 0 or not np.isfinite(carry) or not np.isfinite(apex):
            continue

        apex_ft = apex * 3.0  # convert yards → feet for display

        # Apex position: launch angle shifts where the peak occurs along the carry
        apex_frac = float(np.clip(0.38 + 0.004 * launch, 0.38, 0.55))
        x_apex = carry * apex_frac

        # Ascending segment (0 → x_apex): quadratic reaching apex_ft at x_apex
        # y = H · x · (2·x_apex − x) / x_apex²
        for x in np.linspace(0.0, x_apex, 120):
            y = apex_ft * x * (2.0 * x_apex - x) / x_apex ** 2
            records.append({
                "Club Type": club,
                "x": float(x),
                "y": max(0.0, float(y)),
                "segment": "carry",
                "launch_deg": round(launch, 1),
                "carry_yd": round(carry, 1),
                "apex_ft": round(apex_ft, 1),
                "total_yd": round(total, 1),
            })

        # Descending segment (x_apex → carry): quadratic back to ground
        # y = H · (1 − ((x − x_apex) / descent_span)²)
        # Matches dy/dx = 0 at x_apex so the junction with the ascending arc is smooth.
        descent_span = carry - x_apex
        for x in np.linspace(x_apex, carry, 80):
            y = apex_ft * (1.0 - ((x - x_apex) / descent_span) ** 2)
            records.append({
                "Club Type": club,
                "x": float(x),
                "y": max(0.0, float(y)),
                "segment": "carry",
                "launch_deg": round(launch, 1),
                "carry_yd": round(carry, 1),
                "apex_ft": round(apex_ft, 1),
                "total_yd": round(total, 1),
            })

        # Roll — decaying sine bounces from carry to total
        roll = total - carry
        if roll > 0:
            xs_roll = np.linspace(carry, total, 80)
            t = (xs_roll - carry) / roll
            ys_roll = apex_ft * 0.06 * np.exp(-4.0 * t) * np.abs(np.sin(4.0 * np.pi * t))
            for x, y in zip(xs_roll, ys_roll):
                records.append({
                    "Club Type": club,
                    "x": float(x),
                    "y": max(0.0, float(y)),
                    "segment": "roll",
                    "launch_deg": round(launch, 1),
                    "carry_yd": round(carry, 1),
                    "apex_ft": round(apex_ft, 1),
                    "total_yd": round(total, 1),
                })

    traj_df = pd.DataFrame(records)

    ground = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color="#999999", strokeWidth=1.5)
        .encode(y="y:Q")
    )

    tooltip = [
        alt.Tooltip("Club Type:N", title="Club"),
        alt.Tooltip("launch_deg:Q", format=".1f", title="Avg Launch Angle (°)"),
        alt.Tooltip("carry_yd:Q", format=".1f", title="Avg Carry (yds)"),
        alt.Tooltip("apex_ft:Q", format=".1f", title="Avg Apex (ft)"),
        alt.Tooltip("total_yd:Q", format=".1f", title="Avg Total (yds)"),
    ]

    carry_lines = (
        alt.Chart(traj_df[traj_df["segment"] == "carry"])
        .mark_line(strokeWidth=2.5)
        .encode(
            x=alt.X("x:Q", title="Distance (yds)"),
            y=alt.Y("y:Q", title="Apex Height (ft)", scale=alt.Scale(domainMin=0)),
            color=alt.Color("Club Type:N", legend=alt.Legend(title="Club")),
            detail="Club Type:N",
            tooltip=tooltip,
        )
    )

    roll_df = traj_df[traj_df["segment"] == "roll"]
    roll_lines = (
        alt.Chart(roll_df)
        .mark_line(strokeWidth=1.5, opacity=0.6)
        .encode(
            x=alt.X("x:Q"),
            y=alt.Y("y:Q"),
            color=alt.Color("Club Type:N", legend=None),
            detail="Club Type:N",
        )
    ) if not roll_df.empty else None

    layers: list[alt.Chart] = [ground, carry_lines]
    if roll_lines is not None:
        layers.append(roll_lines)

    return (
        alt.layer(*layers)
        .properties(
            title=alt.TitleParams(
                text="Ball Flight Trajectory by Club",
                fontSize=TITLE_FONTSIZE,
                anchor="start",
                dy=-10,
            ),
            height=380,
            width=760,
        )
        .configure_axis(labelFontSize=LABEL_FONTSIZE, titleFontSize=LABEL_FONTSIZE)
        .interactive()
    )


def plot_shot_shape_arcs(df_sc: pd.DataFrame) -> alt.Chart:
    """
    Top-down bird's-eye view of average shot paths per club.
    Each club is a quadratic Bezier arc from origin (0, 0) to (avg_finish_x, avg_carry),
    curved by avg_start_yards which encodes the launch direction.

    Control point: P1 = (start_yards × 0.45, carry × 0.45)
    This preserves the launch direction angle at the tee while giving visible curvature.
    """
    fn = "plot_shot_shape_arcs"
    _require_cols(df_sc, ["Club Type", "start_yards", "finish_x", "finish_y"], fn)

    grouped = (
        df_sc.groupby("Club Type", dropna=True)
        .agg(
            avg_start=("start_yards", "mean"),
            avg_finish_x=("finish_x", "mean"),
            avg_carry=("finish_y", "mean"),
            shots=("finish_y", "count"),
        )
        .reset_index()
        .sort_values("avg_carry")
    )

    arc_records: list[dict] = []
    dot_records: list[dict] = []

    for _, row in grouped.iterrows():
        club = str(row["Club Type"])
        sx = float(row["avg_start"])
        fx = float(row["avg_finish_x"])
        fy = float(row["avg_carry"])
        shots = int(row["shots"])

        if not (np.isfinite(sx) and np.isfinite(fx) and np.isfinite(fy)) or fy <= 0:
            continue

        # Quadratic Bezier: preserves launch direction at origin
        # P0 = (0,0), P1 = (sx*k, fy*k), P2 = (fx, fy)
        k = 0.45
        p0 = np.array([0.0, 0.0])
        p1 = np.array([sx * k, fy * k])
        p2 = np.array([fx, fy])

        t = np.linspace(0.0, 1.0, 150)
        bx = (1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * p1[0] + t ** 2 * p2[0]
        by = (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * p1[1] + t ** 2 * p2[1]

        shared = {
            "Club Type": club,
            "avg_carry": round(fy, 1),
            "avg_offline": round(fx, 1),
            "avg_start": round(sx, 1),
            "shots": shots,
        }
        for x, y in zip(bx, by):
            arc_records.append({"x": float(x), "y": float(y), **shared})

        dot_records.append({"x": fx, "y": fy, **shared})

    arc_df = pd.DataFrame(arc_records)
    dot_df = pd.DataFrame(dot_records)

    tooltip = [
        alt.Tooltip("Club Type:N", title="Club"),
        alt.Tooltip("avg_carry:Q", format=".1f", title="Avg Carry (yds)"),
        alt.Tooltip("avg_offline:Q", format=".1f", title="Avg Offline (yds)"),
        alt.Tooltip("avg_start:Q", format=".1f", title="Avg Start Dir (yds)"),
        alt.Tooltip("shots:Q", title="Shots"),
    ]

    target_line = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color="#aaaaaa", strokeDash=[5, 4], strokeWidth=1.5)
        .encode(x="x:Q")
    )

    arcs = (
        alt.Chart(arc_df)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=alt.X("x:Q", title="Lateral Deviation (yds  −left / +right)"),
            y=alt.Y("y:Q", title="Carry Distance (yds)", scale=alt.Scale(domainMin=0)),
            color=alt.Color("Club Type:N", legend=alt.Legend(title="Club")),
            detail="Club Type:N",
            tooltip=tooltip,
        )
    )

    dots = (
        alt.Chart(dot_df)
        .mark_point(filled=True, size=90)
        .encode(
            x=alt.X("x:Q"),
            y=alt.Y("y:Q"),
            color=alt.Color("Club Type:N", legend=None),
            tooltip=tooltip,
        )
    )

    club_labels = (
        alt.Chart(dot_df)
        .mark_text(fontSize=11, fontWeight="bold", dx=8, align="left")
        .encode(
            x=alt.X("x:Q"),
            y=alt.Y("y:Q"),
            text="Club Type:N",
            color=alt.Color("Club Type:N", legend=None),
        )
    )

    return (
        alt.layer(target_line, arcs, dots, club_labels)
        .properties(
            title=alt.TitleParams(
                text="Average Shot Shape by Club (Top-Down View)",
                fontSize=TITLE_FONTSIZE,
                anchor="start",
                dy=-10,
            ),
            height=600,
            width=680,
        )
        .configure_axis(labelFontSize=LABEL_FONTSIZE, titleFontSize=LABEL_FONTSIZE)
        .interactive()
    )


def plot_performance_metrics(df: pd.DataFrame) -> alt.Chart:
    """
    Interactive selector to view per-club averages for key performance metrics.
    Metrics: Club Speed, Ball Speed, Carry Distance, Total Distance, Spin Rate, and Smash Factor.
    Apex Height is rendered separately via plot_apex_height().
    """
    fn = "plot_performance_metrics"
    metrics = [
        ("Club Speed", "Club Speed (mph)"),
        ("Ball Speed", "Ball Speed (mph)"),
        ("Carry Distance", "Carry Distance (yds)"),
        ("Total Distance", "Total Distance (yds)"),
        ("Smash Factor", "Smash Factor"),
        ("Spin Rate", "Spin Rate (rpm)"),
    ]
    cols = ["Club Type"] + [m[0] for m in metrics]
    _require_cols(df, cols, fn)

    dfc = df[cols].copy()
    for m, _ in metrics:
        dfc[m] = _safe_numeric(dfc[m])

    # Aggregate by club (mean)
    grouped = dfc.groupby("Club Type", dropna=True).mean(numeric_only=True).reset_index()
    long = grouped.melt("Club Type", var_name="metric", value_name="value")

    metric_order = [m[0] for m in metrics]
    selector = alt.selection_point(
        fields=["metric"],
        bind=alt.binding_select(options=metric_order, name="Metric: "),
        value=[{"metric": "Carry Distance"}],
    )

    chart = (
        alt.Chart(long)
        .add_params(selector)
        .transform_filter(selector)
        .mark_bar(opacity=0.8)
        .encode(
            x=alt.X("value:Q", title=None),
            y=alt.Y("Club Type:N", sort="-x", title=None),
            color=alt.Color("Club Type:N", legend=None),
            tooltip=[
                alt.Tooltip("Club Type:N", title="Club"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", format=".1f", title="Value"),
            ],
        )
        .properties(
            title=alt.TitleParams(text="Performance Metrics by Club", fontSize=TITLE_FONTSIZE, anchor="start", dy=-10),
            height=520,
            width=620,
        )
        .configure_axis(labelFontSize=LABEL_FONTSIZE, titleFontSize=LABEL_FONTSIZE)
    )

    return chart.interactive()
