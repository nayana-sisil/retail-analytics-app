"""
Methodology — assumptions, pipeline, limitations.

This page is the same narrative content as the original notebook, re-formatted
for non-technical readers. It exists so stakeholders can sanity-check the
numbers on the dashboard.
"""

import streamlit as st


st.set_page_config(page_title="Methodology · Retail Analytics", page_icon="📖", layout="wide")


st.title("📖 Methodology, Assumptions, Limitations")
st.caption(
    "Everything the dashboard numbers are based on — read this if you're going to "
    "quote any of the metrics in a deck."
)


# -----------------------------------------------------------------------------
# Executive summary
# -----------------------------------------------------------------------------
st.markdown(
    """
## 1. Executive summary

The pipeline answers two questions:

> **Where are shoppers going?** (customer journey)

> **Are they engaging with the displays?** (display engagement)

The computer-vision system only sees pixels. It does not know what a
"storefront" or a "checkout" is. The analytics are the result of teaching
the system where those things *are* on the floor — by drawing zones.

Once a shopper is detected and tracked, every position they visit is
classified by zone. From there it's a few pandas operations to get
funnels, transitions, and dwell times.
"""
)


# -----------------------------------------------------------------------------
# Pipeline architecture
# -----------------------------------------------------------------------------
st.markdown(
    """
## 2. The pipeline

```
                    RETAIL VIDEO
                         │
                         ▼
                ┌─────────────────┐
                │  Frame Images   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ YOLO11n Person  │
                │    Detection    │
                └────────┬────────┘
                         │ bounding boxes + confidence
                         ▼
                ┌─────────────────┐
                │   ByteTrack     │
                │   Tracking      │
                └────────┬────────┘
                         │ persistent track_id per person
                         ▼
                ┌─────────────────┐
                │ Zone Assignment │
                │ (point-in-poly) │
                └────────┬────────┘
                         │ zone label per detection
                         ▼
                ┌─────────────────┐
                │   Analytics     │
                │  (pandas)       │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Dashboard      │
                └─────────────────┘
```

**Detection** — `YOLO11n` (the nano variant, pretrained on COCO) detects
people in each frame. Restricted to class `0` (person). Confidence
threshold 0.35.

**Tracking** — ByteTrack links detections across frames into persistent
trajectories using a Kalman filter + Hungarian matcher. Same person
across frames keeps the same `track_id`.

**Zone assignment** — for each detection's foot point `(cx, cy)`, Shapely
tests point-in-polygon against the predefined zones.

**Analytics** — pandas groups, counts, and pivots. Two outputs:
- `footfall_by_zone`: unique track_ids per zone.
- `zone_transitions`: pairs of consecutive (zone_from, zone_to) per shopper.
- `display_metrics`: per-display passers / entries / engagement rate / dwell.
"""
)


# -----------------------------------------------------------------------------
# Key assumptions
# -----------------------------------------------------------------------------
st.markdown(
    """
## 3. Key assumptions

| Assumption | Why it matters | What would change with a real measurement |
|---|---|---|
| `FPS = 1.5` (frames/sec) | Directly scales every dwell-time number | If the true camera FPS is 30, dwell times are 20× shorter |
| `MAX_FRAMES = 200` | The sample only covers part of the store's day | A longer capture would reveal more unique shoppers and more rare paths |
| Pretrained YOLO11n (no retail fine-tune) | Model wasn't trained on in-store crowds | A retail fine-tune would likely improve detection in occluded scenes |
| Fixed rectangular zones | Zone quality depends on the operator placing them correctly | Interactive zone drawing on a calibration frame would help |
| One camera, one sequence | No cross-camera ID matching | Production needs re-ID across cameras for full-store journeys |
| Passers = all tracked IDs | Over-counts "people near the display" | A near-display corridor polygon would scope passers correctly |
| Point-in-polygon for zone membership | Hard boundary; no fuzzy membership | Probabilistic zone membership (Gaussian) handles noise better |
"""
)


# -----------------------------------------------------------------------------
# Limitations
# -----------------------------------------------------------------------------
st.markdown(
    """
## 4. Limitations

**Identity persistence** — ByteTrack keeps IDs while a person stays
visible. A long occlusion can swap IDs. The mall dataset has a top-down
camera with few occlusions, so this is fine; an aisle camera would need
stronger re-identification.

**Zone rigidity** — zones are hard rectangles. A person straddling the
entrance/center boundary will be assigned to whichever polygon their
foot point falls inside. This is consistent but not always intuitive.

**Camera FPS** — the dataset is a sequence of frames, not a true video.
The 1.5 fps assumption is reasonable for foot-traffic observation but
should be replaced with a measured camera FPS in production.

**Single viewpoint** — no cross-camera handoff. In a multi-camera store
the same person gets different IDs on different cameras.

**No business context** — the system counts people and time. It does
not know who buys, who picks up a product, or who talks to a store
associate. Those signals require additional sensors or POS integration.

**Sample size** — 200 frames is enough to demonstrate the pipeline, not
enough to draw business conclusions. A real deployment would run on
weeks of footage.
"""
)


# -----------------------------------------------------------------------------
# What would be different in production
# -----------------------------------------------------------------------------
st.markdown(
    """
## 5. What production would add

- Camera calibration and measured FPS (not assumed)
- Retail-specific detector fine-tune
- Re-identification across cameras
- Live streaming + GPU inference
- Interactive zone drawing
- POS / transaction join for conversion analytics
- Alerting (e.g. "queue at checkout > 5 people for > 2 min")
- A/B testing infrastructure for layout changes

This POC demonstrates that the building blocks all work end-to-end on a
sample dataset. The next step is hardening each block, not inventing
new ones.
"""
)


# -----------------------------------------------------------------------------
# Try it yourself
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🛠️ Run it yourself")
st.code(
    """
# Install
pip install -r requirements.txt

# Process a folder of frames (output saved as JSON + CSV)
python scripts/process_video.py --frames path/to/frames --out results/

# Launch the dashboard locally
streamlit run app.py
    """,
    language="bash",
)
st.caption(
    "On Streamlit Community Cloud the free tier is CPU-only, so re-running the "
    "detector on a fresh video upload is slow. Locally with a GPU, a 200-frame "
    "video runs in ~10 seconds."
)
