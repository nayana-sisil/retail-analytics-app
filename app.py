"""
Retail Video Analytics - landing page.

A public-facing demo of a computer-vision pipeline that turns retail video
into shopper journey + display engagement analytics.

Use the sidebar to navigate:
  - Where People Went        (instant, cached analytics)
  - Browse the Video        (annotated video + per-moment chart)
  - How It Works             (FAQ, plain language)
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
    st.markdown("## Pages")
    st.markdown(
        """
- [Where People Went](/Where_People_Went) &mdash; numbers + charts
- [Browse the Video](/Browse_the_Video) &mdash; annotated playback
- [How It Works](/How_It_Works) &mdash; FAQ
        """
    )
    st.markdown("---")
    st.markdown("## Sample data")
    st.caption("Mall footage, 200 snapshots, ~2 minutes")


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


# -----------------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------------
styles.hero(
    "Retail Video Analytics",
    "Turn ordinary store cameras into shopper insights anyone can read.",
)


# -----------------------------------------------------------------------------
# First-time explainer
# -----------------------------------------------------------------------------
with st.expander("First time here? What am I looking at?", expanded=False):
    st.markdown(
        """
This is a working demo built on a real store video. The system watches the
footage and answers two simple business questions:

1. **Where do shoppers go?** We drew colored boxes on the floor of the store
   to mark areas (entrance, center, storefronts, checkout). The system counts
   who visited each area.

2. **Do displays work?** Two boxes marked **Display A** and **Display B**
   mark the product displays. We track how many people stopped there and
   for how long.

The numbers on the next pages are real &mdash; computed from a 200-snapshot
sample of mall footage. Use the sidebar to navigate.
        """
    )


# -----------------------------------------------------------------------------
# About
# -----------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("### What this is, in one paragraph")
    st.markdown(
        """
Every retail floor already has cameras. This demo turns that footage into
the kind of structured data you might be used to from your website:
**who came, where they went, what they did, and where they dropped off.**
No one watches hours of tape &mdash; the system reads the footage and gives
you the numbers.
        """
    )

    st.markdown("### Where to start")
    st.markdown(
        """
1. Open **Where People Went** to see the analytics on the sample video.
   Numbers load instantly &mdash; they were calculated at build time.
2. Open **Browse the Video** to scrub through the footage yourself and see
   what the system is tracking in each moment.
3. Open **How It Works** if you want the FAQ &mdash; what's happening,
   how accurate it is, and what's next.
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
        "Top-line numbers from the sample. Every chart on the next page is "
        "built from this same data."
    )

    n_shoppers = int(result.tracks_df["track_id"].nunique()) if len(result.tracks_df) else 0
    avg_dwell = float(result.display_summary["avg_dwell_sec"].mean()) if len(result.display_summary) else 0
    busiest = (
        result.footfall.idxmax() if len(result.footfall) else "-"
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Different people", f"{n_shoppers}")
    with c2:
        st.metric("Total visits to areas", f"{int(result.footfall.sum())}")
    with c3:
        st.metric("Avg time at a display", f"{avg_dwell:.1f}s")
    with c4:
        st.metric("Busiest area", busiest.title())

    # Hero image - the cleaner zones-only version
    best_frame_path = ASSETS / "best_frame.jpg"
    if best_frame_path.exists():
        st.markdown("---")
        st.subheader("How we split the store into areas")
        styles.interpretation(
            "We drew six colored boxes on the floor: four horizontal bands "
            "(entrance, center, storefronts, checkout) and two rectangles "
            "(Display A, Display B). Every shopper counted above is one who "
            "stepped into one of these boxes."
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
    "POC. Plain-language demo. Built with Streamlit. Source code in the "
    "project root."
)
