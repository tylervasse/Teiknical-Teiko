import sqlite3
import streamlit as st

from pages.part2 import render_part2
from pages.part3 import render_part3
from pages.part4 import render_part4
def _db_ready() -> bool:
    try:
        conn = sqlite3.connect("cell_counts.db")
        conn.execute("SELECT 1 FROM projects LIMIT 1")
        conn.close()
        return True
    except Exception:
        return False


if not _db_ready():
    import db_creation
    with st.spinner("Building database from CSV — please wait..."):
        db_creation.main()
    st.cache_data.clear()
    st.cache_resource.clear()


st.set_page_config(page_title="Loblaw Bio - Immune Dashboard", layout="wide")
st.title("Loblaw Bio - Immune Cell Dashboard")

# Pin sidebar nav buttons to a consistent appearance.
# Uses 3 attribute selectors so this rule wins over the 2-attribute sort-header
# rules in tables.py that would otherwise leak their styles here.
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] > button {
        background: #FFE1E1 !important;
        border: 1px solid #e6bcbc !important;
        color: #333 !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 10px 12px !important;
        box-shadow: none !important;
        filter: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] > button:hover {
        filter: brightness(0.98) !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] > button:disabled {
        color: #bbb !important;
        opacity: 0.6 !important;
        filter: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SECTIONS = [
    ("Overview", render_part2),
    ("Response Group Comparison", render_part3),
    ("Subset Analysis", render_part4),
]

SECTION_NAMES = [name for name, _ in SECTIONS]

st.session_state.setdefault("section_idx", 0)


def _clamp_section(i: int) -> int:
    return max(0, min(int(i), len(SECTIONS) - 1))


def section_prev():
    st.session_state.section_idx = _clamp_section(st.session_state.section_idx - 1)


def section_next():
    st.session_state.section_idx = _clamp_section(st.session_state.section_idx + 1)


st.sidebar.markdown('<div class="section-pager-anchor"></div>', unsafe_allow_html=True)
st.sidebar.markdown('<p style="font-size:1.6rem; font-weight:700; margin-bottom:12px;">Part</p>', unsafe_allow_html=True)
b1, mid, b2 = st.sidebar.columns([1, 4, 1], gap="small")

idx = st.session_state.section_idx

with b1:
    st.button("◀", on_click=section_prev, disabled=(idx <= 0), key="section_prev")
with mid:
    st.markdown(
        f'<div style="text-align:center; font-weight:700; font-size:1.3rem; transform: translateY(-10px);">{SECTION_NAMES[idx]}</div>',
        unsafe_allow_html=True,
    )
with b2:
    st.button("▶", on_click=section_next, disabled=(idx >= len(SECTIONS) - 1), key="section_next")

st.sidebar.markdown('<div style="margin-bottom:20px;"></div>', unsafe_allow_html=True)

containers = [st.empty() for _ in SECTIONS]

_, active_render = SECTIONS[idx]
for i, container in enumerate(containers):
    if i == idx:
        with container.container():
            active_render()
    else:
        container.empty()
