import streamlit as st

from constants import PAGER_PULL_UP_PX


def init_state(page_key: str):
    st.session_state.setdefault("global_sort_key", "sample")
    st.session_state.setdefault("global_sort_dir", "asc")
    st.session_state.setdefault(f"{page_key}_page", 1)
    st.session_state.setdefault(f"{page_key}_page_input", int(st.session_state[f"{page_key}_page"]))


def clamp_page(p: int, total_pages: int) -> int:
    total_pages = max(1, int(total_pages))
    return max(1, min(int(p), total_pages))


def set_sort(new_key: str, page_key: str):
    init_state(page_key)
    if st.session_state.global_sort_key == new_key:
        st.session_state.global_sort_dir = "asc" if st.session_state.global_sort_dir == "desc" else "desc"
    else:
        st.session_state.global_sort_key = new_key
        st.session_state.global_sort_dir = "asc"

    st.session_state[f"{page_key}_page"] = 1
    st.session_state[f"{page_key}_page_input"] = 1


def render_pager(total_pages: int, page_key: str, pull_up_px: int = PAGER_PULL_UP_PX):
    init_state(page_key)
    page_state_key = f"{page_key}_page"
    page_input_key = f"{page_key}_page_input"

    def sync():
        st.session_state[page_input_key] = int(st.session_state[page_state_key])

    def prev_page():
        st.session_state[page_state_key] = clamp_page(st.session_state[page_state_key] - 1, total_pages)
        sync()

    def next_page():
        st.session_state[page_state_key] = clamp_page(st.session_state[page_state_key] + 1, total_pages)
        sync()

    def jump_page():
        desired = st.session_state.get(page_input_key, 1)
        st.session_state[page_state_key] = clamp_page(desired, total_pages)
        sync()

    st.markdown(
        f"""
        <style>
          .pager-anchor-{page_key} {{ margin-top: {-int(pull_up_px)}px; }}

          /* Keep the 4 widgets on one row and vertically centered */
          .pager-anchor-{page_key} + div [data-testid="stHorizontalBlock"] {{
            align-items: center !important;
          }}

          .pager-anchor-{page_key} + div [data-testid="stButton"] > button {{
            padding: 0px 10px !important;
            height: 28px !important;
            min-height: 28px !important;
            font-size: 12px !important;
            border-radius: 8px !important;
            background: #f0f0f0 !important;
            border: 1px solid #d5d5d5 !important;
            color: #444 !important;
            box-shadow: none !important;
          }}
          .pager-anchor-{page_key} + div [data-testid="stButton"] > button:hover {{
            background: #e9e9e9 !important;
            border-color: #cfcfcf !important;
          }}
          .pager-anchor-{page_key} + div [data-testid="stButton"] > button:disabled {{
            background: #f0f0f0 !important;
            border: 1px solid #d5d5d5 !important;
            color: #999 !important;
            opacity: 1 !important;
          }}

          .pager-anchor-{page_key} + div [data-testid="stNumberInput"] {{
            width: 70px !important;
            min-width: 70px !important;
            max-width: 70px !important;
          }}
          .pager-anchor-{page_key} + div [data-testid="stNumberInput"] input {{
            height: 28px !important;
            min-height: 28px !important;
            font-size: 12px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            text-align: center !important;
          }}

          /* Make "/ 2100" align perfectly with the input + buttons */
          .pager-anchor-{page_key} + div .pager-total {{
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: 10px !important;
            font-weight: 450 !important;
            color: #444 !important;
            white-space: nowrap !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f'<div class="pager-anchor-{page_key}"></div>', unsafe_allow_html=True)

    _, right = st.columns([12, 3], gap="small")
    with right:
        # Tuned widths to keep the number input visually centered between arrows
        c1, c2, c3, c4 = st.columns([0.9, 1.4, 1.0, 0.9], gap="small")

        with c1:
            st.button(
                "◀", on_click=prev_page, disabled=(st.session_state[page_state_key] <= 1),
                key=f"{page_key}_prev", use_container_width=True,
            )
        with c2:
            st.number_input(
                "Page", min_value=1, max_value=int(total_pages), step=1,
                label_visibility="collapsed", key=page_input_key, on_change=jump_page,
            )
        with c3:
            # Change font-size here to resize the "/ N" total pages text
            st.markdown(
                f'<div style="font-size: 21px; font-weight: 450; color: #444; white-space: nowrap;">/ {int(total_pages)}</div>',
                unsafe_allow_html=True,
            )
        with c4:
            st.button(
                "▶", on_click=next_page, disabled=(st.session_state[page_state_key] >= total_pages),
                key=f"{page_key}_next", use_container_width=True,
            )
