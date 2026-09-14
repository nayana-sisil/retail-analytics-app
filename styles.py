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
    h1 { font-weight: 800; letter-spacing: -0.02em; color: #0f172a; }
    h2 { font-weight: 700; letter-spacing: -0.01em; color: #1e293b;
         border-bottom: 2px solid #e2e8f0; padding-bottom: 0.4rem; margin-top: 1.5rem; }
    h3 { font-weight: 600; color: #334155; margin-top: 1.2rem; }
    p, li { color: #334155; line-height: 1.65; }

    /* ---- Big number KPI cards ---- */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem; font-weight: 800; color: #0f172a;
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
        border-radius: 12px;
        padding: 1.5rem 1.75rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }

    /* ---- Buttons ---- */
    .stDownloadButton button, .stButton button {
        border-radius: 8px; font-weight: 600;
    }

    /* ---- Tables ---- */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* ---- Hero block ---- */
    .hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: #ffffff; padding: 3rem 2.5rem; border-radius: 14px;
        margin-bottom: 1.5rem;
    }
    .hero h1 { color: #ffffff; margin: 0 0 0.6rem 0; font-size: 2.4rem; }
    .hero p { color: #dbeafe; font-size: 1.15rem; margin: 0; line-height: 1.5; }

    /* ---- Use-case cards ---- */
    .use-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3b82f6;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        height: 100%;
        transition: transform 0.15s ease;
    }
    .use-card h3 {
        margin: 0 0 0.5rem 0; color: #0f172a; font-size: 1.05rem;
    }
    .use-card p { color: #475569; margin: 0 0 0.5rem 0; font-size: 0.95rem; }
    .use-card .answer {
        color: #1e3a8a; font-weight: 600; font-size: 0.95rem;
        margin: 0.5rem 0 0 0; padding-top: 0.5rem;
        border-top: 1px dashed #cbd5e1;
    }

    /* ---- Story callout ---- */
    .story {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%);
        border-left: 4px solid #16a34a;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin: 0.75rem 0;
    }
    .story h3 {
        margin: 0 0 0.4rem 0; color: #166534; font-size: 1.1rem;
    }
    .story p { color: #334155; margin: 0; font-size: 0.95rem; }

    /* ---- Question/Answer blocks ---- */
    .qa-q {
        color: #1e3a8a; font-weight: 700; font-size: 1.05rem;
        margin: 1rem 0 0.4rem 0;
    }
    .qa-a { color: #334155; margin: 0 0 0.5rem 0; }

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

    /* ---- Make st.columns gaps a bit bigger for cards ---- */
    [data-testid="stHorizontalBlock"] { gap: 1rem; }
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


def use_card(icon: str, question: str, what_it_does: str, value: str):
    """A use-case card. icon is a single-character glyph (e.g. an emoji or symbol)."""
    st.markdown(
        f"""
<div class="use-card">
  <div style="font-size:1.8rem;line-height:1;margin-bottom:0.4rem;">{icon}</div>
  <h3>{question}</h3>
  <p>{what_it_does}</p>
  <div class="answer">So you can {value}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def story(title: str, body: str):
    """A value-style callout: 'here is what we learned and what it means'.

    The body may use **bold** markdown; we convert it to <strong> tags
    since the body is rendered inside HTML (not markdown).
    """
    import re
    html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    st.markdown(
        f'<div class="story"><h3>{title}</h3><p>{html_body}</p></div>',
        unsafe_allow_html=True,
    )
