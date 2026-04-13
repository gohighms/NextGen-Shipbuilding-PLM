import pandas as pd
import streamlit as st

from src.common.paths import PROCESSED_DATA_DIR
from src.features.spec_search.attribute_utils import flatten_attributes
from src.features.spec_search.repository import SpecRepository
from src.features.spec_search.service import SpecSearchService


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
    "machinery.propulsion_type": "기관 / 추진 형식",
    "cargo_system.cargo_capacity_m3": "화물 / 화물창 용적",
    "cargo_system.capacity_teu": "화물 / 적재 능력(TEU)",
    "cargo_system.cargo_tank_system": "화물 / 화물창 형식",
    "cargo_system.deadweight_ton": "화물 / 재화중량톤수",
}


def _display_field_name(field_name: str) -> str:
    return FIELD_LABELS.get(field_name, field_name)


def _build_preview_rows(saved_specs: list) -> list[dict]:
    rows = []
    for item in saved_specs:
        rows.append(
            {
                "사양서 ID": item.spec_id,
                "프로젝트명": item.project_name,
                "선종": item.ship_type,
            }
        )
    return rows


def _render_spec_preview(document) -> None:
    st.markdown("### 선택한 사양서 미리보기")

    summary_col1, summary_col2, summary_col3 = st.columns(3)
    summary_col1.metric("선종", document.ship_type or "-")
    summary_col2.metric("세부 항목 수", len(flatten_attributes(document.attributes)))
    summary_col3.metric("원문 길이", len(document.text))

    info_col1, info_col2 = st.columns([1, 2])
    with info_col1:
        st.write(f"- 사양서 ID: `{document.spec_id}`")
        st.write(f"- 프로젝트명: `{document.project_name}`")
    with info_col2:
        with st.expander("원문 요약 보기", expanded=False):
            st.write(document.text)

    tabs = st.tabs(["기본정보", "주요치수", "성능", "기관", "화물"])
    sections = [
        ("basic_info", tabs[0]),
        ("principal_dimensions", tabs[1]),
        ("performance", tabs[2]),
        ("machinery", tabs[3]),
        ("cargo_system", tabs[4]),
    ]

    for section_name, tab in sections:
        with tab:
            section_data = document.attributes.get(section_name, {})
            if not section_data:
                st.info("등록된 내용이 없습니다.")
                continue

            section_rows = []
            for key, value in section_data.items():
                field_name = f"{section_name}.{key}"
                section_rows.append(
                    {
                        "항목명": _display_field_name(field_name),
                        "값": value,
                    }
                )
            st.dataframe(pd.DataFrame(section_rows), use_container_width=True, hide_index=True)


def render_spec_search_page() -> None:
    st.title("건조사양서 유사 검색 및 비교")
    st.caption("과거 사양서와 비교해 가장 가까운 기준 문서를 찾고 주요 차이를 빠르게 확인합니다.")

    repository = SpecRepository(data_dir=PROCESSED_DATA_DIR)
    saved_specs = repository.list_all()

    if saved_specs:
        st.subheader(
            "현재 데이터 현황",
            help="지금 화면에서 비교에 활용할 수 있는 이전 사양서 목록입니다. 어떤 데이터가 들어 있는지 먼저 확인할 수 있습니다.",
        )
        st.metric("적재된 사양서 수", len(saved_specs))
        st.dataframe(
            pd.DataFrame(_build_preview_rows(saved_specs)),
            use_container_width=True,
            hide_index=True,
            height=260,
        )

        st.divider()
        selected_spec_id = st.selectbox(
            "미리볼 사양서 선택",
            options=[item.spec_id for item in saved_specs],
            format_func=lambda spec_id: next(
                f"{item.project_name} ({item.spec_id})"
                for item in saved_specs
                if item.spec_id == spec_id
            ),
        )
        selected_document = next(item for item in saved_specs if item.spec_id == selected_spec_id)
        _render_spec_preview(selected_document)
    else:
        st.subheader(
            "현재 데이터 현황",
            help="지금 화면에서 비교에 활용할 수 있는 이전 사양서 목록입니다. 어떤 데이터가 들어 있는지 먼저 확인할 수 있습니다.",
        )
        st.metric("적재된 사양서 수", 0)
        st.info("`data/processed` 아래에 비교할 사양서 데이터가 없습니다.")

    st.divider()

    input_left_col, input_right_col = st.columns([1.15, 0.85])

    with input_left_col:
        project_name = st.text_input("프로젝트명", value="LNGC-241K-NEW")
        spec_text = st.text_area(
            "주요 키워드 입력",
            height=260,
            value=(
                "LNG 운반선, 화물창 용적 241,000 cbm, "
                "주기관 ME-GI, 서비스 속력 19.5 knots, "
                "전장 299.0 m, 선폭 46.4 m, 만재흘수 11.5 m."
            ),
            help="주요 제원, 속력, 용적, 주기관처럼 핵심 항목 위주로 입력하면 됩니다.",
        )
        top_k = st.slider("비교 후보 수", min_value=1, max_value=5, value=3)
        run_clicked = st.button("검색 실행", type="primary", use_container_width=True)

    with input_right_col:
        st.markdown("### 검색 전 안내")
        st.info("먼저 위에서 이전 사양서를 확인한 뒤, 아래에 비교할 키워드를 입력하고 검색을 실행하면 흐름을 이해하기 쉽습니다.")

    if not run_clicked:
        return

    if not spec_text.strip():
        st.warning("비교할 키워드나 설명을 입력해 주세요.")
        return

    service = SpecSearchService(repository=repository)
    result = service.search(project_name=project_name, spec_text=spec_text, top_k=top_k)

    st.divider()
    st.subheader(
        "유사 문서 검색 결과",
        help="입력한 키워드와 이전 사양서 설명을 비교해 가장 비슷한 문서를 찾은 결과입니다. 현재는 문장 유사도 중심의 1차 검색입니다.",
    )

    if not result["results"]:
        st.info("비교 가능한 샘플 데이터가 없습니다.")
        return

    result_rows = []
    for item in result["results"]:
        result_rows.append(
            {
                "사양서 ID": item["spec_id"],
                "프로젝트명": item["project_name"],
                "선종": item["ship_type"],
                "유사도": round(item["score"], 3),
            }
        )
    st.dataframe(pd.DataFrame(result_rows), use_container_width=True, hide_index=True)

    top_item = result["results"][0]
    top_doc = top_item["document"]
    comparison = result["comparison"]
    query_attributes = flatten_attributes(result["query"].attributes)
    baseline_attributes = flatten_attributes(top_doc.attributes)

    st.progress(max(0, min(int(top_item["score"] * 100), 100)))
    st.caption(f"현재 입력 내용은 `{top_doc.spec_id}`와 가장 가깝고, 유사도는 `{top_item['score']:.3f}`입니다.")

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("최상위 유사도", f"{top_item['score']:.3f}")
    metric_col2.metric(
        "공통 항목 수",
        len(comparison.get("shared_fields", [])),
        help="입력 문서와 기준 문서에 모두 존재하는 항목 수입니다. 서로 직접 비교할 수 있는 항목의 개수로 보면 됩니다.",
    )
    metric_col3.metric(
        "차이 항목 수",
        len(comparison.get("changed_fields", [])),
        help="이름은 같지만 값이 서로 다르게 나온 항목 수입니다. 실제 검토가 필요한 변경 포인트로 볼 수 있습니다.",
    )

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        st.markdown("#### 가장 유사한 기준 문서")
        st.write(f"- 사양서 ID: `{top_doc.spec_id}`")
        st.write(f"- 프로젝트명: `{top_doc.project_name}`")
        st.write(f"- 선종: `{top_doc.ship_type or '-'}`")
        st.write(f"- 세부 항목 수: `{len(baseline_attributes)}`")

    with detail_col2:
        st.markdown("#### 비교 요약")
        st.write(f"- 공통 항목: `{len(comparison.get('shared_fields', []))}`")
        st.write(f"- 입력 문서에만 있는 항목: `{len(comparison.get('only_in_current', []))}`")
        st.write(f"- 기준 문서에만 있는 항목: `{len(comparison.get('only_in_baseline', []))}`")
        st.write(f"- 값이 다른 항목: `{len(comparison.get('changed_fields', []))}`")

    if query_attributes:
        st.markdown(
            "#### 입력 문서에서 추출한 항목",
            help="입력한 키워드나 설명에서 시스템이 읽어낸 주요 제원과 속성입니다. 실제 비교는 이 항목들을 기준으로 함께 참고합니다.",
        )
        extracted_rows = [
            {"항목명": _display_field_name(key), "입력값": value}
            for key, value in query_attributes.items()
        ]
        st.dataframe(pd.DataFrame(extracted_rows), use_container_width=True, hide_index=True)

    if comparison.get("changed_fields"):
        st.markdown("#### 변경된 항목")
        changed_rows = []
        for item in comparison["changed_fields"]:
            changed_rows.append(
                {
                    "항목명": _display_field_name(item["field"]),
                    "입력값": item["current"],
                    "기준값": item["baseline"],
                }
            )
        st.dataframe(pd.DataFrame(changed_rows), use_container_width=True, hide_index=True)

    if baseline_attributes:
        st.markdown(
            "#### 기준 문서 세부 항목",
            help="가장 유사한 것으로 판단된 이전 사양서의 세부 항목입니다. 입력 문서와 비교할 때 기준점으로 사용하는 데이터입니다.",
        )
        baseline_rows = [
            {"항목명": _display_field_name(key), "기준값": value}
            for key, value in baseline_attributes.items()
        ]
        st.dataframe(pd.DataFrame(baseline_rows), use_container_width=True, hide_index=True)
