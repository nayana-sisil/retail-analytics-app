# Retail Video Analytics - Streamlit Demo

A public-facing web demo of a computer-vision pipeline that turns retail
video into **shopper journey** + **display engagement** analytics.

Pretrained **YOLO11n** for detection, **ByteTrack** for tracking,
**Shapely** polygons for zones, **pandas** for analytics, **Streamlit** for
the UI.

---

## Project structure

```
retail-analytics-app/
├── app.py                        # Landing page
├── pipeline.py                   # Core analytics (reusable, no UI)
├── requirements.txt
├── README.md
├── DEPLOY.md                     # Streamlit Community Cloud deployment
├── .streamlit/
│   └── config.toml               # Theme + upload limits
├── pages/
│   ├── 1_Results_Dashboard.py    # KPIs, funnels, heatmaps
│   ├── 2_Live_Demo.py            # Annotated video + per-frame chart
│   └── 3_Methodology.py          # Assumptions, limitations
├── scripts/
│   ├── build_sample_assets.py    # Generate the bundled demo assets
│   └── process_video.py          # Run pipeline on a local video/folder
└── assets/                       # Pre-computed sample (created by build script)
    ├── mall_sample.mp4
    ├── mall_sample_annotated.mp4
    ├── mall_sample_results.json
    ├── mall_sample_tracks.csv
    ├── mall_sample_transitions.csv
    ├── mall_sample_display_summary.csv
    └── best_frame.jpg
```

---

## Run it locally

```bash
# 1. Install
pip install -r requirements.txt

# 2. (Optional) regenerate the bundled sample assets
python scripts/build_sample_assets.py --n 200 --fps 1.5

# 3. Launch
streamlit run app.py
```

Open http://localhost:8501

---

## Run the pipeline on your own video

```bash
# Frames
python scripts/process_video.py --frames path/to/frames/ --out results/

# Video file
python scripts/process_video.py --video path/to/video.mp4 --out results/
```

Outputs:
- `results.json` — full pipeline output
- `tracks.csv` — per-frame detections
- `transitions.csv` — zone→zone counts
- `display_summary.csv` — per-display engagement
- `annotated.mp4` — overlay video

---

## Deploy to the public internet

See **[DEPLOY.md](DEPLOY.md)** for a step-by-step Streamlit Community Cloud guide.

---

## The pipeline (TL;DR)

```
video frames
  → YOLO11n person detection (class 0)
  → ByteTrack persistent tracking
  → Shapely point-in-polygon zone assignment
  → pandas analytics (footfall, transitions, dwell)
  → dashboard
```

Two use cases:

- **UC1 — Customer journey**: footfall per zone + zone→zone transition matrix.
- **UC2 — Display engagement**: passers / entries / engagement rate / avg & max dwell.

See the **Methodology** page in the app for assumptions, limitations, and
the full narrative.

---

## Notes for production

This is a **proof of concept**. To turn it into something a retailer would
actually deploy, you'd add:

- Camera calibration + measured FPS (replaces the 1.5 fps assumption)
- Retail-specific detector fine-tune (handles occlusions, atypical angles)
- Re-identification across cameras
- Live streaming + GPU inference
- Interactive zone drawing on a calibration frame
- POS / transaction join for conversion analytics
- Alerting (e.g. queue-at-checkout thresholds)
- A/B testing infra for store layout experiments

The blocks are all here. The next step is hardening each one, not inventing
new ones.
