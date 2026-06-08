"""Shared premium UI: global CSS, Plotly theme, and reusable components."""

import streamlit as st
import plotly.graph_objects as go

from config import BRAND_GREEN, BRAND_WHITE, BRAND_GREY, BRAND_BLACK

# Surfaces
BG       = "#0A0A0A"
SURFACE  = "#141414"
SURFACE2 = "#1C1C1C"
BORDER   = "#262626"
GRID     = "#222222"
MUTED    = "#8A8A8A"


def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, sans-serif;
}}
.stApp {{ background: {BG}; }}

/* ── Headings ─────────────────────────────────────────── */
h1 {{ font-weight: 800 !important; letter-spacing: -0.02em; color: {BRAND_WHITE} !important; }}
h2, h3 {{ font-weight: 700 !important; letter-spacing: -0.01em; color: {BRAND_WHITE} !important; }}

/* Section subheaders get a green tick */
[data-testid="stHeading"] h3::before {{
    content: ""; display: inline-block; width: 4px; height: 16px;
    background: {BRAND_GREEN}; margin-right: 10px; border-radius: 2px;
    vertical-align: -2px;
}}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: {SURFACE}; border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] * {{ color: {BRAND_WHITE}; }}

/* ── Metric cards ─────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 18px 20px;
    transition: border-color .2s ease, transform .2s ease;
}}
[data-testid="stMetric"]:hover {{
    border-color: {BRAND_GREEN};
    transform: translateY(-2px);
}}
[data-testid="stMetricValue"] {{
    color: {BRAND_WHITE}; font-size: 1.7rem; font-weight: 800; letter-spacing: -0.02em;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED}; font-size: .72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: .08em;
}}
[data-testid="stMetricDelta"] {{ font-size: .8rem; font-weight: 600; }}

/* ── Tabs ─────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {BORDER}; }}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent; border-radius: 8px 8px 0 0;
    color: {MUTED}; font-weight: 600; padding: 8px 16px;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: {SURFACE}; color: {BRAND_GREEN};
    border-bottom: 2px solid {BRAND_GREEN};
}}

/* ── Inputs ───────────────────────────────────────────── */
[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input {{
    background: {SURFACE2} !important; border-color: {BORDER} !important;
    color: {BRAND_WHITE} !important; border-radius: 10px !important;
}}
.stMultiSelect [data-baseweb="tag"] {{
    background: {BRAND_GREEN} !important; color: {BRAND_BLACK} !important;
    font-weight: 600;
}}

/* ── Buttons ──────────────────────────────────────────── */
.stButton button {{
    background: {BRAND_GREEN}; color: {BRAND_BLACK};
    border: none; border-radius: 10px; font-weight: 700;
    transition: filter .2s ease;
}}
.stButton button:hover {{ filter: brightness(1.1); color: {BRAND_BLACK}; }}

/* ── Dataframe ────────────────────────────────────────── */
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 12px; }}

/* ── Dividers ─────────────────────────────────────────── */
hr {{ border-color: {BORDER} !important; margin: 1.2rem 0 !important; }}

/* ── Progress bars ────────────────────────────────────── */
.stProgress > div > div > div > div {{ background: {BRAND_GREEN}; }}

/* Expander */
[data-testid="stExpander"] {{ border: 1px solid {BORDER}; border-radius: 12px; background: {SURFACE}; }}

/* Reduce top padding */
.block-container {{ padding-top: 2.2rem; }}
</style>
""", unsafe_allow_html=True)


def plotly_theme(height=320, legend=True, showgrid=True):
    """Consistent dark Plotly layout dict."""
    layout = dict(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=BRAND_WHITE, family="Inter", size=12),
        margin=dict(l=10, r=10, t=20, b=10),
        height=height,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=MUTED),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=MUTED),
        colorway=[BRAND_GREEN, BRAND_WHITE, BRAND_GREY, "#9ECC00", "#4A4A4A", "#E0E0E0"],
    )
    if not showgrid:
        layout["xaxis"]["showgrid"] = False
        layout["yaxis"]["showgrid"] = False
    if legend:
        layout["legend"] = dict(
            bgcolor="rgba(0,0,0,0)", font=dict(color=BRAND_WHITE, size=11),
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        )
    return layout


def page_header(title: str, subtitle: str = ""):
    sub = f"<p style='color:{MUTED};margin:2px 0 0;font-size:.92rem'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"<div style='margin-bottom:18px'>"
        f"<h1 style='margin:0;font-size:1.9rem'>{title}</h1>{sub}</div>",
        unsafe_allow_html=True,
    )


def section(title: str):
    st.markdown(
        f"<h3 style='font-size:1.05rem;margin:6px 0 10px'>{title}</h3>",
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(**plotly_theme(**kwargs))
    return fig
