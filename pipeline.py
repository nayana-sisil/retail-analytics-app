"""
Retail Video Analytics — core pipeline.

Refactored from the original notebook. Provides reusable functions for:
  - Process a video (or a frame directory) with YOLO + ByteTrack
  - Assign observations to spatial zones (Shapely polygons)
  - Compute customer journey analytics (footfall, transitions)
  - Compute display engagement analytics (dwell time, engagement rate)

All public functions return plain Python dicts / pandas DataFrames so they
are easy to call from a Streamlit UI or a notebook.
"""

from __future__ import annotations

import os
import glob
import json
import warnings
from dataclasses import dataclass, field
from typing import Iterable

import cv2
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

warnings.filterwarnings("ignore")


# -----------------------------------------------------------------------------
# Zone definitions (relative to image / video frame dimensions)
# -----------------------------------------------------------------------------

def build_journey_zones(W: int, H: int) -> dict[str, Polygon]:
    """UC1: customer journey zones — horizontal bands across the frame."""
    return {
        "entrance":    Polygon([(0, 0),      (W, 0),      (W, H * 0.25), (0, H * 0.25)]),
        "center":      Polygon([(0, H * 0.25), (W, H * 0.25), (W, H * 0.55), (0, H * 0.55)]),
        "storefronts": Polygon([(0, H * 0.55), (W, H * 0.55), (W, H * 0.80), (0, H * 0.80)]),
        "checkout":    Polygon([(0, H * 0.80), (W, H * 0.80), (W, H),       (0, H)]),
    }


def build_display_zones(W: int, H: int) -> dict[str, Polygon]:
    """UC2: display engagement zones — two rectangular regions in the middle band."""
    return {
        "display_a": Polygon([(W * 0.05, H * 0.30), (W * 0.35, H * 0.30),
                              (W * 0.35, H * 0.75), (W * 0.05, H * 0.75)]),
        "display_b": Polygon([(W * 0.65, H * 0.30), (W * 0.95, H * 0.30),
                              (W * 0.95, H * 0.75), (W * 0.65, H * 0.75)]),
    }


ZONE_COLORS = {
    "entrance":    (255, 200,   0),
    "center":      (  0, 200, 255),
    "storefronts": (255, 100, 100),
    "checkout":    (200, 100, 255),
    "display_a":   (  0, 255, 100),
    "display_b":   (255,  50, 200),
}


# -----------------------------------------------------------------------------
# Detection + tracking
# -----------------------------------------------------------------------------

def iter_video_frames(source) -> Iterable[tuple[int, np.ndarray]]:
    """Yield (frame_index, BGR ndarray) pairs from a video path or frame dir."""
    if isinstance(source, str) and os.path.isdir(source):
        files = sorted(glob.glob(os.path.join(source, "*.jpg")))
        for i, f in enumerate(files):
            yield i, cv2.imread(f)
    else:
        cap = cv2.VideoCapture(source)
        try:
            i = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                yield i, frame
                i += 1
        finally:
            cap.release()


def track_video(
    model,
    source,
    max_frames: int = 200,
    conf: float = 0.35,
    progress_cb=None,
) -> tuple[pd.DataFrame, int, int]:
    """Run YOLO + ByteTrack on a video / frame directory.

    Returns (tracks_df, frame_w, frame_h).
    tracks_df columns: frame, track_id, conf, cx, cy, x1, y1, x2, y2
    """
    rows: list[dict] = []
    H = W = 0
    for idx, frame in iter_video_frames(source):
        if idx >= max_frames:
            break
        if frame is None:
            continue
        H, W = frame.shape[:2]
        results = model.track(
            frame, persist=True, classes=[0], conf=conf,
            tracker="bytetrack.yaml", verbose=False,
        )
        r = results[0]
        if r.boxes is not None and r.boxes.id is not None:
            boxes = r.boxes.xyxy.cpu().numpy()
            ids = r.boxes.id.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()
            for box, tid, c in zip(boxes, ids, confs):
                x1, y1, x2, y2 = box
                rows.append({
                    "frame": idx,
                    "track_id": int(tid),
                    "conf": float(c),
                    "cx": float((x1 + x2) / 2),
                    "cy": float(y2),  # bottom center = foot position
                    "x1": float(x1), "y1": float(y1),
                    "x2": float(x2), "y2": float(y2),
                })
        if progress_cb is not None:
            progress_cb(idx + 1, max_frames)
    df = pd.DataFrame(rows)
    return df, W, H


# -----------------------------------------------------------------------------
# Zone assignment
# -----------------------------------------------------------------------------

def assign_zones(df: pd.DataFrame, zones: dict[str, Polygon]) -> pd.DataFrame:
    """Add a 'zone' column giving the polygon name a point falls inside, or None."""
    out = df.copy()
    polys = list(zones.items())

    def _z(row):
        pt = Point(row.cx, row.cy)
        for name, poly in polys:
            if poly.contains(pt):
                return name
        return None

    out["zone"] = out.apply(_z, axis=1)
    return out


# -----------------------------------------------------------------------------
# UC1: customer journey analytics
# -----------------------------------------------------------------------------

def footfall_by_zone(journey_df: pd.DataFrame, zones: dict[str, Polygon]) -> pd.Series:
    """Unique visitors per zone (nunique of track_id)."""
    return (
        journey_df.dropna(subset=["zone"])
        .groupby("zone")["track_id"]
        .nunique()
        .reindex(zones.keys(), fill_value=0)
    )


def zone_transitions(journey_df: pd.DataFrame, zones: dict[str, Polygon]) -> tuple[pd.DataFrame, dict[int, list[str]]]:
    """Zone -> zone transition counts (matrix + per-id sequences)."""
    zone_names = list(zones.keys())
    trans = pd.DataFrame(0, index=zone_names, columns=zone_names, dtype=int)
    sequences: dict[int, list[str]] = {}

    for tid, g in journey_df.sort_values("frame").groupby("track_id"):
        seq = [z for z in g["zone"].tolist() if z is not None]
        collapsed = [z for i, z in enumerate(seq) if i == 0 or z != seq[i - 1]]
        if collapsed:
            sequences[int(tid)] = collapsed
        for a, b in zip(collapsed, collapsed[1:]):
            if a in trans.index and b in trans.columns:
                trans.loc[a, b] += 1
    return trans, sequences


# -----------------------------------------------------------------------------
# UC2: display engagement analytics
# -----------------------------------------------------------------------------

def display_metrics(
    display_df: pd.DataFrame,
    all_tracks_df: pd.DataFrame,
    zones: dict[str, Polygon],
    fps: float,
) -> pd.DataFrame:
    """Per-display engagement summary."""
    all_ids = set(all_tracks_df["track_id"].unique())
    passers = len(all_ids)
    rows = []
    for name in zones:
        in_zone = display_df[display_df["zone"] == name]
        entered_ids = set(in_zone["track_id"].unique())
        dwell_frames = in_zone.groupby("track_id").size()
        rows.append({
            "display": name,
            "passers": passers,
            "zone_entries": len(entered_ids),
            "engagement_rate": round(len(entered_ids) / max(passers, 1), 3),
            "avg_dwell_sec": round(float(dwell_frames.mean() / fps), 2) if len(dwell_frames) else 0.0,
            "max_dwell_sec": round(float(dwell_frames.max() / fps), 2) if len(dwell_frames) else 0.0,
        })
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Combined runner — convenience for the UI
# -----------------------------------------------------------------------------

@dataclass
class PipelineResult:
    tracks_df: pd.DataFrame
    journey_df: pd.DataFrame
    display_df: pd.DataFrame
    footfall: pd.Series
    transitions: pd.DataFrame
    display_summary: pd.DataFrame
    width: int
    height: int
    fps: float
    n_frames_processed: int
    journey_zones: dict[str, Polygon] = field(default_factory=dict)
    display_zones: dict[str, Polygon] = field(default_factory=dict)


def run_pipeline(
    model,
    source,
    fps: float = 1.5,
    max_frames: int = 200,
    conf: float = 0.35,
    progress_cb=None,
) -> PipelineResult:
    """End-to-end pipeline. Returns a PipelineResult with everything the UI needs."""
    tracks_df, W, H = track_video(model, source, max_frames=max_frames, conf=conf, progress_cb=progress_cb)
    j_zones = build_journey_zones(W, H)
    d_zones = build_display_zones(W, H)
    journey_df = assign_zones(tracks_df, j_zones)
    display_df = assign_zones(tracks_df, d_zones)
    footfall = footfall_by_zone(journey_df, j_zones)
    trans, _ = zone_transitions(journey_df, j_zones)
    dsummary = display_metrics(display_df, tracks_df, d_zones, fps)
    return PipelineResult(
        tracks_df=tracks_df,
        journey_df=journey_df,
        display_df=display_df,
        footfall=footfall,
        transitions=trans,
        display_summary=dsummary,
        width=W, height=H, fps=fps,
        n_frames_processed=int(tracks_df["frame"].max() + 1) if len(tracks_df) else 0,
        journey_zones=j_zones,
        display_zones=d_zones,
    )


# -----------------------------------------------------------------------------
# JSON-safe serialization for cached results
# -----------------------------------------------------------------------------

def result_to_jsonable(result: PipelineResult) -> dict:
    """Convert a PipelineResult into a JSON-safe dict (Polygons -> coord lists)."""
    def _poly(p: Polygon) -> list[list[float]]:
        return [list(pt) for pt in list(p.exterior.coords)]
    return {
        "tracks_df": result.tracks_df.to_dict(orient="records"),
        "footfall": result.footfall.to_dict(),
        "transitions": result.transitions.to_dict(orient="index"),
        "display_summary": result.display_summary.to_dict(orient="records"),
        "width": result.width,
        "height": result.height,
        "fps": result.fps,
        "n_frames_processed": result.n_frames_processed,
        "journey_zones": {k: _poly(v) for k, v in result.journey_zones.items()},
        "display_zones": {k: _poly(v) for k, v in result.display_zones.items()},
    }


def result_from_jsonable(d: dict) -> PipelineResult:
    """Rebuild a PipelineResult from a JSON-safe dict."""
    tracks_df = pd.DataFrame(d["tracks_df"])
    width = d["width"]; height = d["height"]; fps = d["fps"]
    j_zones = {k: Polygon(v) for k, v in d["journey_zones"].items()}
    d_zones = {k: Polygon(v) for k, v in d["display_zones"].items()}
    footfall = pd.Series(d["footfall"])
    trans = pd.DataFrame.from_dict(d["transitions"], orient="index").astype(int)
    dsummary = pd.DataFrame(d["display_summary"])
    return PipelineResult(
        tracks_df=tracks_df,
        journey_df=tracks_df,  # zone col will be re-derived on display only
        display_df=tracks_df,
        footfall=footfall,
        transitions=trans,
        display_summary=dsummary,
        width=width, height=height, fps=fps,
        n_frames_processed=d.get("n_frames_processed", int(tracks_df["frame"].max() + 1) if len(tracks_df) else 0),
        journey_zones=j_zones,
        display_zones=d_zones,
    )
