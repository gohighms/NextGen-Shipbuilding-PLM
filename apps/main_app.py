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
    render_work_instruction_page,
)
from src.features.design_change_management.ui import render_design_change_management_page
from src.features.design_plan_management.ui import render_design_plan_management_page
from src.features.digital_thread.ontology_ui import render_ontology_management_page
from src.features.digital_thread.supply_chain_ui import render_supply_chain_tracking_page
from src.features.digital_thread.ui import render_project_thread_map_page
from src.features.model_generation.ui import render_model_generation_page
from src.features.pos_generation.ui import render_pos_generation_page
from src.features.spec_search.ui import render_spec_search_page
from src.features.tag_management.ui import render_tag_management_page


REUSE_AREA = "실적선 기반 설계 재활용"
PROJECT_AREA = "프로젝트 관리"
BOM_AREA = "목적별 BOM 관리"
THREAD_AREA = "디지털 쓰레드"
NAVIGATION_STATE_KEY = "selected_navigation_page"

REUSE_PAGES = {
    "1. 유사 프로젝트 검색": render_spec_search_page,
    "2. 유사 프로젝트 기반 POS 편집설계": render_pos_generation_page,
    "3. 유사 프로젝트 기반 모델 편집설계": render_model_generation_page,
}

PROJECT_PAGES = {
    "1. 설계계획(DP) 관리": render_design_plan_management_page,
    "2. 설계 변경 관리": render_design_change_management_page,
}

BOM_PAGES = {
    "1. Block Division": render_block_division_page,
    "2. MBOM 생성": render_mbom_page,
    "3. WBOM 생성": render_wbom_page,
    "4. 작업지시서": render_work_instruction_page,
}

THREAD_PAGES = {
    "1. TAG 관리": render_tag_management_page,
    "2. 프로젝트 Thread Map": render_project_thread_map_page,
    "3. 온톨로지 / 지식그래프 관리": render_ontology_management_page,
    "4. 구매-설계-생산 추적": render_supply_chain_tracking_page,
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


def _scroll_to_top_if_page_changed(page_name: str) -> None:
    previous_page = st.session_state.get(NAVIGATION_STATE_KEY)
    st.session_state[NAVIGATION_STATE_KEY] = page_name

    if previous_page and previous_page != page_name:
        components.html(
            """
            <script>
            const scrollTopNow = () => {
                window.parent.scrollTo({top: 0, left: 0, behavior: "instant"});
                const parentDoc = window.parent.document;
                const appView = parentDoc.querySelector('[data-testid="stAppViewContainer"]');
                const mainSection = parentDoc.querySelector('section.main');
                const blockContainer = parentDoc.querySelector('.main .block-container');

                if (appView) appView.scrollTop = 0;
                if (mainSection) mainSection.scrollTop = 0;
                if (blockContainer) blockContainer.scrollTop = 0;
            };

            scrollTopNow();
            setTimeout(scrollTopNow, 30);
            </script>
            """,
            height=0,
        )


def main() -> None:
    st.set_page_config(page_title="NextGen Shipbuilding PLM", layout="wide")
    initialize_session_environment()
    _apply_global_font_scale()

    st.sidebar.title("NextGen Shipbuilding PLM")
    area_name = st.sidebar.selectbox("영역 선택", [REUSE_AREA, PROJECT_AREA, BOM_AREA, THREAD_AREA])

    if area_name == REUSE_AREA:
        st.sidebar.markdown("### 실적선 기반 설계 재활용")
        page_name = st.sidebar.radio("세부 기능", list(REUSE_PAGES.keys()))
        render_page = REUSE_PAGES[page_name]
    elif area_name == PROJECT_AREA:
        st.sidebar.markdown("### 프로젝트 관리")
        page_name = st.sidebar.radio("세부 기능", list(PROJECT_PAGES.keys()))
        render_page = PROJECT_PAGES[page_name]
    elif area_name == BOM_AREA:
        st.sidebar.markdown("### 목적별 BOM 관리")
        page_name = st.sidebar.radio("세부 기능", list(BOM_PAGES.keys()))
        render_page = BOM_PAGES[page_name]
    else:
        st.sidebar.markdown("### 디지털 쓰레드")
        page_name = st.sidebar.radio("세부 기능", list(THREAD_PAGES.keys()))
        render_page = THREAD_PAGES[page_name]

    _scroll_to_top_if_page_changed(page_name)
    _render_sidebar_status()
    render_page()


if __name__ == "__main__":
    main()
