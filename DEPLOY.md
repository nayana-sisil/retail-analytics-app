# Deploying to Streamlit Community Cloud (free, public link)

This is the fastest way to get a public URL. Total time: ~10 minutes.

## Prerequisites

- A GitHub account
- This repository pushed to GitHub (public, or private + you give Streamlit access)
- ~15 minutes

## Steps

### 1. Push to GitHub

```bash
cd retail-analytics-app
git init
git add .
git commit -m "Initial deploy"
gh repo create retail-analytics-app --public --source=. --push
```

Or use the GitHub web UI to create a repo and push manually.

### 2. Connect Streamlit Community Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click **"New app"**
4. Pick the repo, branch (`main`), and main file path (`app.py`)
5. Click **"Deploy"**

That's it. Streamlit will:
- Install everything from `requirements.txt`
- Start the app
- Give you a public URL like `https://your-app.streamlit.app`

### 3. First deploy takes a few minutes

The first install pulls Ultralytics + PyTorch. That's ~1GB. On the free
tier it usually takes 3-5 minutes. Subsequent deploys are fast (cached).

### 4. Cold starts

Streamlit Community Cloud apps **sleep after ~7 days of no traffic**.
The first visitor after sleep gets a ~30 second wake-up. For a meeting
demo, hit the link 5 minutes early.

### 5. If something breaks

Check the **"Logs"** tab in the Streamlit Cloud dashboard. The most
common issues:

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: X` | Add `X` to `requirements.txt` |
| `FileNotFoundError: assets/mall_sample_results.json` | Make sure you committed the `assets/` folder |
| App crashes on YOLO download | The first call to `YOLO("yolo11n.pt")` downloads the model. Streamlit Cloud allows this. |
| Out of memory on first load | Reduce `MAX_FRAMES` in `pipeline.py` and re-run `build_sample_assets.py` |

## Optional: keep the app awake

If you don't want cold starts, either:
- Upgrade to Streamlit's paid tier (no sleep)
- Or set up an external cron (e.g. cron-job.org) to ping the URL every
  6 days

## Optional: custom domain

Free tier URL: `https://<name>.streamlit.app`. For a custom domain you
need Streamlit's paid tier, or proxy through Cloudflare in front.

## Alternative: HuggingFace Spaces

If you'd rather use Gradio (and skip Streamlit entirely), the same
pattern works on HF Spaces:

1. Create a Space at https://huggingface.co/new-space
2. Pick **Gradio** as the SDK
3. Push your code (with a slightly different `app.py` that uses `gr.Blocks`)
4. URL: `https://huggingface.co/spaces/<you>/<space>`

Free tier: 2 CPU cores, 16GB RAM, sleep after 48h of inactivity.
