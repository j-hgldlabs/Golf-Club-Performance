from __future__ import annotations

import time

import streamlit as st
import pandas as pd
from pygwalker.api.streamlit import StreamlitRenderer

import golf_analytics.api_client as api
from golf_analytics.cleaning.normalize import normalize_avg_carry
from golf_analytics.io.loaders import load_avg_carry_yds
from golf_analytics.metrics.summary import carry_summary
from golf_analytics.viz.charts import carry_comparison_chart
from golf_analytics.metrics.notebook_metrics import (
    compute_start_curve_finish,
    add_shape_labels,
    shape_summary_by_club,
)
from golf_analytics.viz.notebook_charts import (
    plot_finish_dispersion,
    plot_start_vs_curve,
    plot_club_dispersion,
    plot_performance_metrics,
)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _token() -> str:
    """Return a valid access token, refreshing automatically if within 5 minutes of expiry."""
    auth = st.session_state.auth
    if time.time() > auth.get("expires_at", 0) - 300:
        try:
            result = api.refresh_session(auth["refresh_token"])
            auth.update({
                "token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expires_at": result["expires_at"],
            })
        except Exception:
            _logout()
            st.stop()
    return auth["token"]


def _login_form() -> None:
    st.header("Sign In")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary", use_container_width=True):
        if not email or not password:
            st.error("Enter your email and password.")
            return
        try:
            result = api.login(email, password)
            st.session_state.auth = {
                "authenticated": True,
                "email": result["email"],
                "role": result["role"],
                "token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expires_at": result["expires_at"],
            }
            st.rerun()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Login failed: {e}")


def _logout() -> None:
    st.session_state.pop("auth", None)
    st.cache_data.clear()
    st.rerun()


def _ensure_auth() -> None:
    if "auth" not in st.session_state:
        st.session_state.auth = {"authenticated": False}

    if not st.session_state.auth.get("authenticated"):
        _login_form()
        st.stop()


def _admin_controls() -> None:
    st.markdown("---")
    st.subheader("Admin — user management")

    with st.form("invite_user"):
        new_email = st.text_input("Email to invite")
        submitted = st.form_submit_button("Send invite", use_container_width=True)

    if submitted:
        if not new_email:
            st.error("Provide an email.")
        else:
            try:
                api.invite_user(_token(), new_email)
                st.success(f"Invite sent to {new_email}.")
            except Exception as e:
                st.error(f"Could not invite: {e}")

    if st.button("Refresh user list", use_container_width=True):
        st.cache_data.clear()

    try:
        users = api.list_users(_token())
        if users:
            st.dataframe(
                pd.DataFrame(users)[["email", "role", "created_at", "last_sign_in"]],
                hide_index=True,
                width="stretch",
            )
    except Exception as e:
        st.warning(f"Could not load users: {e}")


# ---------------------------------------------------------------------------
# Cached API data loaders
# (token is the cache key — different users get separate cached results)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def _load_shots(token: str) -> pd.DataFrame:
    return api.get_shots(token)


@st.cache_data(ttl=120, show_spinner=False)
def _load_summary(token: str) -> pd.DataFrame:
    return api.get_summary(token)


@st.cache_data(ttl=120, show_spinner=False)
def _load_carry_averages(token: str) -> pd.DataFrame:
    return api.get_carry_averages(token)


@st.cache_data(ttl=120, show_spinner=False)
def _load_face_variance(token: str) -> pd.DataFrame:
    return api.get_face_variance(token)


@st.cache_data(ttl=120, show_spinner=False)
def _load_avg_carry(token: str) -> pd.DataFrame:
    return api.get_avg_carry(token)


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def _melt_for_chart(df: pd.DataFrame) -> pd.DataFrame:
    long = df.melt("Club Type", var_name="Wind Condition", value_name="value")
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long


def _download_button_from_df(label: str, df: pd.DataFrame, filename: str) -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv_bytes, file_name=filename, mime="text/csv", width="content")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def run() -> None:
    st.set_page_config(
        page_title="Golf Performance Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _ensure_auth()

    # Top bar
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.caption(f"Signed in as {st.session_state.auth['email']} ({st.session_state.auth['role']})")
    with top_right:
        if st.button("Log out", use_container_width=True, key="logout_main"):
            _logout()

    st.title("Golf Performance Dashboard")

    # -------------------------
    # Sidebar
    # -------------------------
    with st.sidebar:
        if st.session_state.auth.get("role") == "admin":
            _admin_controls()

        st.header("Inputs")

        st.subheader("A) Distance dashboard input")
        mode = st.radio(
            "Avg-carry source:",
            ["Compute from sessions", "Upload avg_carry_yds.csv"],
            index=0,
        )
        uploaded_avg = None
        if mode == "Upload avg_carry_yds.csv":
            uploaded_avg = st.file_uploader("Upload avg_carry_yds.csv", type=["csv"], key="avg")

        st.divider()

        st.subheader("B) Upload session CSV(s)")
        uploaded_raw = st.file_uploader(
            "Upload Garmin R10 session CSV(s)",
            type=["csv"],
            accept_multiple_files=True,
            key="raw",
        ) or []

        if uploaded_raw:
            if st.button("Upload to Supabase", type="primary", width="stretch"):
                success, failed = 0, 0
                for f in uploaded_raw:
                    try:
                        result = api.upload_session(_token(), f.read(), f.name)
                        success += 1
                        st.success(f"{f.name}: {result['rows_imported']} shots imported")
                    except Exception as e:
                        failed += 1
                        st.error(f"{f.name}: {e}")
                if success:
                    st.cache_data.clear()

        st.divider()

        if st.button("Generate analytics", type="primary", width="stretch",
                     help="Recompute all stats from your uploaded sessions"):
            try:
                with st.spinner("Computing..."):
                    result = api.generate_analytics(_token())
                st.success(f"Done — {result.get('clubs_computed', '?')} clubs computed")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Generate failed: {e}")

    # -------------------------
    # Load avg carry (Tab 1)
    # -------------------------
    avg_df = None
    if mode == "Compute from sessions":
        try:
            avg_df = normalize_avg_carry(_load_avg_carry(_token()))
        except Exception as e:
            st.sidebar.warning(f"Could not compute carry: {e}")
    elif uploaded_avg is not None:
        try:
            avg_df = normalize_avg_carry(load_avg_carry_yds(uploaded_avg))
        except Exception as e:
            st.error(f"Could not load avg_carry_yds.csv: {e}")

    # -------------------------
    # Load shot data (Tabs 3 & 4)
    # -------------------------
    merged: pd.DataFrame | None = None
    merged_error: str | None = None
    try:
        merged = _load_shots(_token())
        if merged.empty:
            merged = None
            merged_error = "No shots found. Upload sessions and click Generate analytics."
    except Exception as e:
        merged_error = str(e)

    tab_dash, tab_delivs, tab_viz, tab_perf = st.tabs(
        ["Distance dashboard", "Notebook deliverables", "Notebook visualizations", "Performance metrics"]
    )

    # -------------------------
    # Tab 1: Distance dashboard
    # -------------------------
    with tab_dash:
        if avg_df is None:
            st.info("Upload avg_carry_yds.csv in the sidebar to see the distance dashboard.")
        else:
            summary = carry_summary(avg_df)

            top_left, top_right = st.columns([1.1, 1], gap="large")
            with top_left:
                st.subheader("Average Carry (yds)")
                st.metric("Longest carry by Club Type", f"{summary.longest_value:.1f} - {summary.longest_club}")
                st.metric("Shortest carry by Club Type", f"{summary.shortest_value:.1f} - {summary.shortest_club}")
            with top_right:
                st.subheader("Dataset snapshot")
                st.dataframe(avg_df, width="stretch", height=260, hide_index=True)

            st.markdown("---")

            tab_chart, tab_pyg = st.tabs(["Distance comparison", "Explore Distance"])
            long_df = _melt_for_chart(avg_df)

            with tab_chart:
                st.subheader("Distance comparison")
                chart = carry_comparison_chart(long_df).properties(height=420)
                st.altair_chart(chart, width="stretch", theme="streamlit")

            with tab_pyg:
                st.subheader("Explore Distance")
                st.caption("Drag fields to build custom visuals (Pygwalker).")
                walker = StreamlitRenderer(avg_df)
                walker.explorer()

    # -------------------------
    # Tab 2: Deliverables
    # -------------------------
    with tab_delivs:
        st.subheader("Analytics deliverables")
        st.caption("Loaded from Supabase. Click **Generate analytics** in the sidebar to recompute.")

        club_summary_df: pd.DataFrame | None = None
        face_variance_df: pd.DataFrame | None = None
        carry_averages_df: pd.DataFrame | None = None

        try:
            club_summary_df = _load_summary(_token())
        except Exception:
            pass

        try:
            face_variance_df = _load_face_variance(_token())
        except Exception:
            pass

        try:
            carry_averages_df = _load_carry_averages(_token())
        except Exception:
            pass

        if club_summary_df is None and face_variance_df is None and carry_averages_df is None:
            st.info("No analytics found. Upload sessions and click **Generate analytics** in the sidebar.")
        else:
            if club_summary_df is not None:
                st.markdown("### Club summary")
                st.dataframe(club_summary_df, width="stretch", hide_index=True)
                _download_button_from_df("Download club_summary.csv", club_summary_df, "club_summary.csv")

            if face_variance_df is not None:
                st.markdown("### Face-to-path variance by club")
                st.dataframe(face_variance_df, width="stretch", hide_index=True)
                _download_button_from_df(
                    "Download face_variance_by_club.csv", face_variance_df, "face_variance_by_club.csv"
                )

            if carry_averages_df is not None:
                st.markdown("### Club carry averages")
                st.dataframe(carry_averages_df, width="stretch", hide_index=True)
                _download_button_from_df(
                    "Download club_carry_averages.csv", carry_averages_df, "club_carry_averages.csv"
                )

    # -------------------------
    # Tab 3: Notebook visuals
    # -------------------------
    with tab_viz:
        st.subheader("Notebook visualizations")
        st.caption("Shot shape and dispersion analysis from your Supabase shot data.")

        if merged is None:
            st.info(merged_error or "No shot data found.")
        else:
            df_sc = compute_start_curve_finish(merged)
            df_sc = add_shape_labels(df_sc)

            col1, col2 = st.columns([2.3, 1.2], gap="large")

            with col1:
                st.markdown("### Finish dispersion (carry)")
                chart1 = plot_finish_dispersion(df_sc, wide=True)
                st.altair_chart(chart1, width="stretch")

            with col2:
                st.markdown("### Start vs curve")
                chart2 = plot_start_vs_curve(df_sc)
                st.altair_chart(chart2, width="stretch")

                st.markdown("---")
                st.markdown("### Shot dispersion by club")
                clubs = sorted(df_sc["Club Type"].dropna().unique().tolist())
                if clubs:
                    selected = st.selectbox("Club", clubs, index=0, key="club_select")
                    chart3 = plot_club_dispersion(merged, selected)
                    st.altair_chart(chart3, width="stretch")
                else:
                    st.info("No clubs found in this dataset.")

            st.markdown("---")
            st.markdown("### Shape summary by club")
            summary_df = shape_summary_by_club(df_sc)
            st.dataframe(summary_df, width="stretch", hide_index=True)
            _download_button_from_df("Download shape_summary_by_club.csv", summary_df, "shape_summary_by_club.csv")

    # -------------------------
    # Tab 4: Performance metrics
    # -------------------------
    with tab_perf:
        st.subheader("Performance metrics")
        st.caption("Club speed, ball speed, apex height, carry distance, total distance, spin rate, and smash factor by club.")

        if merged is None:
            st.info(merged_error or "No shot data found.")
        else:
            chart_perf = plot_performance_metrics(merged)
            st.altair_chart(chart_perf, width="stretch")


if __name__ == "__main__":
    run()
