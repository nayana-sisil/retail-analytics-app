"""
Results Dashboard - the numbers from the sample video.

The data was calculated at build time and is shipped with the app, so the
page loads instantly. Use the tabs and controls to slice the data.
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
    page_title="Where People Went - Retail Analytics",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231e3a8a'/%3E%3Ctext x='50' y='68' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ER%3C/text%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()


HERE = Path(__file__).parent.parent
ASSETS = HERE / "assets"


# Colors for the four store areas + two displays (kept in sync with the hero image)
AREA_COLORS = {
    "entrance":    "#f59e0b",
    "center":      "#06b6d4",
    "storefronts": "#ef4444",
    "checkout":    "#a855f7",
    "display_a":   "#22c55e",
    "display_b":   "#ec4899",
}


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
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## About the sample")
    st.caption(
        f"About {result.n_frames_processed / result.fps:.0f} seconds of mall "
        f"footage, analyzed at {result.fps} snapshots per second."
    )
    st.markdown("---")
    st.markdown("## Tab guide")
    st.markdown(
        """
- **Overview** - the headline numbers
- **Where People Went** - area visits and movement
- **Did Displays Work** - how the displays did
- **Numbers & Downloads** - tables and CSVs
        """
    )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
styles.hero(
    "Where People Went",
    f"Headline numbers from the sample video "
    f"({result.n_frames_processed} snapshots, "
    f"~{result.n_frames_processed / result.fps:.0f} seconds of footage).",
)


# -----------------------------------------------------------------------------
# First-time explainer
# -----------------------------------------------------------------------------
with st.expander("First time here? How to read these numbers", expanded=False):
    st.markdown(
        """
- **Different people** = how many unique shoppers the system spotted in the footage.
- **Total visits to areas** = sum of every person counted in every area. One
  person visiting two areas counts twice.
- **Avg time at a display** = average seconds a person spent inside Display A
  or Display B.
- **Busiest area** = which of the four store areas had the most unique visitors.
        """
    )


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab_overview, tab_journey, tab_engagement, tab_data = st.tabs([
    "Overview",
    "Where People Went",
    "Did Displays Work",
    "Numbers & Downloads",
])


# =============================================================================
# Tab 1: Overview
# =============================================================================
with tab_overview:
    styles.section("Headline numbers")
    styles.interpretation(
        "These are the four numbers worth quoting in any executive summary. "
        "Everything else on this page is built from the same underlying data."
    )

    n_shoppers = int(result.tracks_df["track_id"].nunique()) if len(result.tracks_df) else 0
    total_visits = int(result.footfall.sum())
    avg_dwell = float(result.display_summary["avg_dwell_sec"].mean()) if len(result.display_summary) else 0
    best_display = (
        result.display_summary.loc[result.display_summary["avg_dwell_sec"].idxmax(), "display_label"]
        if len(result.display_summary) and "display_label" in result.display_summary.columns
        else (
            result.display_summary.loc[result.display_summary["avg_dwell_sec"].idxmax(), "display"]
            if len(result.display_summary) else "-"
        )
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Different people", f"{n_shoppers}")
    c2.metric("Total visits to areas", f"{total_visits}")
    c3.metric("Avg time at a display", f"{avg_dwell:.1f}s")
    c4.metric(
        "Top display (longer stays)",
        str(best_display).replace("_", " ").title(),
    )

    st.markdown("---")

    styles.section("How many people in each area")
    styles.interpretation(
        "Each colored bar is one of the four store areas. Taller means "
        "more unique visitors. A shopper who stood in the same area for "
        "many snapshots still counts as one visitor."
    )

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        zone_ref_path = ASSETS / "zone_reference.jpg"
        if zone_ref_path.exists():
            st.image(str(zone_ref_path), use_container_width=True)

    with right:
        chart_kind = st.radio(
            "Chart type",
            ["Bar", "Donut"],
            horizontal=True,
            label_visibility="collapsed",
        )
        footfall_df = result.footfall.reset_index()
        footfall_df.columns = ["area", "unique_visitors"]
        footfall_df = footfall_df[footfall_df["unique_visitors"] > 0]

        if chart_kind == "Bar":
            fig = px.bar(
                footfall_df, x="area", y="unique_visitors",
                color="area", color_discrete_map=AREA_COLORS,
                text="unique_visitors",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                showlegend=False, height=380,
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis_title=None, yaxis_title="Unique visitors",
                yaxis=dict(gridcolor="#e2e8f0"),
                margin=dict(l=10, r=10, t=20, b=10),
            )
        else:
            fig = px.pie(
                footfall_df, names="area", values="unique_visitors",
                color="area", color_discrete_map=AREA_COLORS,
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
# Tab 2: Where People Went
# =============================================================================
with tab_journey:
    styles.section("How many people in each area")
    styles.interpretation(
        "Same data as the bar chart on the Overview tab. Use the filter to "
        "focus on a subset of areas."
    )

    all_zones = result.footfall.index.tolist()
    selected_zones = st.multiselect(
        "Areas to show",
        options=all_zones,
        default=all_zones,
        help="Uncheck an area to hide it from both the bar chart and the "
             "movement grid below.",
        format_func=lambda z: z.replace("_", " ").title(),
    )
    if not selected_zones:
        st.warning("Pick at least one area.")
        st.stop()

    ff = result.footfall.reset_index()
    ff.columns = ["area", "unique_visitors"]
    ff = ff[ff["area"].isin(selected_zones)]

    c_bar, c_kpi = st.columns([3, 1])
    with c_bar:
        fig = px.bar(
            ff, x="area", y="unique_visitors",
            color="area", color_discrete_map=AREA_COLORS,
            text="unique_visitors",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False, height=300,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Unique visitors",
            yaxis=dict(gridcolor="#e2e8f0"),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    with c_kpi:
        st.metric("Areas shown", f"{len(selected_zones)}")
        st.metric("Total visitors", f"{int(ff['unique_visitors'].sum())}")
        st.metric(
            "Busiest area",
            ff.loc[ff["unique_visitors"].idxmax(), "area"].title() if len(ff) else "-",
        )

    st.markdown("---")

    styles.section("How people moved between areas")
    styles.interpretation(
        "Each row is an area someone started in. Each column is the area "
        "they went to next. Bigger numbers mean that path was taken more "
        "often. Hover any cell for the exact count."
    )

    trans = result.transitions.copy()
    trans = trans.loc[
        trans.index.isin(selected_zones), trans.columns.isin(selected_zones)
    ]
    zone_names = [z.replace("_", " ").title() for z in trans.index.tolist()]

    fig = go.Figure(data=go.Heatmap(
        z=trans.values,
        x=zone_names,
        y=zone_names,
        colorscale=[[0, "#f8fafc"], [1, "#1e3a8a"]],
        text=trans.values,
        texttemplate="%{text}",
        textfont={"size": 14, "color": "#0f172a"},
        hovertemplate="From <b>%{y}</b><br>To <b>%{x}</b><br>"
                      "<b>%{z}</b> trips<extra></extra>",
        colorbar=dict(title="trips", tickfont=dict(size=11)),
    ))
    fig.update_layout(
        height=480,
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title="Went to",
        yaxis_title="Came from",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    styles.section("Most common paths")
    styles.interpretation(
        "The three paths shoppers took most often. Read straight off the "
        "grid above."
    )

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
                    value=f"{n} trips",
                    help=f"Number of times a shopper moved from {a} to {b}",
                )
    else:
        st.info("No movements between the selected areas.")


# =============================================================================
# Tab 3: Did Displays Work
# =============================================================================
with tab_engagement:
    styles.section("How the displays did")
    styles.interpretation(
        "Pick one or both displays. **People who walked by** is the total "
        "of every unique person the system spotted in the footage. "
        "**Share who stopped** is the fraction of those people who stepped "
        "into the display's colored rectangle. **Time spent** is how long "
        "they stayed once they were inside."
    )

    ds = result.display_summary.copy()
    ds["share_pct"] = (ds["engagement_rate"] * 100).round(1)
    ds["display_label"] = ds["display"].str.replace("_", " ").str.title()

    display_choice = st.multiselect(
        "Displays to compare",
        options=ds["display_label"].tolist(),
        default=ds["display_label"].tolist(),
        help="Uncheck a display to hide it. At least one must be selected.",
    )
    if not display_choice:
        st.warning("Pick at least one display.")
        st.stop()
    ds_filtered = ds[ds["display_label"].isin(display_choice)]

    color_map_label = {"Display A": "#22c55e", "Display B": "#ec4899"}

    c1, c2 = st.columns(2, gap="large")

    with c1:
        styles.section("Share who stopped")
        styles.interpretation(
            "Out of everyone who walked past the display, what fraction "
            "actually stepped inside. Higher = more pull."
        )
        fig = px.bar(
            ds_filtered, x="display_label", y="share_pct",
            color="display_label", color_discrete_map=color_map_label,
            text=ds_filtered["share_pct"],
        )
        fig.update_traces(textposition="outside", texttemplate="%{text}%")
        fig.update_layout(
            showlegend=False, height=360,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Share of people who walked by",
            yaxis=dict(gridcolor="#e2e8f0"),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        styles.section("Average time spent")
        styles.interpretation(
            "Once a shopper stepped inside the display, how long did they "
            "stay on average. Higher = the display holds attention."
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
            yaxis=dict(gridcolor="#e2e8f0"),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    if len(display_choice) == 2:
        st.markdown("---")
        styles.section("Side-by-side")
        styles.interpretation(
            "Normalized comparison. Each bar shows the value as a share of "
            "the better-performing display for that metric, so the winner "
            "is obvious at a glance."
        )
        norm = ds.set_index("display_label")[["share_pct", "avg_dwell_sec"]].copy()
        for col in norm.columns:
            mx = norm[col].max()
            if mx > 0:
                norm[col] = (norm[col] / mx * 100).round(1)
        norm = norm.reset_index().melt(
            id_vars="display_label", var_name="metric", value_name="share_pct"
        )
        metric_labels = {"share_pct": "Share who stopped", "avg_dwell_sec": "Avg time spent"}
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
            yaxis=dict(gridcolor="#e2e8f0", range=[0, 115]),
            legend_title="",
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    styles.section("Full display numbers")
    styles.interpretation(
        "All the numbers behind the charts above. 'People who walked by' is "
        "the same for both displays, so the rates are directly comparable."
    )
    display_df = ds[[
        "display_label", "passers", "zone_entries",
        "share_pct", "avg_dwell_sec", "max_dwell_sec",
    ]].rename(columns={
        "display_label":    "Display",
        "passers":          "People who walked by",
        "zone_entries":     "How many entered",
        "share_pct":        "Share who stopped",
        "avg_dwell_sec":    "Avg time spent (s)",
        "max_dwell_sec":    "Longest stay (s)",
    })
    st.dataframe(
        display_df.style.format({
            "Share who stopped": "{:.1f}%",
            "Avg time spent (s)": "{:.2f}",
            "Longest stay (s)": "{:.2f}",
        }),
        use_container_width=True, hide_index=True,
    )


# =============================================================================
# Tab 4: Numbers & Downloads
# =============================================================================
with tab_data:
    styles.section("Per-person summary")
    styles.interpretation(
        "Top N longest-tracked people. **Snapshots seen** is how many of "
        "the 200 frames the system spotted this person in. **Seconds seen** "
        "is that number converted to wall time using the 1.5 snapshots/sec "
        "rate."
    )

    track_lengths = (
        result.tracks_df.groupby("track_id").size()
        .reset_index().rename(columns={0: "snapshots_seen"})
    )
    track_lengths.columns = ["person", "snapshots_seen"]
    track_lengths["seconds_seen"] = (track_lengths["snapshots_seen"] / result.fps).round(1)

    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 2])
    with ctrl1:
        top_n = st.slider("Show top N people", 5, min(50, len(track_lengths)), 25)
    with ctrl2:
        sort_by = st.selectbox("Sort by", ["snapshots_seen", "person", "seconds_seen"])
    with ctrl3:
        ascending = st.checkbox("Ascending", value=False)

    track_lengths_sorted = track_lengths.sort_values(sort_by, ascending=ascending).head(top_n)
    st.dataframe(track_lengths_sorted, use_container_width=True, hide_index=True)

    st.markdown("---")

    styles.section("How long are people usually in the footage?")
    styles.interpretation(
        "Most shoppers appear in only a handful of snapshots - they walk "
        "through quickly. A long tail stay longer."
    )
    fig = px.histogram(
        track_lengths, x="snapshots_seen", nbins=20,
        color_discrete_sequence=["#3b82f6"],
    )
    fig.update_layout(
        height=280, plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title="Snapshots seen",
        yaxis_title="Number of people",
        showlegend=False,
        yaxis=dict(gridcolor="#e2e8f0"),
        xaxis=dict(gridcolor="#e2e8f0"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    styles.section("Download the numbers")
    styles.interpretation(
        "All raw outputs as CSV. Drop these into Excel or a slide deck."
    )

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Trajectories CSV",
        data=result.tracks_df.to_csv(index=False).encode("utf-8"),
        mime="text/csv",
        use_container_width=True,
        help="One row per person per snapshot. Use to build your own analysis.",
    )
    d2.download_button(
        "Trips between areas CSV",
        data=result.transitions.to_csv().encode("utf-8"),
        mime="text/csv",
        use_container_width=True,
        help="Counts of how people moved between areas.",
    )
    d3.download_button(
        "Display numbers CSV",
        data=result.display_summary.to_csv(index=False).encode("utf-8"),
        mime="text/csv",
        use_container_width=True,
        help="Per-display summary.",
    )
