import streamlit as st
import pandas as pd
import altair as alt
from pygwalker.api.streamlit import StreamlitRenderer

st.set_page_config(
    page_title="Golf Performance Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("Golf Performance Dashboard")

golfShots = pd.read_csv("data/avg_carry_yds.csv") #update with actual path (if used)

golfShots.columns = golfShots.columns.str.strip()
golfShots["Base Carry"] = pd.to_numeric(golfShots["Base Carry"], errors="coerce")

long = golfShots.melt("Club Type", var_name="Wind Condition", value_name="value")
long["value"] = pd.to_numeric(long["value"], errors="coerce")

# Compact hero metrics + snapshot
top_left, top_right = st.columns([1.1, 1])
with top_left:
    st.subheader("Average Carry (yds)")
    st.metric("Longest carry by Club Type", f"{golfShots['Base Carry'].max():.1f} - {golfShots['Club Type'][golfShots['Base Carry'].idxmax()]}")
    st.metric("Shortest carry by Club Type", f"{golfShots['Base Carry'].min():.1f} - {golfShots['Club Type'][golfShots['Base Carry'].idxmin()]}")
with top_right:
    st.subheader("Dataset snapshot")
    st.dataframe(golfShots, width="stretch", height=260, hide_index=True)

tab_chart, tab_pyg = st.tabs(["Distance comparison", "Explore Distance"])

with tab_chart:
    chart = (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("Club Type:N", title="Club"),
            xOffset="Wind Condition:N",
            y=alt.Y(
                "value:Q",
                title="Carry Distance (yds)",
                scale=alt.Scale(domain=[0, 320]),
            ),
            color=alt.Color("Wind Condition:N", legend=alt.Legend(orient="bottom", columns=3)),
            tooltip=["Club Type", "Wind Condition", alt.Tooltip("value:Q", format=".1f")],
        )
    ).properties(height=420)

    st.altair_chart(chart, width="stretch", theme="streamlit")

with tab_pyg:
    st.write("Drag fields to build custom visuals; powered by Pygwalker.")
    walker = StreamlitRenderer(golfShots)
    walker.explorer()
