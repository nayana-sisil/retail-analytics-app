"""
Retail Video Analytics - landing page.

A public-facing demo of a computer-vision pipeline that turns retail video
into shopper journey + display engagement analytics.

Use the sidebar to navigate:
  - Results Dashboard  (instant, pre-computed)
  - Live Demo          (annotated video + per-frame chart)
  - Methodology        (assumptions, pipeline, limitations)
"""

import json
from pathlib import Path

import streamlit as st

import pipeline
import styles


# -----------------------------------------------------------------------------
# Page config + style
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Retail Video Analytics",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231e3a8a'/%3E%3Ctext x='50' y='68' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ER%3C/text%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()


HERE = Path(__file__).parent
ASSETS = HERE / "assets"


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Retail Analytics")
    st.caption("Computer-vision POC")
    st.markdown("---")
    st.markdown("## Navigate")
    st.markdown(
        """
- [Results Dashboard](/Results_Dashboard) &mdash; KPIs, charts, downloads
- [Live Demo](/Live_Demo) &mdash; annotated video playback
- [Methodology](/Methodology) &mdash; assumptions & limitations
        """
    )
    st.markdown("---")
    st.markdown("## Sample data")
    st.caption("Mall dataset, 200 frames @ 1.5 fps")


# -----------------------------------------------------------------------------
# Cached loaders
# -----------------------------------------------------------------------------
@st.cache_data
def load_sample_results():
    path = ASSETS / "mall_sample_results.json"
    if not path.exists():
        return None
    with open(path) as f:
        return pipeline.result_from_jsonable(json.load(f))


@st.cache_resource
def load_model():
    """YOLO11n - small enough for free-tier CPU. Loaded once per session."""
    try:
        from ultralytics import YOLO
        return YOLO("yolo11n.pt")
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------------
styles.hero(
    "Retail Video Analytics",
    "Turn store video into shopper journey and display engagement insights."
)


# -----------------------------------------------------------------------------
# About
# -----------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("### What this is")
    st.markdown(
        """
A pretrained **YOLO11n** person detector paired with **ByteTrack** tracking
converts store video into persistent shopper trajectories. Those trajectories
are mapped to spatial zones and turned into two kinds of business analytics:

- **Customer journey** - where shoppers go, in what order, how often.
- **Display engagement** - who stops, who walks past, how long they stay.

The full pipeline (detect &rarr; track &rarr; zone &rarr; analyze &rarr; visualize)
lives in `pipeline.py`. The original notebook this was refactored from is
in the repository.
"""
    )

    st.markdown("### Where to start")
    st.markdown(
        """
1. Open the **Results Dashboard** to see the analytics on the bundled sample
   video (loads instantly - results are pre-computed).
2. Open the **Live Demo** to watch the annotated video with bounding boxes,
   track IDs, and zone overlays.
3. Open the **Methodology** page to read about assumptions, the pipeline, and
   the limitations of this POC.
        """
    )


# -----------------------------------------------------------------------------
# KPIs
# -----------------------------------------------------------------------------
result = load_sample_results()
if result is not None:
    st.markdown("---")
    st.subheader("At a glance - sample video")
    styles.interpretation(
        "Top-line numbers from the bundled 200-frame sample. Every metric on the "
        "Results Dashboard is derived from the same underlying trajectory data."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Frames processed", f"{result.n_frames_processed:,}")
    with c2:
        n_shoppers = int(result.tracks_df["track_id"].nunique()) if len(result.tracks_df) else 0
        st.metric("Unique shoppers", f"{n_shoppers}")
    with c3:
        st.metric("Total zone visits", f"{int(result.footfall.sum())}")
    with c4:
        avg_dwell = float(result.display_summary["avg_dwell_sec"].mean()) if len(result.display_summary) else 0
        st.metric("Avg display dwell", f"{avg_dwell:.1f}s")

    # Hero image: best annotated frame
    best_frame_path = ASSETS / "best_frame.jpg"
    if best_frame_path.exists():
        st.markdown("---")
        st.subheader("What the computer sees")
        styles.interpretation(
            "A single frame from the sample video. Each tracked person has a "
            "persistent ID. Colored polygons are the journey and display zones "
            "the analytics are computed against."
        )
        st.image(str(best_frame_path), use_container_width=True)
else:
    st.warning(
        "Sample results not found in `assets/`. "
        "Run `python scripts/build_sample_assets.py` to generate them, "
        "or check DEPLOY.md."
    )


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "POC. Pretrained YOLO11n. CPU-friendly. Built with Streamlit. "
    "Source code in the project root."
)
