from __future__ import annotations

import altair as alt
import pandas as pd


def carry_comparison_chart(long_df: pd.DataFrame, domain_max: int = 320) -> alt.Chart:
    """Grouped bar chart: carry distance by club + wind condition."""
    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X("Club Type:N", title="Club"),
            xOffset="Wind Condition:N",
            y=alt.Y("value:Q", title="Carry Distance (yds)", scale=alt.Scale(domain=[0, domain_max])),
            color=alt.Color("Wind Condition:N", legend=alt.Legend(orient="bottom", columns=3)),
            tooltip=["Club Type", "Wind Condition", alt.Tooltip("value:Q", format=".1f")],
        )
    )
    return chart
