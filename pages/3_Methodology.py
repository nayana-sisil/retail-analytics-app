"""
Methodology - assumptions, pipeline architecture, limitations, and how to
run the pipeline on your own video.
"""

import streamlit as st

import styles


st.set_page_config(
    page_title="Methodology - Retail Analytics",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231e3a8a'/%3E%3Ctext x='50' y='68' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ER%3C/text%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Read order")
    st.markdown(
        """
1. Executive summary
2. The pipeline
3. Assumptions
4. Limitations
5. Production gap
        """
    )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
styles.hero(
    "Methodology",
    "Everything the dashboard numbers are based on - read this if you're "
    "going to quote any of the metrics in a deck.",
)


# =============================================================================
# Executive summary
# =============================================================================
styles.section("1. Executive summary")
with st.container(border=True):
    st.markdown(
        """
The pipeline answers two questions:

> **Where are shoppers going?** (customer journey)

> **Are they engaging with the displays?** (display engagement)

The computer-vision system only sees pixels. It does not know what a
"storefront" or a "checkout" is. The analytics are the result of teaching
the system where those things *are* on the floor - by drawing zones.

Once a shopper is detected and tracked, every position they visit is
classified by zone. From there it's a few pandas operations to get funnels,
transitions, and dwell times.
        """
    )


# =============================================================================
# Pipeline architecture
# =============================================================================
styles.section("2. The pipeline")
with st.container(border=True):
    st.code(
        """
                    RETAIL VIDEO
                         |
                         v
                +-----------------+
                |  Frame Images   |
                +--------+--------+
                         |
                         v
                +-----------------+
                | YOLO11n Person  |
                |    Detection    |
                +--------+--------+
                         | bounding boxes + confidence
                         v
                +-----------------+
                |   ByteTrack     |
                |   Tracking      |
                +--------+--------+
                         | persistent track_id per person
                         v
                +-----------------+
                | Zone Assignment |
                | (point-in-poly) |
                +--------+--------+
                         | zone label per detection
                         v
                +-----------------+
                |   Analytics     |
                |  (pandas)       |
                +--------+--------+
                         |
                         v
                +-----------------+
                |   Dashboard     |
                +-----------------+
        """,
        language="text",
    )

    st.markdown("**Detection**")
    st.markdown(
        "`YOLO11n` (the nano variant, pretrained on COCO) detects people in each "
        "frame. Restricted to class `0` (person). Confidence threshold 0.35."
    )

    st.markdown("**Tracking**")
    st.markdown(
        "ByteTrack links detections across frames into persistent trajectories "
        "using a Kalman filter + Hungarian matcher. Same person across frames "
        "keeps the same `track_id`."
    )

    st.markdown("**Zone assignment**")
    st.markdown(
        "For each detection's foot point `(cx, cy)`, Shapely tests "
        "point-in-polygon against the predefined zones."
    )

    st.markdown("**Analytics**")
    st.markdown(
        "Pandas groups, counts, and pivots. Two outputs: footfall by zone, "
        "zone-to-zone transition counts, and per-display engagement metrics."
    )


# =============================================================================
# Assumptions
# =============================================================================
styles.section("3. Key assumptions")
styles.interpretation(
    "These are the choices baked into every number on the dashboard. "
    "Change any of them and the metrics change."
)

with st.container(border=True):
    st.markdown(
        """
| Assumption | Why it matters | What would change with a real measurement |
|---|---|---|
| `FPS = 1.5` (frames/sec) | Directly scales every dwell-time number | If the true camera FPS is 30, dwell times are 20x shorter |
| `MAX_FRAMES = 200` | The sample only covers part of the store's day | A longer capture would reveal more unique shoppers and more rare paths |
| Pretrained YOLO11n (no retail fine-tune) | Model wasn't trained on in-store crowds | A retail fine-tune would likely improve detection in occluded scenes |
| Fixed rectangular zones | Zone quality depends on the operator placing them correctly | Interactive zone drawing on a calibration frame would help |
| One camera, one sequence | No cross-camera ID matching | Production needs re-ID across cameras for full-store journeys |
| Passers = all tracked IDs | Over-counts "people near the display" | A near-display corridor polygon would scope passers correctly |
| Point-in-polygon for zone membership | Hard boundary; no fuzzy membership | Probabilistic zone membership (Gaussian) handles noise better |
        """
    )


# =============================================================================
# Limitations
# =============================================================================
styles.section("4. Limitations")

with st.container(border=True):
    st.markdown("**Identity persistence**")
    st.markdown(
        "ByteTrack keeps IDs while a person stays visible. A long occlusion "
        "can swap IDs. The mall dataset has a top-down camera with few "
        "occlusions, so this is fine; an aisle camera would need stronger "
        "re-identification."
    )

    st.markdown("**Zone rigidity**")
    st.markdown(
        "Zones are hard rectangles. A person straddling the entrance/center "
        "boundary will be assigned to whichever polygon their foot point "
        "falls inside. Consistent but not always intuitive."
    )

    st.markdown("**Camera FPS**")
    st.markdown(
        "The dataset is a sequence of frames, not a true video. The 1.5 fps "
        "assumption is reasonable for foot-traffic observation but should be "
        "replaced with a measured camera FPS in production."
    )

    st.markdown("**Single viewpoint**")
    st.markdown(
        "No cross-camera handoff. In a multi-camera store the same person "
        "gets different IDs on different cameras."
    )

    st.markdown("**No business context**")
    st.markdown(
        "The system counts people and time. It does not know who buys, who "
        "picks up a product, or who talks to a store associate. Those signals "
        "require additional sensors or POS integration."
    )

    st.markdown("**Sample size**")
    st.markdown(
        "200 frames is enough to demonstrate the pipeline, not enough to "
        "draw business conclusions. A real deployment would run on weeks "
        "of footage."
    )


# =============================================================================
# Production gap
# =============================================================================
styles.section("5. What production would add")
styles.interpretation(
    "The blocks are all here. The next step is hardening each one, not "
    "inventing new ones."
)

with st.container(border=True):
    st.markdown(
        """
- Camera calibration and measured FPS (not assumed)
- Retail-specific detector fine-tune
- Re-identification across cameras
- Live streaming + GPU inference
- Interactive zone drawing
- POS / transaction join for conversion analytics
- Alerting (e.g. "queue at checkout > 5 people for > 2 min")
- A/B testing infrastructure for layout changes
        """
    )


# =============================================================================
# Run it yourself
# =============================================================================
styles.section("6. Run it on your own data")
styles.interpretation(
    "Three commands. Need Python 3.10+ and a GPU is recommended for the "
    "detector (CPU works on small videos, just slowly)."
)

with st.container(border=True):
    st.code(
        """
# 1. Install
pip install -r requirements.txt

# 2. Process a video (or frame directory) -> produces JSON + CSV + annotated mp4
python scripts/process_video.py --video path/to/video.mp4 --out results/

# 3. Launch the dashboard locally
streamlit run app.py
        """,
        language="bash",
    )

    st.caption(
        "On Streamlit Community Cloud the free tier is CPU-only, so "
        "re-running the detector on a fresh video upload is slow. Locally "
        "with a GPU, a 200-frame video runs in about 10 seconds."
    )


st.markdown("---")
st.caption(
    "This page documents what was built, what was assumed, and what's not "
    "yet production-ready. Treat every number on the dashboard as a POC "
    "estimate, not a measurement."
)
