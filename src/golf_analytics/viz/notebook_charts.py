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


def plot_performance_metrics(df: pd.DataFrame) -> alt.Chart:
    """
    Interactive selector to view per-club averages for key performance metrics.
    Metrics: Club Speed, Ball Speed, Apex Height, Carry Distance, Total Distance, Spin Rate, and Smash Factor.
    """
    fn = "plot_performance_metrics"
    metrics = [
        ("Club Speed", "Club Speed (mph)"),
        ("Ball Speed", "Ball Speed (mph)"),
        ("Apex Height", "Apex (ft)"),
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
