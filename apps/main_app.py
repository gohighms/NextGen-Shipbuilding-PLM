import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.common.reuse_state import get_current_spec, get_selected_project
from src.common.session_bootstrap import initialize_session_environment
from src.features.model_generation.ui import render_model_generation_page
from src.features.pos_generation.ui import render_pos_generation_page
from src.features.spec_search.ui import render_spec_search_page
from src.features.tag_management.ui import render_tag_management_page


REUSE_AREA = "실적선 기반 설계 재활용"
THREAD_AREA = "디지털 쓰레드"
NAVIGATION_STATE_KEY = "selected_navigation_page"

REUSE_PAGES = {
    "1. 건조사양서 기반 유사 프로젝트 찾기": render_spec_search_page,
    "2. 유사 프로젝트 기반 POS 편집설계": render_pos_generation_page,
    "3. 유사 프로젝트 기반 모델 편집설계": render_model_generation_page,
}

THREAD_PAGES = {
    "TAG 관리": render_tag_management_page,
}


def _render_sidebar_status() -> None:
    selected_project = get_selected_project()
    current_spec = get_current_spec()

    st.sidebar.divider()
    st.sidebar.markdown("### 현재 연결 상태")

    if selected_project:
        st.sidebar.success(f"기준 실적선\n`{selected_project['project_name']}`")
    else:
        st.sidebar.info("아직 선택된 유사 프로젝트가 없습니다.")

    if current_spec:
        st.sidebar.caption(f"현재 프로젝트: `{current_spec['project_name']}`")


def _scroll_to_top_if_page_changed(page_name: str) -> None:
    previous_page = st.session_state.get(NAVIGATION_STATE_KEY)
    st.session_state[NAVIGATION_STATE_KEY] = page_name

    if previous_page and previous_page != page_name:
        components.html(
            """
            <script>
            window.parent.scrollTo({top: 0, behavior: "instant"});
            </script>
            """,
            height=0,
        )


def main() -> None:
    st.set_page_config(page_title="NextGen Shipbuilding PLM", layout="wide")
    initialize_session_environment()

    st.sidebar.title("NextGen Shipbuilding PLM")
    area_name = st.sidebar.selectbox("영역 선택", [REUSE_AREA, THREAD_AREA])

    if area_name == REUSE_AREA:
        st.sidebar.markdown("### 실적선 기반 설계 재활용")
        page_name = st.sidebar.radio("세부 기능", list(REUSE_PAGES.keys()))
        render_page = REUSE_PAGES[page_name]
    else:
        st.sidebar.markdown("### 디지털 쓰레드")
        page_name = st.sidebar.radio("세부 기능", list(THREAD_PAGES.keys()))
        render_page = THREAD_PAGES[page_name]

    _scroll_to_top_if_page_changed(page_name)
    _render_sidebar_status()
    render_page()


if __name__ == "__main__":
    main()
