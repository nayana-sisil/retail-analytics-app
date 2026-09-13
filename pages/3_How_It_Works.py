"""
How It Works - plain-language FAQ for non-technical readers.
"""

import streamlit as st

import styles


st.set_page_config(
    page_title="How It Works - Retail Analytics",
    page_icon="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%231e3a8a'/%3E%3Ctext x='50' y='68' font-size='60' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'%3ER%3C/text%3E%3C/svg%3E",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()


# Sidebar
with st.sidebar:
    st.markdown("## Quick links")
    st.markdown(
        """
- [What is this?](#what-is-this)
- [How accurate is it?](#how-accurate-is-it)
- [What are the limits?](#what-are-the-limits)
- [What's next?](#whats-next)
- [Can I run it on my own data?](#can-i-run-it-on-my-own-data)
        """
    )


# Header
styles.hero(
    "How It Works",
    "Plain-language answers to the questions people ask before they trust "
    "the numbers.",
)


# =============================================================================
# Q1: What is this?
# =============================================================================
styles.section("What is this?")
with st.container(border=True):
    st.markdown(
        """
A demo of a system that watches ordinary store-camera footage and turns
it into two simple kinds of information:

1. **Where shoppers go.** We drew colored boxes on the floor of the store
   to mark areas (entrance, center, storefronts, checkout). The system
   counts how many different people stepped into each box.

2. **Whether displays work.** Two more boxes mark the product displays.
   The system tracks how many people stopped there, and for how long.

That's it. No magic, no jargon. The system uses a pre-built AI model that
was already trained to recognize people in video, and pairs of boxes to
say which area each person was in.
        """
    )


# =============================================================================
# Q2: How accurate is it?
# =============================================================================
styles.section("How accurate is it?")
with st.container(border=True):
    st.markdown(
        """
**Good enough for direction, not yet for accounting.**

On this sample the system recognized 202 different people in 200 snapshots.
That is in the same range as a human doing a careful head-count.

Two things to keep in mind:

- **The 1.5 snapshots-per-second rate** is an estimate based on the sample
  data, not a measured camera rate. If the real camera is faster, every
  dwell time in this demo would be shorter than shown.
- **"People who walked by" includes everyone in the footage**, including
  people who never came near the displays. A production version would draw
  a small "near the display" box and count only those people, which would
  make the numbers more conservative.

For a serious pilot, we would compare the system's counts against a human
doing a hand count for one or two hours. That tells us how close the
system is for our specific store, with our cameras.
        """
    )


# =============================================================================
# Q3: What are the limits?
# =============================================================================
styles.section("What are the limits?")
with st.container(border=True):
    st.markdown(
        """
The system has limits worth knowing about before you quote these numbers
in a deck.

- **One camera.** The numbers cover only what this one camera can see. If a
  shopper walks out of frame into a hallway the system loses them.

- **Crowded scenes.** When many people overlap, the system can confuse one
  person for two, or briefly lose track. The mall footage in this demo is
  relatively uncrowded; a busy Saturday would be harder.

- **Lighting and angles.** The system is sensitive to camera placement.
  A camera pointed down at the floor (like in this demo) works well.
  A camera at an angle, or one with backlighting, would need calibration.

- **Two hundred snapshots is not a month.** This demo covers about two
  minutes of footage. Real decisions would need at least a week of data
  to account for time-of-day patterns.

None of these are blockers. They are all things we know how to handle
with calibration, more footage, and store-specific tuning.
        """
    )


# =============================================================================
# Q4: What's next?
# =============================================================================
styles.section("What's next?")
with st.container(border=True):
    st.markdown(
        """
This is a proof of concept. The next step is a measured pilot on one
real store. A typical pilot has three phases:

1. **Pilot in one store, six weeks.** Install the system on a real camera,
   compare its counts to a hand count, and decide if the numbers are
   accurate enough to act on.

2. **Multiple stores, six to eight weeks.** Roll out to three to five
   stores. Connect to the point-of-sale system so we can see, for example,
   whether shoppers who stopped at a display actually bought something.

3. **Decision support, eight to twelve weeks.** A simple dashboard for
   store managers with daily and weekly views, plus alerts for things
   like a queue at checkout.

The investment is roughly one engineer working with one store team for
six weeks. Most of the cost is integration time (cameras, network, IT),
not the AI itself.
        """
    )


# =============================================================================
# Q5: Can I run it on my own data?
# =============================================================================
styles.section("Can I run it on my own data?")
with st.container(border=True):
    st.markdown(
        """
Yes. The code in this project runs on any video or sequence of images.
A GPU is recommended (CPU works on small videos, just slowly). Three
commands:

```
# 1. Install
pip install -r requirements.txt

# 2. Process a video (or folder of frames)
python scripts/process_video.py --video path/to/video.mp4 --out results/

# 3. Launch the dashboard locally
streamlit run app.py
```

The processing step writes JSON with all the analytics, plus an annotated
MP4 showing what the system spotted. The dashboard reads the JSON
directly, so it loads instantly the same way the online demo does.
        """
    )


# Footer
st.markdown("---")
st.caption(
    "If you have a question this page does not answer, ask whoever shared "
    "this demo with you. They can route it to the right person."
)
