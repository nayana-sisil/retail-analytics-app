"""
Results Dashboard — pre-computed analytics for the bundled sample video.

Loads `assets/mall_sample_results.json` (cached on first deploy) and renders
the full set of business metrics:

  - KPI cards
  - Journey funnel
  - Zone-to-zone transition heatmap
  - Display engagement bars
  - Per-shopper journey table
  - Downloadable CSVs
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import pipeline


HERE = Path(__file__).parent.parent
ASSETS = HERE / "assets"


st.set_page_config(page_title="Results Dashboard · Retail Analytics", page_icon="📊", layout="wide")


@st.cache_data
def load_sample_results():
    path = ASSETS / "mall_sample_results.json"
    if not path.exists():
        return None
    with open(path) as f:
        return pipeline.result_from_jsonable(json.load(f))


def draw_zones_overlay(W: int, H: int, j_zones: dict, d_zones: dict) -> np.ndarray:
    """Render a clean reference frame with all zones drawn (used as a 'legend' image)."""
    img = np.full((H, W, 3), 245, dtype=np.uint8)  # light gray
    for name, poly in j_zones.items():
        pts = np.array(list(poly.exterior.coords), dtype=np.int32)
        color = pipeline.ZONE_COLORS[name]
        cv2_polylines(img, [pts], True, color, 2)
        x, y = pts[0]
        cv2.putText(img, name, (int(x) + 6, int(y) + 18),
                    cv2_FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    for name, poly in d_zones.items():
        pts = np.array(list(poly.exterior.coords), dtype=np.int32)
        color = pipeline.ZONE_COLORS[name]
        # dashed effect: draw thinner border + diagonal hatching skipped (kept simple)
        cv2_polylines(img, [pts], True, color, 2)
        x, y = pts[0]
        cv2.putText(img, name, (int(x) + 6, int(y) + 18),
                    cv2_FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return img


# Lazy imports to keep page load snappy
import cv2
cv2_FONT_HERSHEY_SIMPLEX = cv2.FONT_HERSHEY_SIMPLEX
cv2_polylines = cv2.polylines


result = load_sample_results()
if result is None:
    st.error(
        "Sample results file `assets/mall_sample_results.json` not found. "
        "Run `python scripts/build_sample_assets.py` to generate it, then restart."
    )
    st.stop()


# -----------------------------------------------------------------------------
# Header + KPIs
# -----------------------------------------------------------------------------
st.title("📊 Results Dashboard")
st.caption(
    f"Sample video: **{result.n_frames_processed} frames** at "
    f"**{result.fps} fps** ({result.n_frames_processed / result.fps:.0f} s) · "
    f"resolution **{result.width}×{result.height}**"
)

n_shoppers = int(result.tracks_df["track_id"].nunique()) if len(result.tracks_df) else 0
total_visits = int(result.footfall.sum())
avg_dwell = float(result.display_summary["avg_dwell_sec"].mean()) if len(result.display_summary) else 0
best_display = (
    result.display_summary.loc[result.display_summary["avg_dwell_sec"].idxmax(), "display"]
    if len(result.display_summary) else "—"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Unique shoppers", f"{n_shoppers}")
c2.metric("Total zone visits", f"{total_visits}")
c3.metric("Avg display dwell", f"{avg_dwell:.1f} s")
c4.metric("Top display (dwell)", best_display)

st.markdown("---")


# -----------------------------------------------------------------------------
# Zone reference + journey funnel
# -----------------------------------------------------------------------------
left, right = st.columns([1, 1.3])

with left:
    st.subheader("🗺️ Zone layout")
    st.caption("Spatial zones used for all analytics on this page.")
    zone_img = draw_zones_overlay(result.width, result.height, result.journey_zones, result.display_zones)
    st.image(zone_img, channels="RGB", use_container_width=True)

with right:
    st.subheader("👣 Customer journey — footfall by zone")
    st.caption("Number of unique shoppers observed in each journey zone.")
    footfall_df = result.footfall.reset_index()
    footfall_df.columns = ["zone", "unique_visitors"]
    st.bar_chart(footfall_df, x="zone", y="unique_visitors", height=300)

st.markdown("---")


# -----------------------------------------------------------------------------
# Zone transitions
# -----------------------------------------------------------------------------
st.subheader("🔀 Zone → Zone transitions")
st.caption(
    "How shoppers moved between zones. Rows = origin, columns = destination. "
    "Consecutive duplicate zones are collapsed (no fake 'entrance → entrance' counts)."
)
trans = result.transitions.copy()
# Render as a Plotly heatmap for hover/tooltips, with a fallback to a st.dataframe.
import plotly.graph_objects as go
fig = go.Figure(data=go.Heatmap(
    z=trans.values,
    x=trans.columns.tolist(),
    y=trans.index.tolist(),
    colorscale="Blues",
    text=trans.values,
    texttemplate="%{text}",
    hovertemplate="from %{y}<br>to %{x}<br>%{z} transitions<extra></extra>",
))
fig.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="To zone",
    yaxis_title="From zone",
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# -----------------------------------------------------------------------------
# Display engagement
# -----------------------------------------------------------------------------
st.subheader("🛒 Display engagement")
st.caption(
    "Per-display summary. **Passers** = all unique tracked shoppers in the video "
    "(a simplification — see methodology). **Engagement rate** = entries / passers. "
    "**Dwell** is in seconds, computed as frames inside the display / assumed FPS."
)
ds = result.display_summary

import plotly.graph_objects as go
fig = go.Figure()
fig.add_trace(go.Bar(
    x=ds["display"], y=ds["avg_dwell_sec"],
    name="Avg dwell (s)", marker_color="#DD8452",
    text=ds["avg_dwell_sec"], texttemplate="%{text:.1f}s",
))
fig.add_trace(go.Bar(
    x=ds["display"], y=ds["engagement_rate"] * 100,
    name="Engagement rate (%)", marker_color="#55A868",
    text=(ds["engagement_rate"] * 100).round(1),
    texttemplate="%{text:.1f}%",
))
fig.update_layout(
    barmode="group", height=380,
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis_title="seconds / percent",
)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    ds.style.format({
        "engagement_rate": "{:.1%}",
        "avg_dwell_sec": "{:.2f}",
        "max_dwell_sec": "{:.2f}",
    }),
    use_container_width=True,
)

st.markdown("---")


# -----------------------------------------------------------------------------
# Per-shopper journey table
# -----------------------------------------------------------------------------
st.subheader("🧍 Per-shopper journey (top 25 by track length)")
track_lengths = (
    result.tracks_df.groupby("track_id")
    .size()
    .sort_values(ascending=False)
    .head(25)
    .reset_index()
)
track_lengths.columns = ["track_id", "frames_seen"]
track_lengths["seconds_seen"] = (track_lengths["frames_seen"] / result.fps).round(1)
st.dataframe(track_lengths, use_container_width=True, hide_index=True)

st.markdown("---")


# -----------------------------------------------------------------------------
# Downloads
# -----------------------------------------------------------------------------
st.subheader("⬇️ Download data")
d1, d2, d3 = st.columns(3)
d1.download_button(
    "trajectories.csv",
    data=result.tracks_df.to_csv(index=False).encode("utf-8"),
    mime="text/csv",
    use_container_width=True,
)
d2.download_button(
    "transitions.csv",
    data=result.transitions.to_csv().encode("utf-8"),
    mime="text/csv",
    use_container_width=True,
)
d3.download_button(
    "display_summary.csv",
    data=result.display_summary.to_csv(index=False).encode("utf-8"),
    mime="text/csv",
    use_container_width=True,
)
