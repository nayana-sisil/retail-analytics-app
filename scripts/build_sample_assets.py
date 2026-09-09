#!/usr/bin/env python3
"""
build_sample_assets.py

Generates the bundled sample assets for the demo:

  - assets/mall_sample.mp4            : original frames -> mp4 at ASSUMED_FPS
  - assets/mall_sample_annotated.mp4  : same video with bboxes, track IDs, zone overlays
  - assets/mall_sample_results.json   : cached analytics (consumed by the UI)
  - assets/best_frame.jpg             : a single nicely-annotated frame for the landing page
  - assets/sample_frames/             : 20 evenly-spaced frames for the Live Demo scrubber

Usage:
  python scripts/build_sample_assets.py \\
      --frames /path/to/mall_dataset/frames \\
      --out assets/

If --frames is not provided, defaults to the KaggleHub cache path. If the
kagglehub cache is empty, the script will try to download the dataset.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

# Allow `python scripts/build_sample_assets.py` from project root
sys.path.insert(0, str(Path(__file__).parent.parent))
import pipeline  # noqa: E402

warnings.filterwarnings("ignore")


DEFAULT_FRAMES = (
    "/workspace/.home/.cache/kagglehub/datasets/chaozhuang/mall-dataset/versions/3/frames/frames"
)

DEFAULT_KAGGLE_SLUG = "chaozhuang/mall-dataset"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def ensure_frames(frames_dir: str) -> str:
    if os.path.isdir(frames_dir) and any(f.endswith(".jpg") for f in os.listdir(frames_dir)[:5]):
        return frames_dir
    print(f"Frames not found at {frames_dir}, attempting kagglehub download...")
    import kagglehub
    path = kagglehub.dataset_download(DEFAULT_KAGGLE_SLUG)
    nested = os.path.join(path, "frames")
    if os.path.isdir(nested) and any(f.endswith(".jpg") for f in os.listdir(nested)[:5]):
        return nested
    return path


def stitch_video(frame_dir: str, out_path: str, n_frames: int, fps: float):
    """Use ffmpeg to encode n_frames JPEGs -> mp4 at the target fps."""
    files = sorted([f for f in os.listdir(frame_dir) if f.endswith(".jpg")])[:n_frames]
    if not files:
        raise RuntimeError(f"No .jpg frames found in {frame_dir}")

    # Make a temp symlink dir with sequential names so ffmpeg can pick them up
    tmp = Path(out_path).parent / "_stitch_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(files):
        os.symlink(os.path.join(frame_dir, f), tmp / f"f{i:06d}.jpg")

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(fps),
        "-i", str(tmp / "f%06d.jpg"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        out_path,
    ]
    print(f"[ffmpeg] encoding {len(files)} frames @ {fps} fps -> {out_path}")
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    print(f"[ffmpeg] done")


def render_annotated_video(
    result: pipeline.PipelineResult,
    frame_dir: str,
    out_path: str,
    fps: float,
):
    """Render the same frames with bboxes + track IDs + zone polygons drawn."""
    W, H = result.width, result.height

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(out_path, fourcc, fps, (W, H))

    tracks = result.tracks_df

    # Build per-frame lookup
    by_frame = {int(f): g for f, g in tracks.groupby("frame")}

    frame_files = sorted([f for f in os.listdir(frame_dir) if f.endswith(".jpg")])[
        : result.n_frames_processed
    ]

    for idx, fname in enumerate(frame_files):
        img = cv2.imread(os.path.join(frame_dir, fname))
        # Draw zones first (under detections)
        for name, poly in {**result.journey_zones, **result.display_zones}.items():
            pts = np.array(list(poly.exterior.coords), dtype=np.int32)
            color = pipeline.ZONE_COLORS[name]
            overlay = img.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
            cv2.polylines(img, [pts], True, color, 2)
            x, y = pts[0]
            cv2.putText(img, name, (int(x) + 6, int(y) + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        # Draw detections
        for _, row in by_frame.get(idx, pd.DataFrame()).iterrows():
            x1, y1, x2, y2 = int(row.x1), int(row.y1), int(row.x2), int(row.y2)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"#{int(row.track_id)} {row.conf:.2f}"
            cv2.putText(img, label, (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        # Header text
        cv2.putText(img, f"frame {idx}/{result.n_frames_processed-1}",
                    (10, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(img, f"frame {idx}/{result.n_frames_processed-1}",
                    (10, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        vw.write(img)
    vw.release()
    print(f"[render] wrote {out_path}")


def write_best_frame(result: pipeline.PipelineResult, frame_dir: str, out_path: str):
    """Pick the frame with the most tracks, save it annotated as a static image."""
    tracks = result.tracks_df
    if not len(tracks):
        return
    counts = tracks.groupby("frame").size()
    best_idx = int(counts.idxmax())
    frame_files = sorted([f for f in os.listdir(frame_dir) if f.endswith(".jpg")])
    img = cv2.imread(os.path.join(frame_dir, frame_files[best_idx]))

    for name, poly in {**result.journey_zones, **result.display_zones}.items():
        pts = np.array(list(poly.exterior.coords), dtype=np.int32)
        color = pipeline.ZONE_COLORS[name]
        overlay = img.copy()
        cv2.fillPoly(overlay, [pts], color)
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
        cv2.polylines(img, [pts], True, color, 2)
        x, y = pts[0]
        cv2.putText(img, name, (int(x) + 6, int(y) + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    for _, row in tracks[tracks["frame"] == best_idx].iterrows():
        x1, y1, x2, y2 = int(row.x1), int(row.y1), int(row.x2), int(row.y2)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"#{int(row.track_id)}", (x1, max(y1 - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

    cv2.imwrite(out_path, img)
    print(f"[best] saved {out_path} (frame {best_idx}, {counts.iloc[0]} detections)")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", default=DEFAULT_FRAMES, help="Directory with seq_*.jpg frames")
    parser.add_argument("--out", default="assets", help="Output directory")
    parser.add_argument("--n", type=int, default=200, help="Number of frames to process")
    parser.add_argument("--fps", type=float, default=1.5, help="Assumed FPS for dwell calc + video encoding")
    parser.add_argument("--conf", type=float, default=0.35, help="YOLO confidence threshold")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = ensure_frames(args.frames)
    print(f"Using frames from: {frames_dir}")

    print("Loading YOLO11n...")
    model = YOLO("yolo11n.pt")

    print(f"Running pipeline on first {args.n} frames @ {args.fps} fps...")
    progress = {"i": 0}
    def cb(i, total):
        if i % 10 == 0 or i == total:
            print(f"  frame {i}/{total}")
    result = pipeline.run_pipeline(
        model, frames_dir, fps=args.fps, max_frames=args.n, conf=args.conf, progress_cb=cb,
    )
    print(f"Pipeline done. {len(result.tracks_df)} detections, "
          f"{result.tracks_df['track_id'].nunique()} unique shoppers.")

    # Stitch raw video
    raw_mp4 = out_dir / "mall_sample.mp4"
    stitch_video(frames_dir, str(raw_mp4), n_frames=args.n, fps=args.fps)

    # Render annotated video
    annotated_mp4 = out_dir / "mall_sample_annotated.mp4"
    # Re-encode raw mp4 to h264 first so browser playback works
    h264_raw = out_dir / "_mall_sample_h264.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(raw_mp4), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(h264_raw),
    ], check=True)
    shutil.move(str(h264_raw), str(raw_mp4))

    render_annotated_video(result, frames_dir, str(out_dir / "_annotated_tmp.mp4"), fps=args.fps)
    # Re-encode annotated to h264 for browser compatibility
    h264_ann = out_dir / "mall_sample_annotated.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(out_dir / "_annotated_tmp.mp4"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(h264_ann),
    ], check=True)
    os.remove(out_dir / "_annotated_tmp.mp4")

    # Save JSON results
    json_path = out_dir / "mall_sample_results.json"
    with open(json_path, "w") as f:
        json.dump(pipeline.result_to_jsonable(result), f)
    print(f"[json] wrote {json_path}")

    # Save CSVs (also embedded in the JSON, but handy for direct download)
    result.tracks_df.to_csv(out_dir / "mall_sample_tracks.csv", index=False)
    result.transitions.to_csv(out_dir / "mall_sample_transitions.csv")
    result.display_summary.to_csv(out_dir / "mall_sample_display_summary.csv", index=False)
    print(f"[csv] wrote per-frame tracks, transitions, display summary")

    # Best static frame
    write_best_frame(result, frames_dir, str(out_dir / "best_frame.jpg"))

    # Sample frames for the Live Demo scrubber (20 frames spread across the video)
    sample_dir = out_dir / "sample_frames"
    sample_dir.mkdir(exist_ok=True)
    import shutil as _sh
    for f in sample_dir.glob("*.jpg"):
        f.unlink()
    n_samples = 20
    idxs = np.linspace(0, result.n_frames_processed - 1, n_samples, dtype=int)
    sample_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])[
        : result.n_frames_processed
    ]
    for idx in idxs:
        src = os.path.join(frames_dir, sample_files[int(idx)])
        dst = sample_dir / f"frame_{int(idx):04d}.jpg"
        _sh.copy(src, dst)
    print(f"[samples] saved {n_samples} frames to {sample_dir}/")

    print("\nAll assets generated in", out_dir)
    for p in sorted(out_dir.iterdir()):
        if p.is_file():
            print(f"  {p.name}  ({p.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
