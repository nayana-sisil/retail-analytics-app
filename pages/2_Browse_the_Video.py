"""
Browse the Video - watch the annotated sample and inspect any moment.

The annotated video is shipped with the app - playback is instant. The
Browse tab below the player pulls 20 saved moments so you can click through
the video without needing to wait.
"""

import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import pipeline
import styles


st.set_page_config(
    page_title="Browse the Video - Retail Analytics",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231e3a8a'/%3E%3Ctext x='50' y='68' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ER%3C/text%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()


HERE = Path(__file__).parent.parent
ASSETS = HERE / "assets"
SAMPLE_FRAMES = ASSETS / "sample_frames"


@st.cache_data
def load_sample_results():
    path = ASSETS / "mall_sample_results.json"
    if not path.exists():
        return None
    with open(path) as f:
        return pipeline.result_from_jsonable(json.load(f))


@st.cache_data
def load_annotated_video():
    path = ASSETS / "mall_sample_annotated.mp4"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return f.read()


@st.cache_data
def list_sample_frame_indices():
    if not SAMPLE_FRAMES.exists():
        return []
    indices = []
    for f in sorted(SAMPLE_FRAMES.glob("frame_*.jpg")):
        try:
            idx = int(f.stem.split("_")[1])
            indices.append(idx)
        except (IndexError, ValueError):
            continue
    return indices


@st.cache_data
def get_frame_image(frame_idx):
    path = SAMPLE_FRAMES / f"frame_{int(frame_idx):04d}.jpg"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return f.read()


# Sidebar
with st.sidebar:
    st.markdown("## About this view")
    st.markdown(
        """
The annotated video was generated when the app was built and ships with
it &mdash; playback is instant, no processing happens in the browser.

The **Browse** tab lets you click through 20 saved moments and see exactly
which people the system was tracking.
        """
    )


# Header
styles.hero(
    "Browse the Video",
    "Watch the footage and inspect what the system saw in any moment.",
)


# First-time explainer
with st.expander("First time here? What am I looking at?", expanded=False):
    st.markdown(
        """
- The **colored boxes on the floor** are the store areas (entrance, center,
  storefronts, checkout) and the two displays (A and B).
- The **green rectangles around people** are the system's highlights &mdash;
  one rectangle per person the system spotted.
- The **number in the green tag** is that person's ID. The same person
  keeps the same number across the whole video.
        """
    )


# Load
result = load_sample_results()
video_bytes = load_annotated_video()
frame_indices = list_sample_frame_indices()

if video_bytes is None:
    st.warning(
        "Annotated video not found in `assets/`. "
        "Run `python scripts/build_sample_assets.py` to generate it, then refresh."
    )
    st.stop()


# Tabs
tab_video, tab_browse, tab_chart = st.tabs([
    "Watch",
    "Browse moments",
    "How busy each moment was",
])


# =============================================================================
# Tab 1: Watch
# =============================================================================
with tab_video:
    styles.section("Annotated playback")
    styles.interpretation(
        "Each green rectangle is one person. The number in the tag is that "
        "person's ID - the same person keeps the same number as they move "
        "through the store. The colored floor boxes are the store areas."
    )
    st.video(video_bytes)

    st.markdown("---")

    if frame_indices:
        styles.section("A few saved moments")
        styles.interpretation(
            "Six moments from across the video. Open the **Browse** tab to "
            "scrub through all 20 and see exactly who was in each."
        )
        pick = frame_indices[::max(1, len(frame_indices) // 6)][:6]
        cols = st.columns(3)
        for i, idx in enumerate(pick):
            with cols[i % 3]:
                img_bytes = get_frame_image(idx)
                if img_bytes is not None:
                    st.image(img_bytes, use_container_width=True, caption=f"At {idx/result.fps:.1f}s")


# =============================================================================
# Tab 2: Browse moments (the interactive bit)
# =============================================================================
with tab_browse:
    if not frame_indices:
        st.info("No saved moments available.")
    else:
        styles.section("Pick any moment in the video")
        styles.interpretation(
            "Drag the slider to jump to any saved moment. The image updates "
            "and the table below tells you exactly which people the system "
            "spotted there and which area they were standing in."
        )

        def moment_label(idx):
            return f"moment at {idx / result.fps:.1f}s"

        c_slider, c_number = st.columns([4, 1])
        with c_slider:
            chosen = st.select_slider(
                "Moment",
                options=frame_indices,
                value=frame_indices[len(frame_indices) // 2],
                format_func=moment_label,
                label_visibility="collapsed",
            )
        with c_number:
            chosen_num = st.number_input(
                "or jump to",
                min_value=frame_indices[0],
                max_value=frame_indices[-1],
                value=int(chosen),
                step=1,
                label_visibility="collapsed",
            )
        chosen = int(chosen_num)

        img_bytes = get_frame_image(chosen)
        if img_bytes is not None:
            st.image(
                img_bytes,
                use_container_width=True,
                caption=f"At {chosen / result.fps:.1f}s into the footage",
            )

        st.markdown("---")
        styles.section("Who was tracked at this moment?")
        styles.interpretation(
            "Each row is one person the system spotted. **Person #** is "
            "their ID - the same person keeps the same number across the "
            "whole video. **Area** is the store area they were standing "
            "in. **Display** is whether they were inside Display A or B."
        )

        if result is not None and len(result.tracks_df):
            df = result.tracks_df[result.tracks_df["frame"] == chosen].copy()
            if len(df):
                # Add area membership using the pre-built zones
                from shapely.geometry import Point
                j_zones = result.journey_zones
                d_zones = result.display_zones

                def _area(row):
                    pt = Point(row["cx"], row["cy"])
                    for name, poly in j_zones.items():
                        if poly.contains(pt):
                            return name.replace("_", " ").title()
                    return "(none)"

                def _display(row):
                    pt = Point(row["cx"], row["cy"])
                    for name, poly in d_zones.items():
                        if poly.contains(pt):
                            return name.replace("_", " ").title()
                    return "-"

                df["area"] = df.apply(_area, axis=1)
                df["display"] = df.apply(_display, axis=1)

                show = df[["track_id", "area", "display"]].rename(columns={
                    "track_id": "Person #",
                    "area": "Area",
                    "display": "Display",
                }).sort_values("Person #")
                st.dataframe(show, use_container_width=True, hide_index=True)

                st.markdown("")
                m1, m2, m3 = st.columns(3)
                m1.metric("People at this moment", f"{df['track_id'].nunique()}")
                inside = (df["area"] != "(none)").sum()
                m2.metric("Inside a store area", f"{inside} / {len(df)}")
                in_display = (df["display"] != "-").sum()
                m3.metric("Inside a display", f"{in_display} / {len(df)}")
            else:
                st.info("No one was tracked at this moment.")


# =============================================================================
# Tab 3: How busy each moment was
# =============================================================================
with tab_chart:
    if result is not None and len(result.tracks_df):
        styles.section("How full is the store at each moment?")
        styles.interpretation(
            "Each dot is one snapshot. **People spotted** is how many "
            "green rectangles the system drew. **Different people** is how "
            "many unique IDs were active - the more meaningful number, "
            "since one person can appear in many snapshots."
        )

        n_per_frame = (
            result.tracks_df.groupby("frame")
            .agg(spotted=("track_id", "size"), unique=("track_id", "nunique"))
            .reset_index()
        )
        n_per_frame["time_s"] = (n_per_frame["frame"] / result.fps).round(1)

        x_choice = st.radio(
            "Show by",
            ["Snapshot number", "Time (seconds)"],
            horizontal=True,
            label_visibility="collapsed",
        )
        x_col = "time_s" if x_choice == "Time (seconds)" else "frame"

        df_long = n_per_frame.melt(
            id_vars=[x_col],
            value_vars=["spotted", "unique"],
            var_name="metric", value_name="count",
        )
        df_long["metric"] = df_long["metric"].map({
            "spotted": "People spotted (rectangles drawn)",
            "unique":  "Different people (unique IDs)",
        })

        fig = px.line(
            df_long, x=x_col, y="count", color="metric",
            color_discrete_map={
                "People spotted (rectangles drawn)": "#94a3b8",
                "Different people (unique IDs)":     "#1e3a8a",
            },
            markers=True,
        )
        fig.update_layout(
            height=400,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=x_choice,
            yaxis_title="People at this moment",
            legend_title="",
            yaxis=dict(gridcolor="#e2e8f0"),
            xaxis=dict(gridcolor="#e2e8f0"),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg people spotted / moment", f"{n_per_frame['spotted'].mean():.1f}")
        c2.metric("Avg different people / moment", f"{n_per_frame['unique'].mean():.1f}")
        c3.metric("Peak people at one moment", f"{int(n_per_frame['unique'].max())}")
        c4.metric("Busiest moment", f"at {int(n_per_frame.loc[n_per_frame['unique'].idxmax(), 'frame'])/result.fps:.1f}s")
