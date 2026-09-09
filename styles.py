"""
Shared styling + small UI helpers used by all pages.

Inject once at the top of each page. Streamlit re-runs each page on
navigation, so the CSS needs to be re-injected per page.
"""

import streamlit as st


_CSS = """
<style>
    /* ---- Typography ---- */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                     Roboto, "Helvetica Neue", Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
    }
    h1 { font-weight: 700; letter-spacing: -0.02em; color: #0f172a; }
    h2 { font-weight: 600; letter-spacing: -0.01em; color: #1e293b;
         border-bottom: 2px solid #e2e8f0; padding-bottom: 0.4rem; margin-top: 1.5rem; }
    h3 { font-weight: 600; color: #334155; margin-top: 1.2rem; }
    p, li { color: #334155; line-height: 1.6; }

    /* ---- KPI metric cards ---- */
    [data-testid="stMetricValue"] {
        font-size: 1.9rem; font-weight: 700; color: #0f172a;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem; font-weight: 600; color: #64748b;
        text-transform: uppercase; letter-spacing: 0.06em;
    }
    [data-testid="stMetricDelta"] { font-size: 0.78rem; }

    /* ---- Card-like containers ---- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    /* ---- Buttons ---- */
    .stDownloadButton button, .stButton button {
        border-radius: 6px; font-weight: 500;
    }

    /* ---- Tables ---- */
    .stDataFrame { border-radius: 6px; overflow: hidden; }

    /* ---- Hero block ---- */
    .hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: #ffffff; padding: 2.5rem 2rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .hero h1 { color: #ffffff; margin: 0 0 0.5rem 0; }
    .hero p { color: #dbeafe; font-size: 1.05rem; margin: 0; }

    /* ---- Caption / small text ---- */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #64748b !important; font-size: 0.88rem;
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: #f8fafc; border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: #64748b; border: none; margin-top: 1rem;
    }
</style>
"""


def inject():
    """Call once at the top of each page to apply the shared CSS."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str):
    """Top-of-page gradient hero block."""
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def section(title: str, help: str | None = None):
    """Section header with optional help tooltip."""
    if help:
        st.subheader(title, help=help)
    else:
        st.subheader(title)


def interpretation(text: str):
    """A subtle 'how to read this' note under a chart."""
    st.markdown(
        f'<div style="background:#f1f5f9;border-left:3px solid #3b82f6;'
        f'padding:0.75rem 1rem;margin:0.5rem 0 1rem 0;border-radius:4px;'
        f'color:#475569;font-size:0.92rem;line-height:1.5;">'
        f'<strong style="color:#1e293b;">How to read this:</strong> {text}'
        f'</div>',
        unsafe_allow_html=True,
    )
