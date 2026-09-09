"""
Live Demo - annotated video player + per-frame analytics chart for the
bundled sample.

Renders the pre-baked annotated video. No live inference runs on Streamlit
Cloud's free tier; this page shows the output of the pipeline rather than
re-running it.
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
def get_frames_for_video(annotated_bytes, n=6):
    if annotated_bytes is None:
        return []
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as t:
        t.write(annotated_bytes)
        tmp = t.name
    try:
        cap = cv2.VideoCapture(tmp)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        idxs = np.linspace(0, max(total - 1, 0), n, dtype=int)
        out = []
        for idx in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, fr = cap.read()
            if ok:
                out.append(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
        cap.release()
        return out
    except Exception:
        return []
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## About this view")
    st.markdown(
        """
The annotated video is **pre-rendered** and shipped with the app. The
underlying pipeline ran once during the build step and the results
were baked into the file you see here.

To re-run the pipeline on a new video, see the Methodology page.
        """
    )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
styles.hero(
    "Live Demo",
    "Watch the computer-vision pipeline's output on the sample video.",
)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
result = load_sample_results()
video_bytes = load_annotated_video()

if video_bytes is None:
    st.warning(
        "Annotated video not found in `assets/`. "
        "Run `python scripts/build_sample_assets.py` to generate it, then refresh."
    )
    st.stop()


# Tabs
tab_video, tab_chart = st.tabs(["Annotated video", "Per-frame chart"])


with tab_video:
    styles.section("Annotated playback")
    styles.interpretation(
        "Each tracked person has a persistent ID. Colored polygons are the "
        "journey + display zones. Same data the dashboard is built on."
    )
    st.video(video_bytes)

    st.markdown("---")

    styles.section("Sample frames")
    styles.interpretation(
        "Six evenly-spaced frames from the annotated video. Watch how shoppers "
        "enter from the top of the frame, move through the center and storefronts, "
        "and exit via checkout."
    )
    frames = get_frames_for_video(video_bytes, n=6)
    if frames:
        cols = st.columns(3)
        for i, fr in enumerate(frames):
            with cols[i % 3]:
                st.image(fr, use_container_width=True)
    else:
        best = ASSETS / "best_frame.jpg"
        if best.exists():
            st.image(str(best), use_container_width=True)
            st.caption("Frame extraction unavailable - showing the highest-activity frame instead.")


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

        df_long = n_per_frame.melt(
            id_vars="frame",
            value_vars=["detections", "people"],
            var_name="metric", value_name="count",
        )
        df_long["metric"] = df_long["metric"].map({
            "detections": "Raw detections (bboxes)",
            "people": "Unique people (track IDs)",
        })

        fig = px.line(
            df_long, x="frame", y="count", color="metric",
            color_discrete_map={
                "Raw detections (bboxes)": "#94a3b8",
                "Unique people (track IDs)": "#1e3a8a",
            },
        )
        fig.update_layout(
            height=400,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title="Frame index",
            yaxis_title="Count per frame",
            legend_title="",
            yaxis=dict(gridcolor="#e2e8f0"),
            xaxis=dict(gridcolor="#e2e8f0"),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Avg detections / frame",
            f"{n_per_frame['detections'].mean():.1f}",
        )
        c2.metric(
            "Avg people / frame",
            f"{n_per_frame['people'].mean():.1f}",
        )
        c3.metric(
            "Peak people in a frame",
            f"{int(n_per_frame['people'].max())}",
        )
    else:
        st.info("No tracks available for chart.")
