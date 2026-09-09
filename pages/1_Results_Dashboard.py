"""
Results Dashboard - analytics for the bundled sample video.

The numbers are computed at build time and shipped as JSON with the app, so
the page loads instantly. Use the controls on each tab to slice the data.
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
# Sidebar with sample context
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
- **Overview** - top KPIs and zone map
- **Journey** - footfall and transitions
- **Engagement** - per-display metrics
- **Data** - raw tables and downloads
        """
    )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
styles.hero(
    "Results Dashboard",
    f"Analytics for the {result.n_frames_processed}-frame sample video "
    f"({result.n_frames_processed / result.fps:.0f} seconds at {result.fps} fps). "
    f"Use the controls on each tab to slice the data.",
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
        "Headline KPIs. Use these in an exec summary slide. 'Top display' "
        "is whichever display has the higher average dwell time on this sample."
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

    styles.section("Zone layout and footfall")
    styles.interpretation(
        "Reference map of every zone the analytics are computed against. The "
        "four horizontal bands are journey zones; the two rectangles are "
        "displays A and B. The bar chart on the right shows unique shoppers "
        "observed in each journey zone."
    )

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        zone_ref_path = ASSETS / "zone_reference.jpg"
        if zone_ref_path.exists():
            st.image(str(zone_ref_path), use_container_width=True)
        else:
            st.info("Zone reference image not found.")

    with right:
        # Toggle: bar chart or pie chart
        chart_kind = st.radio(
            "Chart type",
            ["Bar", "Donut"],
            horizontal=True,
            label_visibility="collapsed",
        )
        footfall_df = result.footfall.reset_index()
        footfall_df.columns = ["zone", "unique_visitors"]
        footfall_df = footfall_df[footfall_df["unique_visitors"] > 0]

        if chart_kind == "Bar":
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
        else:
            fig = px.pie(
                footfall_df, names="zone", values="unique_visitors",
                color="zone", color_discrete_map=ZONE_COLORS_HEX,
                hole=0.55,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                showlegend=True, height=380,
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            )
        st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# Tab 2: Customer Journey
# =============================================================================
with tab_journey:
    styles.section("Footfall by zone")
    styles.interpretation(
        "Unique shoppers observed in each journey zone. A shopper standing in "
        "the same zone across many frames still counts as one visitor. "
        "Use the filter to focus on a subset of zones."
    )

    all_zones = result.footfall.index.tolist()
    selected_zones = st.multiselect(
        "Zones to show",
        options=all_zones,
        default=all_zones,
        help="Uncheck a zone to hide it from both the bar chart and the heatmap below.",
    )
    if not selected_zones:
        st.warning("Pick at least one zone to see the charts.")
        st.stop()

    # Footfall bar (filtered)
    ff = result.footfall.reset_index()
    ff.columns = ["zone", "unique_visitors"]
    ff = ff[ff["zone"].isin(selected_zones)]

    c_bar, c_kpi = st.columns([3, 1])
    with c_bar:
        fig = px.bar(
            ff, x="zone", y="unique_visitors",
            color="zone", color_discrete_map=ZONE_COLORS_HEX,
            text="unique_visitors",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False, height=300,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Unique shoppers",
            yaxis=dict(gridcolor=PALETTE["grid"]),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    with c_kpi:
        st.metric("Zones shown", f"{len(selected_zones)}")
        st.metric("Total visitors", f"{int(ff['unique_visitors'].sum())}")
        st.metric(
            "Busiest zone",
            ff.loc[ff["unique_visitors"].idxmax(), "zone"] if len(ff) else "-",
        )

    st.markdown("---")

    styles.section("Zone-to-zone transitions")
    styles.interpretation(
        "How shoppers moved between zones. Rows are origins, columns are "
        "destinations. Hover any cell for the exact count. Empty cells mean no "
        "shopper made that particular transition in the sample."
    )

    trans = result.transitions.copy()
    # Restrict to selected zones
    trans = trans.loc[trans.index.isin(selected_zones), trans.columns.isin(selected_zones)]
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

    styles.section("Top shopper paths")
    styles.interpretation(
        "The three most common transitions in the sample. Read directly off "
        "the matrix above."
    )

    # Compute top transitions (excluding self-loops)
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
        st.info("No zone-to-zone transitions detected in the selected zones.")


# =============================================================================
# Tab 3: Display Engagement
# =============================================================================
with tab_engagement:
    styles.section("Per-display engagement")
    styles.interpretation(
        "Pick one or both displays. **Passers** is the total unique shopper "
        "count in the footage (a simplification - see Methodology). "
        "**Engagement rate** is the share of passers who entered the display zone. "
        "**Dwell** is in seconds, computed as frames inside the display / assumed FPS."
    )

    ds = result.display_summary.copy()
    ds["engagement_pct"] = (ds["engagement_rate"] * 100).round(1)
    ds["display_label"] = ds["display"].str.replace("_", " ").str.title()

    display_choice = st.multiselect(
        "Displays to compare",
        options=ds["display_label"].tolist(),
        default=ds["display_label"].tolist(),
        help="Uncheck a display to hide it from the charts. At least one must be selected.",
    )
    if not display_choice:
        st.warning("Pick at least one display.")
        st.stop()
    ds_filtered = ds[ds["display_label"].isin(display_choice)]

    # Two side-by-side bar charts
    c1, c2 = st.columns(2, gap="large")

    color_map_label = {
        "Display A": "#22c55e",
        "Display B": "#ec4899",
    }

    with c1:
        styles.section("Average dwell time")
        styles.interpretation(
            "Higher = more engaging. Compare across displays to see which one "
            "holds shoppers longer on average."
        )
        fig = px.bar(
            ds_filtered, x="display_label", y="avg_dwell_sec",
            color="display_label", color_discrete_map=color_map_label,
            text=ds_filtered["avg_dwell_sec"].round(1),
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
            "Share of all shoppers in the footage who entered this display "
            "zone. Higher means the display pulls in more foot traffic, not "
            "just longer stays from a few people."
        )
        fig = px.bar(
            ds_filtered, x="display_label", y="engagement_pct",
            color="display_label", color_discrete_map=color_map_label,
            text=ds_filtered["engagement_pct"],
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

    # Single combined comparison plot when both selected
    if len(display_choice) == 2:
        st.markdown("---")
        styles.section("Side-by-side comparison")
        styles.interpretation(
            "Normalized comparison across both displays. Bars show the value "
            "as a share of the maximum across the two displays, so you can "
            "see which one wins each metric at a glance."
        )
        norm = ds.set_index("display_label")[["engagement_pct", "avg_dwell_sec"]].copy()
        # Normalize each column to 0-100 within the pair
        for col in norm.columns:
            mx = norm[col].max()
            if mx > 0:
                norm[col] = (norm[col] / mx * 100).round(1)
        norm = norm.reset_index().melt(
            id_vars="display_label", var_name="metric", value_name="share_pct"
        )
        metric_labels = {"engagement_pct": "Engagement rate", "avg_dwell_sec": "Avg dwell"}
        norm["metric"] = norm["metric"].map(metric_labels)
        fig = px.bar(
            norm, x="metric", y="share_pct", color="display_label",
            barmode="group", text="share_pct",
            color_discrete_map=color_map_label,
        )
        fig.update_traces(textposition="outside", texttemplate="%{text:.0f}%")
        fig.update_layout(
            height=340, plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Share of best (%)",
            yaxis=dict(gridcolor=PALETTE["grid"], range=[0, 115]),
            legend_title="",
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    styles.section("Full per-display table")
    styles.interpretation(
        "All engagement metrics side by side. 'Passers' is the same for both "
        "displays since it counts every tracked shopper in the footage, so the "
        "rates are directly comparable."
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
    styles.section("Per-shopper journey")
    styles.interpretation(
        "Top N longest-tracked shoppers, sortable. **frames_seen** is how many "
        "of the 200 sample frames this person was visible. **seconds_seen** "
        "converts to wall time using the 1.5 fps assumption."
    )

    track_lengths = (
        result.tracks_df.groupby("track_id").size()
        .reset_index().rename(columns={0: "frames_seen"})
    )
    track_lengths.columns = ["track_id", "frames_seen"]
    track_lengths["seconds_seen"] = (track_lengths["frames_seen"] / result.fps).round(1)

    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
    with ctrl1:
        top_n = st.slider("Show top N shoppers", 5, min(50, len(track_lengths)), 25)
    with ctrl2:
        sort_by = st.selectbox("Sort by", ["frames_seen", "track_id", "seconds_seen"])
    with ctrl3:
        ascending = st.checkbox("Ascending", value=False)

    track_lengths_sorted = track_lengths.sort_values(sort_by, ascending=ascending).head(top_n)
    st.dataframe(track_lengths_sorted, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Quick bar chart of distribution
    styles.section("How long are shoppers usually visible?")
    styles.interpretation(
        "Distribution of frames-seen across all unique shoppers. Most shoppers "
        "are visible for only a handful of frames (they walk through quickly); "
        "a long tail stay longer."
    )
    fig = px.histogram(
        track_lengths, x="frames_seen", nbins=20,
        color_discrete_sequence=[PALETTE["accent"]],
    )
    fig.update_layout(
        height=280, plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title="Frames seen",
        yaxis_title="Number of shoppers",
        showlegend=False,
        yaxis=dict(gridcolor=PALETTE["grid"]),
        xaxis=dict(gridcolor=PALETTE["grid"]),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

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
