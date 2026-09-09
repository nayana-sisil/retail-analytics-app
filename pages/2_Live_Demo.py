"""
Live Demo - scrub through the annotated sample video and inspect what the
detector saw in each frame.

The annotated video is shipped as a static file with the app, so playback is
instant. The frame scrubber below the player also pulls 20 pre-extracted
frames (saved as JPEGs during the build) so you can click through the video
without depending on opencv at runtime.
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
    page_title="Live Demo - Retail Analytics",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231e3a8a'/%3E%3Ctext x='50' y='68' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ER%3C/text%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()


HERE = Path(__file__).parent.parent
ASSETS = HERE / "assets"
SAMPLE_FRAMES = ASSETS / "sample_frames"


# -----------------------------------------------------------------------------
# Loaders
# -----------------------------------------------------------------------------
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
def get_frame_image(frame_idx: int):
    """Load one of the pre-extracted sample frames as RGB bytes."""
    path = SAMPLE_FRAMES / f"frame_{int(frame_idx):04d}.jpg"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return f.read()


@st.cache_data
def get_detections_at_frame(frame_idx: int):
    """Return the detection rows for a given frame index."""
    if result is None or not len(result.tracks_df):
        return pd.DataFrame()
    return result.tracks_df[result.tracks_df["frame"] == frame_idx].copy()


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## About this view")
    st.markdown(
        """
The annotated video was generated during the build step and ships with
the app - playback is instant, no inference happens in the browser.

To run the pipeline on your own video, see the Methodology page.
        """
    )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
styles.hero(
    "Live Demo",
    "Scrub through the sample video and inspect what the detector found.",
)


# -----------------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------------
result = load_sample_results()
video_bytes = load_annotated_video()
frame_indices = list_sample_frame_indices()

if video_bytes is None:
    st.warning(
        "Annotated video not found in `assets/`. "
        "Run `python scripts/build_sample_assets.py` to generate it, then refresh."
    )
    st.stop()


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab_video, tab_scrub, tab_chart = st.tabs([
    "Video playback",
    "Frame inspector",
    "Activity over time",
])


# =============================================================================
# Tab 1: Video playback
# =============================================================================
with tab_video:
    styles.section("Annotated playback")
    styles.interpretation(
        "Each tracked person has a persistent ID. Colored polygons are the "
        "journey and display zones - same data the dashboard is built on."
    )
    st.video(video_bytes)

    st.markdown("---")

    if frame_indices:
        styles.section("Sample frames")
        styles.interpretation(
            f"{len(frame_indices)} evenly-spaced frames from the video. "
            "Click into the Frame Inspector tab to scrub between them and "
            "see per-frame detection details."
        )
        # Show 6 of them in a 3-column grid
        pick = frame_indices[::max(1, len(frame_indices) // 6)][:6]
        cols = st.columns(3)
        for i, idx in enumerate(pick):
            with cols[i % 3]:
                img_bytes = get_frame_image(idx)
                if img_bytes is not None:
                    st.image(img_bytes, use_container_width=True, caption=f"Frame {idx}")


# =============================================================================
# Tab 2: Frame Inspector (the interactive part)
# =============================================================================
with tab_scrub:
    if not frame_indices:
        st.info("No sample frames available. Re-run the build script to generate them.")
    else:
        styles.section("Scrub through the video")
        styles.interpretation(
            "Drag the slider to pick a frame. The image and the detection "
            "table below update in real time - so you can click around and "
            "see exactly what the system tracked in any moment."
        )

        # Build a quick lookup: frame index -> time string + detection count
        def frame_label(idx):
            seconds = idx / result.fps if result and result.fps else 0
            return f"frame {idx}  ({seconds:.1f}s)"

        # Two sliders: a coarse step slider + a fine numeric input
        c_slider, c_number = st.columns([4, 1])
        with c_slider:
            chosen = st.select_slider(
                "Frame",
                options=frame_indices,
                value=frame_indices[len(frame_indices) // 2],
                format_func=frame_label,
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

        # Show the selected frame
        img_bytes = get_frame_image(chosen)
        if img_bytes is not None:
            st.image(
                img_bytes,
                use_container_width=True,
                caption=f"Frame {chosen} - {chosen / result.fps:.1f}s into the video",
            )

        # Per-frame detection table
        st.markdown("---")
        styles.section(f"Detections in this frame")
        styles.interpretation(
            "Every row is one tracked person visible in the selected frame. "
            "**Confidence** is the detector's certainty. **Position** is the "
            "foot-point (bottom-center of the bounding box) in pixel coordinates."
        )

        if result is not None and len(result.tracks_df):
            df = result.tracks_df[result.tracks_df["frame"] == chosen].copy()
            if len(df):
                # Add zone membership (which journey / display zone the foot-point is in)
                def _zone_for_point(row, zones):
                    from shapely.geometry import Point
                    pt = Point(row["cx"], row["cy"])
                    for name, poly in zones.items():
                        if poly.contains(pt):
                            return name
                    return "(none)"

                j_zones = result.journey_zones
                d_zones = result.display_zones
                df["journey_zone"] = df.apply(lambda r: _zone_for_point(r, j_zones), axis=1)
                df["display_zone"] = df.apply(
                    lambda r: _zone_for_point(r, d_zones) if _zone_for_point(r, d_zones) in d_zones else "-",
                    axis=1,
                )

                show = df[[
                    "track_id", "conf", "journey_zone", "display_zone",
                    "cx", "cy",
                ]].rename(columns={
                    "track_id": "ID",
                    "conf": "Confidence",
                    "journey_zone": "Journey zone",
                    "display_zone": "Display zone",
                    "cx": "X (px)",
                    "cy": "Y (px)",
                }).sort_values("ID")
                st.dataframe(
                    show.style.format({"Confidence": "{:.2f}", "X (px)": "{:.0f}", "Y (px)": "{:.0f}"}),
                    use_container_width=True, hide_index=True,
                )

                # Quick metrics for this frame
                st.markdown("")
                m1, m2, m3 = st.columns(3)
                m1.metric("People in frame", f"{df['track_id'].nunique()}")
                m2.metric("Avg confidence", f"{df['conf'].mean():.2f}")
                inside = (df["journey_zone"] != "(none)").sum()
                m3.metric("Inside a journey zone", f"{inside} / {len(df)}")
            else:
                st.info("No detections in this frame.")


# =============================================================================
# Tab 3: Activity over time
# =============================================================================
with tab_chart:
    if result is not None and len(result.tracks_df):
        styles.section("Detections over time")
        styles.interpretation(
            "How busy the scene is at each point in the video. **Detections** "
            "is the raw detector output (sum of bboxes per frame). **People** "
            "is the count of unique track IDs - the more meaningful number."
        )

        n_per_frame = (
            result.tracks_df.groupby("frame")
            .agg(detections=("track_id", "size"), people=("track_id", "nunique"))
            .reset_index()
        )
        n_per_frame["time_s"] = (n_per_frame["frame"] / result.fps).round(1)

        # Toggle to switch x-axis between frame index and time
        x_choice = st.radio(
            "X axis",
            ["Frame index", "Time (seconds)"],
            horizontal=True,
            label_visibility="collapsed",
        )
        x_col = "time_s" if x_choice == "Time (seconds)" else "frame"

        df_long = n_per_frame.melt(
            id_vars=[x_col],
            value_vars=["detections", "people"],
            var_name="metric", value_name="count",
        )
        df_long["metric"] = df_long["metric"].map({
            "detections": "Raw detections (bboxes)",
            "people": "Unique people (track IDs)",
        })

        fig = px.line(
            df_long, x=x_col, y="count", color="metric",
            color_discrete_map={
                "Raw detections (bboxes)": "#94a3b8",
                "Unique people (track IDs)": "#1e3a8a",
            },
            markers=True,
        )
        fig.update_layout(
            height=400,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=x_choice,
            yaxis_title="Count per frame",
            legend_title="",
            yaxis=dict(gridcolor="#e2e8f0"),
            xaxis=dict(gridcolor="#e2e8f0"),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg detections / frame", f"{n_per_frame['detections'].mean():.1f}")
        c2.metric("Avg people / frame", f"{n_per_frame['people'].mean():.1f}")
        c3.metric("Peak people in a frame", f"{int(n_per_frame['people'].max())}")
        c4.metric("Busiest frame", f"#{int(n_per_frame.loc[n_per_frame['people'].idxmax(), 'frame'])}")
    else:
        st.info("No tracks available for chart.")
