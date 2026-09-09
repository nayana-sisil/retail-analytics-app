#!/usr/bin/env python3
"""
process_video.py — run the pipeline on a local video / frame folder.

Usage:
  python scripts/process_video.py --video path/to/video.mp4 --out results/
  python scripts/process_video.py --frames path/to/frames/ --out results/
"""

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import pandas as pd
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).parent.parent))
import pipeline  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="Path to an .mp4/.mov video file")
    src.add_argument("--frames", help="Path to a directory of seq_*.jpg frames")
    parser.add_argument("--out", default="results", help="Output directory")
    parser.add_argument("--n", type=int, default=400, help="Max frames to process")
    parser.add_argument("--fps", type=float, default=1.5, help="Assumed FPS for dwell time")
    parser.add_argument("--conf", type=float, default=0.35, help="YOLO confidence threshold")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    source = args.video or args.frames
    print(f"Source: {source}")
    print(f"Output: {out_dir}")
    print(f"Max frames: {args.n}, FPS: {args.fps}, conf: {args.conf}")

    print("Loading YOLO11n...")
    model = YOLO("yolo11n.pt")

    print("Running pipeline...")
    def cb(i, total):
        if i % 25 == 0 or i == total:
            print(f"  {i}/{total} frames")
    result = pipeline.run_pipeline(
        model, source, fps=args.fps, max_frames=args.n, conf=args.conf, progress_cb=cb,
    )

    # Save outputs
    with open(out_dir / "results.json", "w") as f:
        json.dump(pipeline.result_to_jsonable(result), f, indent=2)
    result.tracks_df.to_csv(out_dir / "tracks.csv", index=False)
    result.transitions.to_csv(out_dir / "transitions.csv")
    result.display_summary.to_csv(out_dir / "display_summary.csv", index=False)

    # Render annotated video
    if args.video:
        cap = cv2.VideoCapture(args.video)
        fps = cap.get(cv2.CAP_PROP_FPS) or args.fps
        W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
    else:
        files = sorted([f for f in os.listdir(args.frames) if f.endswith(".jpg")])[:args.n]
        img0 = cv2.imread(os.path.join(args.frames, files[0]))
        H, W = img0.shape[:2]
        fps = args.fps

    ann_path = out_dir / "annotated.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(str(ann_path), fourcc, fps, (W, H))

    by_frame = {int(f): g for f, g in result.tracks_df.groupby("frame")}
    if args.video:
        cap = cv2.VideoCapture(args.video)
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or idx >= args.n:
                break
            img = frame
            # zones
            for name, poly in {**result.journey_zones, **result.display_zones}.items():
                pts = np.array(list(poly.exterior.coords), dtype=np.int32)
                color = pipeline.ZONE_COLORS[name]
                overlay = img.copy()
                cv2.fillPoly(overlay, [pts], color)
                cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
                cv2.polylines(img, [pts], True, color, 2)
            # detections
            for _, row in by_frame.get(idx, pd.DataFrame()).iterrows():
                x1, y1, x2, y2 = int(row.x1), int(row.y1), int(row.x2), int(row.y2)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, f"#{int(row.track_id)}", (x1, max(y1 - 6, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            vw.write(img)
            idx += 1
        cap.release()
    vw.release()

    print(f"\nDone. Outputs in {out_dir}/")
    print(f"  - results.json  (full pipeline output)")
    print(f"  - tracks.csv    (per-frame detections)")
    print(f"  - transitions.csv  (zone->zone counts)")
    print(f"  - display_summary.csv  (per-display engagement)")
    print(f"  - annotated.mp4 (overlay video)")


if __name__ == "__main__":
    main()
