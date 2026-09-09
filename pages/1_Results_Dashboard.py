"""
Results Dashboard - pre-computed analytics for the bundled sample video.

Loads `assets/mall_sample_results.json` (cached on first deploy) and renders
the full set of business metrics.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import pipeline
import styles


st.set_page_config(
    page_title="Results Dashboard - Retail Analytics",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231e3a8a'/%3E%3Ctext x='50' y='68' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ER%3C/text%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()


HERE = Path(__file__).parent.parent
ASSETS = HERE / "assets"


# -----------------------------------------------------------------------------
# Color palette (consistent across charts)
# -----------------------------------------------------------------------------
PALETTE = {
    "primary":   "#1e3a8a",
    "accent":    "#3b82f6",
    "warm":      "#ea580c",
    "green":     "#16a34a",
    "muted":     "#94a3b8",
    "grid":      "#e2e8f0",
    "text":      "#0f172a",
}
ZONE_COLORS_HEX = {
    "entrance":    "#f59e0b",
    "center":      "#06b6d4",
    "storefronts": "#ef4444",
    "checkout":    "#a855f7",
    "display_a":   "#22c55e",
    "display_b":   "#ec4899",
}


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


result = load_sample_results()
if result is None:
    st.error(
        "Sample results file `assets/mall_sample_results.json` not found. "
        "Run `python scripts/build_sample_assets.py` to generate it, then restart."
    )
    st.stop()


# -----------------------------------------------------------------------------
# Sidebar with quick context
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Sample context")
    st.metric("Frames", f"{result.n_frames_processed}")
    st.metric("Duration", f"{result.n_frames_processed / result.fps:.0f}s")
    st.metric("Resolution", f"{result.width}x{result.height}")
    st.metric("FPS", f"{result.fps}")
    st.markdown("---")
    st.markdown("## Tab guide")
    st.markdown(
        """
- **Overview** - top KPIs
- **Journey** - footfall & transitions
- **Engagement** - display metrics
- **Data** - raw tables & downloads
        """
    )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
styles.hero(
    "Results Dashboard",
    f"Pre-computed analytics on the {result.n_frames_processed}-frame sample video "
    f"({result.n_frames_processed / result.fps:.0f} seconds at {result.fps} fps).",
)


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab_overview, tab_journey, tab_engagement, tab_data = st.tabs([
    "Overview",
    "Customer Journey",
    "Display Engagement",
    "Data & Downloads",
])


# =============================================================================
# Tab 1: Overview
# =============================================================================
with tab_overview:
    styles.section("Top-line numbers")
    styles.interpretation(
        "Headline KPIs. Use these in an exec summary slide. The 'Top display' "
        "is whichever display (A or B) has the higher average dwell time on this sample."
    )

    n_shoppers = int(result.tracks_df["track_id"].nunique()) if len(result.tracks_df) else 0
    total_visits = int(result.footfall.sum())
    avg_dwell = float(result.display_summary["avg_dwell_sec"].mean()) if len(result.display_summary) else 0
    best_display = (
        result.display_summary.loc[result.display_summary["avg_dwell_sec"].idxmax(), "display"]
        if len(result.display_summary) else "-"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unique shoppers", f"{n_shoppers}")
    c2.metric("Total zone visits", f"{total_visits}")
    c3.metric("Avg display dwell", f"{avg_dwell:.1f}s")
    c4.metric("Top display (dwell)", best_display)

    st.markdown("---")

    styles.section("Zone layout")
    styles.interpretation(
        "Reference map of every zone the analytics are computed against. The four "
        "horizontal bands are journey zones (entrance -> checkout). The two green/"
        "pink rectangles are display zones A and B."
    )

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        zone_ref_path = ASSETS / "zone_reference.jpg"
        if zone_ref_path.exists():
            st.image(str(zone_ref_path), use_container_width=True)
        else:
            st.info("Zone reference image not found.")

    with right:
        styles.section("Footfall by zone")
        styles.interpretation(
            "Unique shoppers observed in each journey zone. A shopper standing in "
            "the same zone across many frames still counts as one visitor."
        )
        footfall_df = result.footfall.reset_index()
        footfall_df.columns = ["zone", "unique_visitors"]
        fig = px.bar(
            footfall_df, x="zone", y="unique_visitors",
            color="zone", color_discrete_map=ZONE_COLORS_HEX,
            text="unique_visitors",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False, height=380,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Unique shoppers",
            yaxis=dict(gridcolor=PALETTE["grid"]),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# Tab 2: Customer Journey
# =============================================================================
with tab_journey:
    styles.section("Zone-to-zone transitions")
    styles.interpretation(
        "How shoppers moved between zones. Rows are origins, columns are "
        "destinations. Hover any cell for the exact count. Empty cells mean no "
        "shopper made that particular transition in the sample."
    )

    trans = result.transitions.copy()
    zone_names = trans.index.tolist()

    fig = go.Figure(data=go.Heatmap(
        z=trans.values,
        x=zone_names,
        y=zone_names,
        colorscale=[[0, "#f8fafc"], [1, PALETTE["primary"]]],
        text=trans.values,
        texttemplate="%{text}",
        textfont={"size": 14, "color": PALETTE["text"]},
        hovertemplate="From <b>%{y}</b><br>To <b>%{x}</b><br>"
                      "<b>%{z}</b> transitions<extra></extra>",
        colorbar=dict(title="count", tickfont=dict(size=11)),
    ))
    fig.update_layout(
        height=480,
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title="To zone",
        yaxis_title="From zone",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    styles.section("What the transitions tell us")
    styles.interpretation(
        "Plain-language summary of the most common shopper paths in the sample. "
        "These are read directly off the matrix above."
    )

    # Compute top 3 transitions
    pairs = []
    for i, a in enumerate(zone_names):
        for j, b in enumerate(zone_names):
            if a != b and trans.values[i, j] > 0:
                pairs.append((a, b, int(trans.values[i, j])))
    pairs.sort(key=lambda x: -x[2])
    top3 = pairs[:3]

    if top3:
        cards = st.columns(len(top3))
        for col, (a, b, n) in zip(cards, top3):
            with col:
                st.metric(
                    label=f"{a} -> {b}",
                    value=f"{n}",
                    help=f"Number of shoppers who moved from {a} to {b}",
                )
    else:
        st.info("No zone-to-zone transitions detected in the sample.")


# =============================================================================
# Tab 3: Display Engagement
# =============================================================================
with tab_engagement:
    styles.section("Per-display engagement")
    styles.interpretation(
        "Comparison of the two retail displays. **Passers** is the total unique "
        "shopper count in the footage (a simplification - see Methodology). "
        "**Engagement rate** is the share of passers who entered the display zone. "
        "**Dwell** is in seconds, computed as frames inside the display / assumed FPS."
    )

    ds = result.display_summary.copy()
    ds["engagement_pct"] = (ds["engagement_rate"] * 100).round(1)
    ds["display_label"] = ds["display"].str.replace("_", " ").str.title()

    # Two side-by-side bar charts
    c1, c2 = st.columns(2, gap="large")

    with c1:
        styles.section("Average dwell time")
        styles.interpretation(
            "Higher = more engaging. Compare across displays to see which one "
            "holds shoppers longer on average."
        )
        fig = px.bar(
            ds, x="display_label", y="avg_dwell_sec",
            color="display", color_discrete_map={"display_a": "#22c55e", "display_b": "#ec4899"},
            text=ds["avg_dwell_sec"].round(1),
        )
        fig.update_traces(textposition="outside", texttemplate="%{text}s")
        fig.update_layout(
            showlegend=False, height=360,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Seconds",
            yaxis=dict(gridcolor=PALETTE["grid"]),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        styles.section("Engagement rate")
        styles.interpretation(
            "Share of all shoppers in the footage who entered this display zone. "
            "Higher means the display pulls in more foot traffic, not just longer "
            "stays from a few people."
        )
        fig = px.bar(
            ds, x="display_label", y="engagement_pct",
            color="display", color_discrete_map={"display_a": "#22c55e", "display_b": "#ec4899"},
            text=ds["engagement_pct"],
        )
        fig.update_traces(textposition="outside", texttemplate="%{text}%")
        fig.update_layout(
            showlegend=False, height=360,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Percent",
            yaxis=dict(gridcolor=PALETTE["grid"]),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    styles.section("Full per-display table")
    styles.interpretation(
        "All engagement metrics side by side. The 'passers' column normalizes "
        "both displays against the same shopper population, so the rates are "
        "directly comparable."
    )
    display_df = ds[[
        "display_label", "passers", "zone_entries",
        "engagement_pct", "avg_dwell_sec", "max_dwell_sec",
    ]].rename(columns={
        "display_label": "Display",
        "passers": "Passers",
        "zone_entries": "Entries",
        "engagement_pct": "Engagement %",
        "avg_dwell_sec": "Avg dwell (s)",
        "max_dwell_sec": "Max dwell (s)",
    })
    st.dataframe(
        display_df.style.format({
            "Engagement %": "{:.1f}%",
            "Avg dwell (s)": "{:.2f}",
            "Max dwell (s)": "{:.2f}",
        }),
        use_container_width=True, hide_index=True,
    )


# =============================================================================
# Tab 4: Data & Downloads
# =============================================================================
with tab_data:
    styles.section("Per-shopper journey (top 25)")
    styles.interpretation(
        "Top 25 longest-tracked shoppers. **frames_seen** is how many of the "
        "200 sample frames this person was visible. **seconds_seen** converts "
        "to wall time using the 1.5 fps assumption."
    )

    track_lengths = (
        result.tracks_df.groupby("track_id").size()
        .sort_values(ascending=False).head(25).reset_index()
    )
    track_lengths.columns = ["track_id", "frames_seen"]
    track_lengths["seconds_seen"] = (track_lengths["frames_seen"] / result.fps).round(1)
    st.dataframe(track_lengths, use_container_width=True, hide_index=True)

    st.markdown("---")

    styles.section("Download data")
    styles.interpretation(
        "All raw outputs as CSV. Drop these into Excel, Tableau, or a slide deck."
    )

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Trajectories CSV",
        data=result.tracks_df.to_csv(index=False).encode("utf-8"),
        mime="text/csv",
        use_container_width=True,
        help="Per-frame detection records for every tracked shopper.",
    )
    d2.download_button(
        "Transitions CSV",
        data=result.transitions.to_csv().encode("utf-8"),
        mime="text/csv",
        use_container_width=True,
        help="Zone-to-zone transition counts matrix.",
    )
    d3.download_button(
        "Display summary CSV",
        data=result.display_summary.to_csv(index=False).encode("utf-8"),
        mime="text/csv",
        use_container_width=True,
        help="Per-display engagement summary.",
    )
