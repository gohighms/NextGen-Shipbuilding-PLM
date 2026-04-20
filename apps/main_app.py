import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.common.reuse_state import get_current_spec, get_selected_project
from src.common.session_bootstrap import initialize_session_environment
from src.features.bom_management.ui import (
    render_block_division_page,
    render_mbom_page,
    render_wbom_page,
)
from src.features.design_change_management.ui import render_design_change_management_page
from src.features.design_plan_management.ui import render_design_plan_management_page
from src.features.digital_thread.ontology_ui import render_ontology_management_page
from src.features.digital_thread.rag_chat_ui import render_rag_chat_demo_page
from src.features.model_generation.ui import render_model_generation_page
from src.features.pos_generation.ui import render_pos_generation_page
from src.features.spec_search.ui import render_spec_search_page
from src.features.tag_management.ui import render_tag_management_page


REUSE_AREA = "설계 자산 재활용"
PROJECT_AREA = "프로젝트 관리"
BOM_AREA = "통합 BOM 관리"
THREAD_AREA = "디지털 쓰레드"
NAVIGATION_STATE_KEY = "selected_navigation_page"
AREA_WIDGET_KEY = "sidebar_area_widget"
PAGE_WIDGET_KEY = "sidebar_page_widget"
NAVIGATION_TARGET_AREA_KEY = "navigation_target_area"
NAVIGATION_TARGET_PAGE_KEY = "navigation_target_page"

REUSE_PAGES = {
    "1. 유사 프로젝트 탐색": render_spec_search_page,
    "2. POS 사양 재구성": render_pos_generation_page,
    "3. 모델 편집설계": render_model_generation_page,
}

PROJECT_PAGES = {
    "1. 설계 계획 관리": render_design_plan_management_page,
    "2. 설계 변경 관리": render_design_change_management_page,
}

BOM_PAGES = {
    "1. 블록 분할 정의": render_block_division_page,
    "2. 생산 BOM 구축": render_mbom_page,
    "3. 작업 패키지 BOM": render_wbom_page,
}

THREAD_PAGES = {
    "1. 통합 TAG 관리": render_tag_management_page,
    "2. 온톨로지 / 지식그래프": render_ontology_management_page,
    "3. AI 지식 어시스턴트": render_rag_chat_demo_page,
}


def _apply_global_font_scale() -> None:
    st.markdown(
        """
        <style>
        html {
            font-size: 17px;
        }

        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"] {
            font-size: 1rem;
        }

        section[data-testid="stSidebar"] {
            width: 24rem !important;
            min-width: 24rem !important;
        }

        h1 {
            font-size: 3rem !important;
        }

        h2 {
            font-size: 2.15rem !important;
        }

        h3 {
            font-size: 1.7rem !important;
        }

        p,
        li,
        label,
        .stMarkdown,
        .stCaption,
        .stText,
        .stSelectbox,
        .stMultiSelect,
        .stRadio,
        .stTextInput,
        .stTextArea,
        .stNumberInput,
        .stDateInput,
        .stTimeInput,
        .stSlider,
        .stDataFrame,
        .stTable,
        .stAlert,
        .stTabs,
        .stButton button,
        .stDownloadButton button {
            font-size: 1rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.9rem !important;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricDelta"] {
            font-size: 1rem !important;
        }

        [data-baseweb="select"] *,
        [data-baseweb="textarea"] *,
        [data-baseweb="input"] * {
            font-size: 1rem !important;
        }

        button[kind],
        [role="tab"],
        [data-testid="stSidebarNav"] * {
            font-size: 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def _scroll_to_top_if_page_changed(navigation_id: str) -> bool:
    previous_page = st.session_state.get(NAVIGATION_STATE_KEY)
    st.session_state[NAVIGATION_STATE_KEY] = navigation_id

    if previous_page and previous_page != navigation_id:
        _inject_scroll_to_top_script()
        return True
    return False


def _inject_scroll_to_top_script() -> None:
    components.html(
        """
        <script>
        const scrollTopNow = () => {
            window.parent.scrollTo({top: 0, left: 0, behavior: "auto"});
            const parentDoc = window.parent.document;
            const appView = parentDoc.querySelector('[data-testid="stAppViewContainer"]');
            const mainSection = parentDoc.querySelector('section.main');
            const blockContainer = parentDoc.querySelector('.main .block-container');
            const mainElement = parentDoc.querySelector('[data-testid="stMain"]');

            if (appView) appView.scrollTop = 0;
            if (mainSection) mainSection.scrollTop = 0;
            if (blockContainer) blockContainer.scrollTop = 0;
            if (mainElement) mainElement.scrollTop = 0;
        };

        scrollTopNow();
        requestAnimationFrame(scrollTopNow);
        setTimeout(scrollTopNow, 30);
        setTimeout(scrollTopNow, 120);
        setTimeout(scrollTopNow, 260);
        </script>
        """,
        height=0,
    )


def main() -> None:
    st.set_page_config(page_title="NextGen Shipbuilding PLM", layout="wide")
    initialize_session_environment()
    _apply_global_font_scale()

    st.sidebar.title("NextGen Shipbuilding PLM")
    if AREA_WIDGET_KEY not in st.session_state:
        st.session_state[AREA_WIDGET_KEY] = REUSE_AREA

    pending_area = st.session_state.pop(NAVIGATION_TARGET_AREA_KEY, None)
    if pending_area in [REUSE_AREA, PROJECT_AREA, BOM_AREA, THREAD_AREA]:
        st.session_state[AREA_WIDGET_KEY] = pending_area

    area_name = st.sidebar.selectbox("영역 선택", [REUSE_AREA, PROJECT_AREA, BOM_AREA, THREAD_AREA], key=AREA_WIDGET_KEY)

    if area_name == REUSE_AREA:
        st.sidebar.markdown("### 실적선 기반 설계 재활용")
        page_options = list(REUSE_PAGES.keys())
        render_map = REUSE_PAGES
    elif area_name == PROJECT_AREA:
        st.sidebar.markdown("### 프로젝트 관리")
        page_options = list(PROJECT_PAGES.keys())
        render_map = PROJECT_PAGES
    elif area_name == BOM_AREA:
        st.sidebar.markdown("### 목적별 BOM 관리")
        page_options = list(BOM_PAGES.keys())
        render_map = BOM_PAGES
    else:
        st.sidebar.markdown("### 디지털 쓰레드")
        page_options = list(THREAD_PAGES.keys())
        render_map = THREAD_PAGES

    if PAGE_WIDGET_KEY not in st.session_state or st.session_state[PAGE_WIDGET_KEY] not in page_options:
        st.session_state[PAGE_WIDGET_KEY] = page_options[0]

    pending_page = st.session_state.pop(NAVIGATION_TARGET_PAGE_KEY, None)
    if pending_page in page_options:
        st.session_state[PAGE_WIDGET_KEY] = pending_page

    page_name = st.sidebar.radio("세부 기능", page_options, key=PAGE_WIDGET_KEY)
    render_page = render_map[page_name]

    navigation_id = f"{area_name}::{page_name}"
    page_changed = _scroll_to_top_if_page_changed(navigation_id)
    _render_sidebar_status()
    render_page()
    if page_changed:
        _inject_scroll_to_top_script()


if __name__ == "__main__":
    main()
