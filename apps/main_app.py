import sys
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.features.spec_search.ui import render_spec_search_page


def main() -> None:
    st.set_page_config(page_title="NextGen Shipbuilding PLM", layout="wide")

    st.sidebar.title("NextGen Shipbuilding PLM")
    feature_name = st.sidebar.radio(
        "기능 선택",
        ["건조사양서 비교", "준비 중"],
        index=0,
    )

    if feature_name == "건조사양서 비교":
        render_spec_search_page()
        return

    st.title("준비 중 기능")
    st.info("다음 기능은 메인 화면에 순차적으로 추가할 예정입니다.")
    st.write("- BOM 검토")
    st.write("- 변경 영향도 확인")
    st.write("- 문서 파싱 자동화")


if __name__ == "__main__":
    main()
