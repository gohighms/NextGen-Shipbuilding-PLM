import sys
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.model_generation.ui import render_model_generation_page
from src.features.pos_generation.ui import render_pos_generation_page
from src.features.spec_search.ui import render_spec_search_page
from src.features.tag_management.ui import render_tag_management_page


def main() -> None:
    st.set_page_config(page_title="NextGen Shipbuilding PLM", layout="wide")

    st.sidebar.title("NextGen Shipbuilding PLM")
    feature_name = st.sidebar.radio(
        "기능 선택",
        ["건조사양서 비교", "TAG 관리", "POS 생성", "모델(EBOM) 생성", "준비 중"],
        index=0,
    )

    if feature_name == "건조사양서 비교":
        render_spec_search_page()
        return

    if feature_name == "TAG 관리":
        render_tag_management_page()
        return

    if feature_name == "POS 생성":
        render_pos_generation_page()
        return

    if feature_name == "모델(EBOM) 생성":
        render_model_generation_page()
        return

    st.title("준비 중 기능")
    st.info("다음 기능은 메인 화면에 순차적으로 추가할 예정입니다.")
    st.write("- 문서 파싱")
    st.write("- 변경 영향도 분석")
    st.write("- MBOM 생성")


if __name__ == "__main__":
    main()
