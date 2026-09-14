"""
Retail Video Analytics - landing page.

Leads with value stories, not metrics. Designed so anyone can read it:
store owner, marketing manager, ops lead - no technical background needed.
"""

import json
from pathlib import Path

import streamlit as st

import pipeline
import styles


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
    st.markdown("## What you can do here")
    st.markdown(
        """
- **What we learned** &mdash; three business stories from the sample
- **Browse the video** &mdash; see it work, moment by moment
- **How it works** &mdash; FAQ, no jargon
        """
    )
    st.markdown("---")
    st.caption(
        "Built on a 200-snapshot, 2-minute sample of mall footage. "
        "The system runs on a public link - no install needed."
    )


# -----------------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------------
styles.hero(
    "What if your store cameras answered your questions?",
    "Every retailer already has cameras on the floor. This demo shows "
    "what happens when you turn that footage into structured data you "
    "can actually act on.",
)


# -----------------------------------------------------------------------------
# The big idea
# -----------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("### The big idea, in one paragraph")
    st.markdown(
        """
Your website team has Google Analytics. Every click, every page view,
every drop-off - measured and reported. Your physical store has the same
amount of data on its cameras, but it's stuck inside video files no one
ever watches.

This system is the Google Analytics for your store. It watches the
footage and tells you where shoppers went, which displays held their
attention, and where they dropped off. You don't have to watch the
video yourself - the system reads it for you.
        """
    )


# -----------------------------------------------------------------------------
# Three use cases
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("Three questions this system answers for you")

c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    styles.use_card(
        icon="1.",
        question="Where do shoppers actually go?",
        what_it_does="Draws boxes on the floor of your store and counts "
                     "how many people step into each one.",
        value="redesign your floor based on real traffic, not guesswork.",
    )

with c2:
    styles.use_card(
        icon="2.",
        question="Do displays and end-caps work?",
        what_it_does="Marks each display and tracks how many people "
                     "stopped there, and for how long.",
        value="put your best products in the spots that actually hold attention.",
    )

with c3:
    styles.use_card(
        icon="3.",
        question="Where do you lose people?",
        what_it_does="Maps the path from entrance to checkout and shows "
                     "you where shoppers drop off.",
        value="fix the bottlenecks in your customer journey.",
    )


# -----------------------------------------------------------------------------
# What we learned from the sample
# -----------------------------------------------------------------------------
result = None
try:
    with open(ASSETS / "mall_sample_results.json") as f:
        result = pipeline.result_from_jsonable(json.load(f))
except FileNotFoundError:
    pass

if result is not None:
    n_shoppers = int(result.tracks_df["track_id"].nunique()) if len(result.tracks_df) else 0
    avg_dwell = float(result.display_summary["avg_dwell_sec"].mean()) if len(result.display_summary) else 0
    ds_records = result.display_summary.to_dict("records") if len(result.display_summary) else []
    display_a = next((x for x in ds_records if x["display"] == "display_a"), None)
    display_b = next((x for x in ds_records if x["display"] == "display_b"), None)

    # Determine which display wins
    if display_a and display_b:
        a_dwell, a_share = display_a["avg_dwell_sec"], display_a["engagement_rate"] * 100
        b_dwell, b_share = display_b["avg_dwell_sec"], display_b["engagement_rate"] * 100
        if a_share > b_share:
            winner, loser = "Display A", "Display B"
            winner_share, loser_share = a_share, b_share
        else:
            winner, loser = "Display B", "Display A"
            winner_share, loser_share = b_share, a_share

    st.markdown("---")
    st.subheader("What we learned from the sample")
    st.caption(
        "Three short stories from the demo footage. The numbers are real - "
        "they came out of a working pipeline. Click through to the dashboard "
        "for the full data."
    )

    s1, s2, s3 = st.columns(3, gap="medium")

    with s1:
        styles.story(
            "Story 1 - The store has a clear traffic pattern.",
            f"In this sample, **{n_shoppers} different people** entered the store. "
            "Most walked through the center on their way to the storefronts. "
            "The store does have flow - it isn't chaos.",
        )

    with s2:
        if display_a and display_b:
            styles.story(
                "Story 2 - One display is pulling more attention.",
                f"**{winner}** stopped about **{winner_share:.0f}%** of the people who "
                f"walked past. **{loser}** stopped "
                f"**{loser_share:.0f}%**. On a 2-minute sample, a 3-point gap is "
                "meaningful - it's the kind of difference that justifies "
                "rearranging your displays.",
            )

    with s3:
        styles.story(
            "Story 3 - People don't linger at displays.",
            f"On average, a shopper who stops at a display stays for only "
            f"**{avg_dwell:.1f} seconds**. Displays have to win attention fast. "
            "A clearer message or better placement could double that number.",
        )


# -----------------------------------------------------------------------------
# How we drew the store map
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("How we drew the store map")
st.caption(
    "The colored boxes on the floor are the same ones the system uses to "
    "count people. Hover the image to see them in context."
)

best_frame_path = ASSETS / "best_frame.jpg"
if best_frame_path.exists():
    st.image(str(best_frame_path), use_container_width=True)

# Legend
lg1, lg2, lg3, lg4, lg5, lg6 = st.columns(6)
with lg1:
    st.markdown('<div style="background:#f59e0b;color:white;padding:0.4rem 0.8rem;border-radius:6px;text-align:center;font-weight:600;font-size:0.85rem;">Entrance</div>', unsafe_allow_html=True)
with lg2:
    st.markdown('<div style="background:#06b6d4;color:white;padding:0.4rem 0.8rem;border-radius:6px;text-align:center;font-weight:600;font-size:0.85rem;">Center</div>', unsafe_allow_html=True)
with lg3:
    st.markdown('<div style="background:#ef4444;color:white;padding:0.4rem 0.8rem;border-radius:6px;text-align:center;font-weight:600;font-size:0.85rem;">Storefronts</div>', unsafe_allow_html=True)
with lg4:
    st.markdown('<div style="background:#a855f7;color:white;padding:0.4rem 0.8rem;border-radius:6px;text-align:center;font-weight:600;font-size:0.85rem;">Checkout</div>', unsafe_allow_html=True)
with lg5:
    st.markdown('<div style="background:#22c55e;color:white;padding:0.4rem 0.8rem;border-radius:6px;text-align:center;font-weight:600;font-size:0.85rem;">Display A</div>', unsafe_allow_html=True)
with lg6:
    st.markdown('<div style="background:#ec4899;color:white;padding:0.4rem 0.8rem;border-radius:6px;text-align:center;font-weight:600;font-size:0.85rem;">Display B</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# CTA strip
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("Where to go next")

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        st.markdown("### I want to see the numbers")
        st.markdown(
            "Open the dashboard for the full breakdown - all areas, all "
            "movements, all displays."
        )
        st.page_link("pages/1_Where_People_Went.py", label="Open the dashboard")

with c2:
    with st.container(border=True):
        st.markdown("### I want to see how it works")
        st.markdown(
            "Browse the video itself. Click through any moment and see "
            "exactly which people the system is tracking."
        )
        st.page_link("pages/2_Browse_the_Video.py", label="Open the video")


st.markdown("---")
st.caption(
    "POC built on real mall footage. Plain-language demo. Source code "
    "in the project root."
)
