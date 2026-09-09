"""
Retail Video Analytics — landing page.

This is a public-facing demo of a computer-vision pipeline that turns retail
video into shopper journey + display engagement analytics.

Use the sidebar to navigate:
  1. Results Dashboard  (instant, pre-computed)
  2. Live Demo          (annotated video player)
  3. Methodology        (assumptions, limitations)
"""

import json
from pathlib import Path

import streamlit as st

import pipeline


# -----------------------------------------------------------------------------
# Page config + global style
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Retail Video Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


HERE = Path(__file__).parent
ASSETS = HERE / "assets"


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
    return None


@st.cache_resource
def load_model():
    """YOLO11n — small enough for free-tier CPU. Loaded once per session."""
    from ultralytics import YOLO
    return YOLO("yolo11n.pt")


# -----------------------------------------------------------------------------
# Landing page
# -----------------------------------------------------------------------------
st.title("🛍️ Retail Video Analytics")
st.caption(
    "A computer-vision proof of concept — turns retail video into shopper "
    "journey and display engagement analytics."
)

st.markdown(
    """
### What this is

A pretrained **YOLO11n** person detector paired with **ByteTrack** tracking
converts store video into persistent shopper trajectories. Those trajectories
are then mapped to spatial zones and turned into two kinds of business
analytics:

- **Customer journey** — where shoppers go, in what order, how often.
- **Display engagement** — who stops, who walks past, how long they stay.

### What to do here

1. Open the **Results Dashboard** to see the analytics on the bundled sample
   video (loads instantly — results are pre-computed).
2. Open the **Live Demo** to watch the annotated video with bounding boxes,
   track IDs, and zone overlays.
3. Open the **Methodology** page to read about assumptions, the pipeline, and
   the limitations of this POC.

> The full pipeline (detect → track → zone → analyze → visualize) is
> implemented in `pipeline.py`. The notebook this was refactored from is in
> the same repository.
"""
)

# Top-level KPIs (computed once from cached results)
result = load_sample_results()
if result is not None:
    st.markdown("---")
    st.subheader("📊 At a glance — sample video")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Frames processed", f"{result.n_frames_processed:,}")
    c2.metric(
        "Unique shoppers",
        f"{result.tracks_df['track_id'].nunique() if len(result.tracks_df) else 0}",
    )
    c3.metric(
        "Total zone visits",
        f"{int(result.footfall.sum())}",
    )
    avg_dwell = result.display_summary["avg_dwell_sec"].mean() if len(result.display_summary) else 0
    c4.metric("Avg display dwell", f"{avg_dwell:.1f} s")

    # Hero image: best annotated frame
    best_frame_path = ASSETS / "best_frame.jpg"
    if best_frame_path.exists():
        st.markdown("---")
        st.subheader("👁️ What the computer sees")
        st.caption(
            "A single frame from the sample video. Each person has a persistent ID. "
            "Colored polygons are the journey + display zones."
        )
        st.image(str(best_frame_path), use_container_width=True)
else:
    st.warning(
        "Sample results not found in `assets/`. Run `scripts/build_sample_assets.py` "
        "to generate them, or check the deployment guide."
    )

st.markdown("---")
st.caption(
    "POC. Pretrained YOLO11n. CPU-friendly. Built with Streamlit. "
    "Source code is in the project root."
)
