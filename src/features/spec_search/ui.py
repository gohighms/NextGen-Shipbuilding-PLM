import pandas as pd
import re
import streamlit as st

from src.common.paths import PROCESSED_DATA_DIR
from src.common.reuse_state import (
    get_current_spec,
    get_selected_project,
    set_current_spec,
    set_selected_project,
)
from src.features.spec_search.attribute_utils import flatten_attributes
from src.features.spec_search.compare import compare_spec_attributes
from src.features.spec_search.repository import SpecRepository
from src.features.spec_search.service import SpecSearchService


SEARCH_RESULT_KEY = "spec_search_last_result"
SEARCH_FLASH_MESSAGE_KEY = "spec_search_flash_message"
PROJECT_NAME_PATTERN = re.compile(r"^HD\d{4}$")

FIELD_LABELS = {
    "basic_info.ship_type_hint": "기본정보 / 선종 추정",
    "basic_info.ship_type": "기본정보 / 선종",
    "basic_info.yard": "기본정보 / 조선소",
    "basic_info.cargo_tank_count": "기본정보 / 화물창 수",
    "basic_info.bay_plan_type": "기본정보 / 베이 플랜 형식",
    "principal_dimensions.loa_m": "주요치수 / 전장(LOA)",
    "principal_dimensions.breadth_m": "주요치수 / 선폭(Breadth)",
    "principal_dimensions.draft_m": "주요치수 / 만재흘수(Draft)",
    "performance.service_speed_kn": "성능 / 서비스 속력",
    "machinery.main_engine": "기관 / 주기관",
    "machinery.propulsion_type": "기관 / 추진 방식",
    "cargo_system.cargo_capacity_m3": "화물 / 화물창 용적",
    "cargo_system.capacity_teu": "화물 / 적재 능력(TEU)",
    "cargo_system.cargo_tank_system": "화물 / 화물창 형식",
    "cargo_system.deadweight_ton": "화물 / 재화중량톤수",
}


def _display_field_name(field_name: str) -> str:
    return FIELD_LABELS.get(field_name, field_name)


def _render_description(text: str) -> None:
    st.caption(text)


def _render_mini_title(text: str) -> None:
    st.markdown(f"#### {text}")


def _build_saved_spec_rows(saved_specs: list) -> list[dict]:
    return [
        {
            "사양서 ID": item.spec_id,
            "프로젝트명": item.project_name,
            "선종": item.ship_type,
        }
        for item in saved_specs
    ]


def _render_spec_preview(document) -> None:
    _render_mini_title("선택한 사양서 미리보기")

    summary_col1, summary_col2, summary_col3 = st.columns(3)
    summary_col1.metric("선종", document.ship_type or "-")
    summary_col2.metric("정리된 항목 수", len(flatten_attributes(document.attributes)))
    summary_col3.metric("원문 길이", len(document.text))

    info_col1, info_col2 = st.columns([1, 2])
    with info_col1:
        st.write(f"- 사양서 ID: `{document.spec_id}`")
        st.write(f"- 프로젝트명: `{document.project_name}`")
    with info_col2:
        with st.expander("원문 요약 보기", expanded=False):
            st.write(document.text)

    tabs = st.tabs(["기본정보", "주요치수", "성능", "기관", "화물"])
    section_pairs = [
        ("basic_info", tabs[0]),
        ("principal_dimensions", tabs[1]),
        ("performance", tabs[2]),
        ("machinery", tabs[3]),
        ("cargo_system", tabs[4]),
    ]

    for section_name, tab in section_pairs:
        with tab:
            section_data = document.attributes.get(section_name, {})
            if not section_data:
                st.info("등록된 내용이 없습니다.")
                continue

            rows = [
                {
                    "항목명": _display_field_name(f"{section_name}.{key}"),
                    "값": value,
                }
                for key, value in section_data.items()
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_selected_project_status() -> None:
    selected_project = get_selected_project()
    current_spec = get_current_spec()

    if not selected_project:
        return

    st.success(
        f"`{selected_project['project_name']}` 프로젝트가 이후 POS/모델 편집설계 기준으로 선택되어 있습니다."
    )

    if current_spec:
        st.caption(
            f"현재 프로젝트 `{current_spec['project_name']}`에 대해 선택된 실적선 기준을 이어서 사용할 수 있습니다."
        )


def render_spec_search_page() -> None:
    st.title("유사 프로젝트 검색")
    _render_description(
        "현재 건조사양서를 기준으로 가장 가까운 실적선 프로젝트를 찾고, 이후 POS와 모델 편집설계의 기준 프로젝트로 연결합니다."
    )

    repository = SpecRepository(data_dir=PROCESSED_DATA_DIR)
    service = SpecSearchService(repository=repository)
    saved_specs = repository.list_all()

    _render_selected_project_status()
    flash_message = st.session_state.pop(SEARCH_FLASH_MESSAGE_KEY, None)
    if flash_message:
        st.success(flash_message)

    st.subheader(
        "현재 데이터 현황",
        help="비교에 사용하는 실적선 사양서 목록입니다. 먼저 어떤 실적 데이터가 들어 있는지 확인할 수 있습니다.",
    )
    st.metric("적재된 실적선 사양서 수", len(saved_specs))

    if saved_specs:
        st.dataframe(
            pd.DataFrame(_build_saved_spec_rows(saved_specs)),
            use_container_width=True,
            hide_index=True,
            height=260,
        )

        st.divider()
        preview_spec_id = st.selectbox(
            "미리볼 사양서 선택",
            options=[item.spec_id for item in saved_specs],
            format_func=lambda spec_id: next(
                f"{item.project_name} ({item.spec_id})"
                for item in saved_specs
                if item.spec_id == spec_id
            ),
        )
        preview_document = next(item for item in saved_specs if item.spec_id == preview_spec_id)
        _render_spec_preview(preview_document)
    else:
        st.info("`data/processed` 아래에 비교용 실적선 사양서가 없습니다.")

    st.divider()

    input_col1, input_col2 = st.columns([0.8, 1.2])
    with input_col1:
        _render_mini_title("유사 프로젝트 검색")
        st.write("1. 현재 건조사양서의 핵심 스펙을 입력합니다.")
        st.write("2. 유사한 실적선 프로젝트를 찾습니다.")

    with input_col2:
        project_name = st.text_input("프로젝트명", value="HD9001")
        spec_text = st.text_area(
            "주요 키워드 입력",
            height=240,
            value=(
                "LNG 운반선, 화물창 용적 241,000 cbm, 주기관 ME-GI, "
                "서비스 속력 19.5 knots, 전장 299.0 m, 선폭 46.4 m, 만재흘수 11.5 m."
            ),
            help="주요 스펙 키워드를 입력하면 유사한 실적선 프로젝트를 찾을 수 있습니다.",
        )
        top_k = st.slider("비교 후보 수", min_value=1, max_value=5, value=3)
        run_clicked = st.button("유사 프로젝트 검색 실행", type="primary", use_container_width=True)

    if run_clicked:
        if not PROJECT_NAME_PATTERN.fullmatch(project_name.strip().upper()):
            st.warning("프로젝트명은 `HD` + 숫자 4자리 형식으로 입력해 주세요. 예: `HD9001`")
            return

        if not spec_text.strip():
            st.warning("비교할 주요 키워드나 설명을 입력해 주세요.")
            return

        normalized_project_name = project_name.strip().upper()
        result = service.search(project_name=normalized_project_name, spec_text=spec_text, top_k=top_k)
        st.session_state[SEARCH_RESULT_KEY] = result
        set_current_spec(normalized_project_name, spec_text, result["query"].attributes)
        st.session_state[SEARCH_FLASH_MESSAGE_KEY] = (
            f"현재 프로젝트 `{normalized_project_name}` 기준으로 유사 프로젝트 검색 결과를 갱신했습니다."
        )
        st.rerun()

    result = st.session_state.get(SEARCH_RESULT_KEY)
    if not result:
        return

    st.divider()
    st.subheader(
        "유사 프로젝트 검색 결과",
        help="입력한 건조사양서와 가장 가까운 실적선 프로젝트를 보여줍니다. 여기서 선택한 프로젝트가 이후 편집설계의 기준이 됩니다.",
    )

    if not result["results"]:
        st.info("비교 가능한 실적선 데이터가 없습니다.")
        return

    result_rows = [
        {
            "사양서 ID": item["spec_id"],
            "프로젝트명": item["project_name"],
            "선종": item["ship_type"],
            "유사도": round(item["score"], 3),
        }
        for item in result["results"]
    ]
    st.dataframe(pd.DataFrame(result_rows), use_container_width=True, hide_index=True)

    selected_baseline_id = st.selectbox(
        "후속 편집설계 기준으로 사용할 실적선 프로젝트 선택",
        options=[item["spec_id"] for item in result["results"]],
        format_func=lambda spec_id: next(
            f"{item['project_name']} ({item['spec_id']})"
            for item in result["results"]
            if item["spec_id"] == spec_id
        ),
    )
    selected_result = next(item for item in result["results"] if item["spec_id"] == selected_baseline_id)

    if st.button("이 프로젝트를 기준 프로젝트로 선택", type="primary", use_container_width=True):
        baseline_doc = selected_result["document"]
        set_selected_project(
            {
                "spec_id": baseline_doc.spec_id,
                "project_name": baseline_doc.project_name,
                "ship_type": baseline_doc.ship_type,
                "text": baseline_doc.text,
                "attributes": baseline_doc.attributes,
            }
        )
        st.session_state[SEARCH_FLASH_MESSAGE_KEY] = (
            f"`{baseline_doc.project_name}` 프로젝트를 기준 프로젝트로 연결했습니다. "
            "이제 POS 편집설계와 모델 편집설계에서 바로 사용할 수 있습니다."
        )
        st.rerun()

    top_doc = selected_result["document"]
    comparison = compare_spec_attributes(result["query"], top_doc)
    query_attributes = flatten_attributes(result["query"].attributes)
    baseline_attributes = flatten_attributes(top_doc.attributes)

    st.progress(max(0, min(int(selected_result["score"] * 100), 100)))
    st.caption(
        f"선택한 기준 프로젝트는 `{top_doc.spec_id}`이며, 현재 입력 사양서와의 유사도는 `{selected_result['score']:.3f}`입니다."
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("선택 프로젝트 유사도", f"{selected_result['score']:.3f}")
    metric_col2.metric(
        "공통 항목 수",
        len(comparison.get("shared_fields", [])),
        help="입력 문서와 기준 프로젝트에 모두 있는 항목 수입니다.",
    )
    metric_col3.metric(
        "차이 항목 수",
        len(comparison.get("changed_fields", [])),
        help="항목 이름은 같지만 값이 다른 항목 수입니다.",
    )
    _render_description(
        "현재는 입력한 건조사양서 문장과 기존 실적선 사양서 원문을 공백 기준 토큰으로 나눈 뒤, "
        "단어 빈도 기반 코사인 유사도로 점수를 계산합니다. "
        "차후에는 RAG 기반으로 원문 문맥까지 함께 탐색해 더 정교하게 기준 프로젝트를 찾을 수 있습니다."
    )

    summary_col1, summary_col2 = st.columns(2)
    with summary_col1:
        st.markdown("#### 선택한 기준 프로젝트")
        st.write(f"- 사양서 ID: `{top_doc.spec_id}`")
        st.write(f"- 프로젝트명: `{top_doc.project_name}`")
        st.write(f"- 선종: `{top_doc.ship_type or '-'}`")
        st.write(f"- 전체 정리 항목 수: `{len(baseline_attributes)}`")
    with summary_col2:
        st.markdown("#### 비교 요약")
        st.write(f"- 공통 항목: `{len(comparison.get('shared_fields', []))}`")
        st.write(f"- 입력 문서에만 있는 항목: `{len(comparison.get('only_in_current', []))}`")
        st.write(f"- 기준 프로젝트에만 있는 항목: `{len(comparison.get('only_in_baseline', []))}`")
        st.write(f"- 값이 다른 항목: `{len(comparison.get('changed_fields', []))}`")

    if query_attributes:
        st.markdown(
            "#### 입력 문서에서 추출한 항목",
            help="입력한 키워드에서 읽어낸 주요 스펙 항목입니다.",
        )
        rows = [{"항목명": _display_field_name(key), "입력값": value} for key, value in query_attributes.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if comparison.get("changed_fields"):
        st.markdown("#### 변경된 항목")
        rows = [
            {
                "항목명": _display_field_name(item["field"]),
                "입력값": item["current"],
                "기준값": item["baseline"],
            }
            for item in comparison["changed_fields"]
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if baseline_attributes:
        st.markdown(
            "#### 기준 프로젝트 세부 항목",
            help="선택한 실적선 프로젝트의 주요 속성입니다. 이후 POS와 모델 편집설계의 기준 데이터로 이어집니다.",
        )
        rows = [{"항목명": _display_field_name(key), "기준값": value} for key, value in baseline_attributes.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
