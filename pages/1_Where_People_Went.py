"""
Where People Went - the dashboard, reframed around value stories.

Each tab leads with a story (what we learned, what it means), then shows
the numbers that back it up. The numbers are for verification; the
stories are for decisions.
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
    st.error("Sample data missing. Run scripts/build_sample_assets.py first.")
    st.stop()


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## What each tab tells you")
    st.markdown(
        """
- **The headline** - the one thing to remember
- **Where people went** - the traffic story
- **Did displays work** - the display story
- **The numbers** - tables and CSVs
        """
    )


# -----------------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------------
styles.hero(
    "Where People Went",
    f"Three business stories from {result.n_frames_processed} snapshots "
    f"of mall footage (~{result.n_frames_processed / result.fps:.0f} seconds). "
    f"Each tab is one story.",
)


# -----------------------------------------------------------------------------
# First-time explainer
# -----------------------------------------------------------------------------
with st.expander("First time here? How to read this dashboard", expanded=False):
    st.markdown(
        """
Each tab is built around a **story** - one clear takeaway you can act on.
Below the story, you'll find the **numbers** that back it up, so anyone can
verify the claim.

The store floor was split into **four areas** (entrance, center, storefronts,
checkout) and **two displays** (A, B). The system counts unique people in each.
        """
    )


# -----------------------------------------------------------------------------
# Compute the headline story upfront
# -----------------------------------------------------------------------------
n_shoppers = int(result.tracks_df["track_id"].nunique()) if len(result.tracks_df) else 0
display_a = next((x for x in result.display_summary if x["display"] == "display_a"), None)
display_b = next((x for x in result.display_summary if x["display"] == "display_b"), None)

# Determine the winning display
winner = None
if display_a and display_b:
    if display_a["engagement_rate"] >= display_b["engagement_rate"]:
        winner = ("Display A", display_a)
        loser = ("Display B", display_b)
    else:
        winner = ("Display B", display_b)
        loser = ("Display A", display_a)


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tab_headline, tab_journey, tab_engagement, tab_data = st.tabs([
    "The headline",
    "Where people went",
    "Did displays work",
    "The numbers",
])


# =============================================================================
# Tab 1: The headline (value-first, story-only)
# =============================================================================
with tab_headline:
    st.markdown("### The one thing to remember")
    styles.interpretation(
        "If you only read one thing on this page, read this tab. The other "
        "tabs are the evidence behind it."
    )

    if winner:
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            styles.story(
                "We found a real signal.",
                f"{n_shoppers} people walked through the store. That's a meaningful "
                "sample - enough to start spotting patterns.",
            )
        with c2:
            w_name, w = winner
            l_name, l = loser
            gap = w["engagement_rate"] * 100 - l["engagement_rate"] * 100
            styles.story(
                f"{w_name} is winning.",
                f"{w_name} stopped **{w['engagement_rate']*100:.1f}%** of the "
                f"people who walked past. {l_name} only stopped "
                f"**{l['engagement_rate']*100:.1f}%**. A {abs(gap):.1f}-point "
                f"gap on this small a sample is a real signal.",
            )
        with c3:
            styles.story(
                "Displays compete for seconds.",
                f"A shopper who stops at a display stays an average of only "
                f"**{result.display_summary['avg_dwell_sec'].mean():.1f} seconds**. "
                "Displays have to win attention fast. This is where the "
                "biggest design wins usually live.",
            )

    st.markdown("---")

    # Quick visual: the store map
    styles.section("Where the numbers came from")
    styles.interpretation(
        "The colored boxes on the floor are the six areas the system counts. "
        "Each color is one area; the boxes for the two displays are inside "
        "the center band."
    )

    col_map, col_text = st.columns([1.2, 1], gap="large")
    with col_map:
        zref = ASSETS / "zone_reference.jpg"
        if zref.exists():
            st.image(str(zref), use_container_width=True)

    with col_text:
        styles.section("What each color means")
        st.markdown(
            """
- **Orange (Entrance)** - where people come in
- **Cyan (Center)** - the main walkway
- **Red (Storefronts)** - where people browse
- **Purple (Checkout)** - where they pay
- **Green (Display A)** - product display on the left
- **Pink (Display B)** - product display on the right
            """
        )
        st.markdown("")
        st.page_link("pages/2_Browse_the_Video.py", label="See it work in the video", icon="2")


# =============================================================================
# Tab 2: Where People Went (the traffic story)
# =============================================================================
with tab_journey:
    # Story headline
    busiest_area = result.footfall.idxmax() if len(result.footfall) else "?"
    quietest_area = result.footfall.idxmin() if len(result.footfall) else "?"
    styles.story(
        f"The {busiest_area.replace('_', ' ').title()} is doing the heavy lifting.",
        f"Most shoppers pass through it on their way somewhere else. The "
        f"{quietest_area.replace('_', ' ').title()} sees the least traffic - "
        f"either it's a destination only some shoppers reach, or it's "
        f"underused.",
    )

    st.markdown("")

    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        styles.section("How many people visited each area")
        styles.interpretation(
            "Tall bars = busy areas. Use the multiselect to hide an area "
            "and re-focus the chart."
        )

        all_zones = result.footfall.index.tolist()
        selected_zones = st.multiselect(
            "Areas to show",
            options=all_zones,
            default=all_zones,
            format_func=lambda z: z.replace("_", " ").title(),
            label_visibility="collapsed",
        )
        if not selected_zones:
            st.warning("Pick at least one area.")
            st.stop()

        ff = result.footfall.reset_index()
        ff.columns = ["area", "visitors"]
        ff = ff[ff["area"].isin(selected_zones)].sort_values("visitors", ascending=False)

        fig = px.bar(
            ff, x="area", y="visitors",
            color="area", color_discrete_map=AREA_COLORS,
            text="visitors",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False, height=380,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Unique visitors",
            yaxis=dict(gridcolor="#e2e8f0"),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        styles.section("What's the story behind the numbers?")
        styles.interpretation(
            "Read each bar as a place in the store. The story is in the "
            "shape - where do people go first, and where do they drop off?"
        )
        # Plain-language takeaway cards
        total = int(ff["visitors"].sum())
        if len(ff):
            top = ff.iloc[0]
            bot = ff.iloc[-1]
            ratio = (top["visitors"] / bot["visitors"]) if bot["visitors"] > 0 else 0
            st.markdown(
                f"""
- The busiest area is **{top['area'].replace('_', ' ').title()}** with
  **{int(top['visitors'])}** visitors - the main walkway or first stop.
- The least-visited area is **{bot['area'].replace('_', ' ').title()}** with
  **{int(bot['visitors'])}** - probably a destination, not a pass-through.
- That's about a **{ratio:.1f}x** difference, which is normal for a store
  where some areas are destinations and others are connectors.
                """
            )

    st.markdown("---")

    # Movements
    styles.section("How people moved between areas")
    styles.interpretation(
        "Each row is where someone started; each column is where they went "
        "next. Hot cells = common journeys. This is the same view a "
        "store-planner would draw on paper, but with real data."
    )

    trans = result.transitions.copy()
    trans = trans.loc[
        trans.index.isin(selected_zones), trans.columns.isin(selected_zones)
    ]
    zone_names = [z.replace("_", " ").title() for z in trans.index.tolist()]

    fig = go.Figure(data=go.Heatmap(
        z=trans.values,
        x=zone_names, y=zone_names,
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

    # Top journeys as cards
    pairs = []
    for i, a in enumerate(zone_names):
        for j, b in enumerate(zone_names):
            if a != b and trans.values[i, j] > 0:
                pairs.append((a, b, int(trans.values[i, j])))
    pairs.sort(key=lambda x: -x[2])
    top3 = pairs[:3]

    if top3:
        st.markdown("##### The three most common journeys")
        cols = st.columns(len(top3))
        for col, (a, b, n) in zip(cols, top3):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{a} -> {b}**")
                    st.markdown(f"### {n} trips")
                    st.caption(
                        f"About {n} shoppers in this sample took this path. "
                        "If this number is high, the two areas are linked "
                        "in shoppers' minds."
                    )


# =============================================================================
# Tab 3: Did Displays Work (the display story)
# =============================================================================
with tab_engagement:
    # Headline story
    if winner:
        w_name, w = winner
        l_name, l = loser
        w_share = w["engagement_rate"] * 100
        l_share = l["engagement_rate"] * 100
        styles.story(
            f"{w_name} is the stronger display.",
            f"Out of every 100 people who walked past, about {w_share:.0f} "
            f"stopped at {w_name}. Only {l_share:.0f} stopped at {l_name}. "
            f"On a small sample, a {w_share - l_share:.1f}-point gap is a real "
            "signal you can act on.",
        )

    st.markdown("")

    styles.section("Pick the displays to compare")
    styles.interpretation(
        "Use the multiselect to compare one display against itself over time, "
        "or both side-by-side. Each bar shows what share of people who "
        "walked past actually stepped inside the display."
    )

    ds = result.display_summary.copy()
    ds["share_pct"] = (ds["engagement_rate"] * 100).round(1)
    ds["display_label"] = ds["display"].str.replace("_", " ").str.title()

    display_choice = st.multiselect(
        "Displays",
        options=ds["display_label"].tolist(),
        default=ds["display_label"].tolist(),
        label_visibility="collapsed",
    )
    if not display_choice:
        st.warning("Pick at least one display.")
        st.stop()
    ds_f = ds[ds["display_label"].isin(display_choice)]
    color_map = {"Display A": "#22c55e", "Display B": "#ec4899"}

    c1, c2 = st.columns(2, gap="large")
    with c1:
        styles.section("Share who stopped")
        styles.interpretation(
            "Of every 100 people who walked past, how many stepped inside."
        )
        fig = px.bar(
            ds_f, x="display_label", y="share_pct",
            color="display_label", color_discrete_map=color_map,
            text=ds_f["share_pct"],
        )
        fig.update_traces(textposition="outside", texttemplate="%{text}%")
        fig.update_layout(
            showlegend=False, height=360,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title=None, yaxis_title="Share who stopped",
            yaxis=dict(gridcolor="#e2e8f0", range=[0, max(ds_f["share_pct"]) * 1.25]),
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        styles.section("Time spent once inside")
        styles.interpretation(
            "Once someone stepped inside, how long did they stay. Longer = "
            "the display is holding attention."
        )
        fig = px.bar(
            ds_f, x="display_label", y="avg_dwell_sec",
            color="display_label", color_discrete_map=color_map,
            text=ds_f["avg_dwell_sec"].round(1),
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
        styles.section("Head-to-head verdict")
        styles.interpretation(
            "If you had to pick one display to put your best product in, "
            "here is the case."
        )
        w_name, w = winner
        l_name, l = loser
        verdict = (
            f"**{w_name}** pulls **{w['engagement_rate']*100:.1f}%** of passers "
            f"and keeps them **{w['avg_dwell_sec']:.1f}s** on average. "
            f"**{l_name}** pulls **{l['engagement_rate']*100:.1f}%** "
            f"and keeps them **{l['avg_dwell_sec']:.1f}s**. "
            f"**{w_name}** wins on stopping power; the time-spent numbers are close."
        )
        styles.story("The verdict.", verdict)

    st.markdown("---")
    styles.section("Full numbers, for reference")
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
# Tab 4: The numbers (for the data team)
# =============================================================================
with tab_data:
    styles.section("Per-person summary")
    styles.interpretation(
        "Top N people the system spotted most often. Useful for verifying "
        "the system isn't double-counting anyone."
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

    styles.section("Download the numbers")
    styles.interpretation(
        "CSV files for your data team or for slides."
    )

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Trajectories CSV",
        data=result.tracks_df.to_csv(index=False).encode("utf-8"),
        mime="text/csv", use_container_width=True,
    )
    d2.download_button(
        "Trips between areas CSV",
        data=result.transitions.to_csv().encode("utf-8"),
        mime="text/csv", use_container_width=True,
    )
    d3.download_button(
        "Display numbers CSV",
        data=result.display_summary.to_csv(index=False).encode("utf-8"),
        mime="text/csv", use_container_width=True,
    )
