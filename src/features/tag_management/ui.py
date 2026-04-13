import pandas as pd
import streamlit as st

from src.common.paths import PROCESSED_DATA_DIR, TAG_REGISTRY_DIR
from src.features.spec_search.repository import SpecRepository
from src.features.tag_management.registry_repository import TagRegistryRepository
from src.features.tag_management.tag_generator import (
    generate_tags_from_attributes,
    generate_tags_from_text,
)


SECTION_LABELS = {
    "basic_info": "기본정보",
    "principal_dimensions": "주요치수",
    "machinery": "기관",
    "cargo_system": "화물",
}


def render_tag_management_page() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #c53030;
            border-color: #c53030;
            color: white;
            font-weight: 600;
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #9b2c2c;
            border-color: #9b2c2c;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("TAG 관리")
    st.caption("건조사양서의 주요 스펙에서 디지털 스레드용 TAG를 생성하고 저장 기준을 관리합니다.")

    spec_repository = SpecRepository(PROCESSED_DATA_DIR)
    registry_repository = TagRegistryRepository(TAG_REGISTRY_DIR)
    saved_specs = spec_repository.list_all()

    title_col1, title_col2 = st.columns([4, 2])
    with title_col1:
        st.subheader(
            "TAG Naming Rule",
            help="CFIHOS 방식을 참고해 섹션, 항목, 값을 코드처럼 이어 붙이는 방식으로 TAG를 만듭니다.",
        )
    with title_col2:
        st.markdown("[ref. CFIHOS 2.0](https://www.jip36-cfihos.org/cfihos-standards/)")

    st.write("기본 형식: `SB-섹션코드-항목코드-값`")
    st.write("- `SB`: Shipbuilding 공통 접두어")
    st.write("- 섹션코드: 기본정보, 주요치수, 기관, 화물 같은 분류")
    st.write("- 항목코드: LOA, MENG, CAPA처럼 짧은 식별 코드")
    st.write("- 값: 실제 사양 값을 정규화한 부분")
    st.caption("CFIHOS를 참고한 실무용 naming rule의 첫 버전입니다.")
    st.info("현재 TAG는 속력 같은 성능값보다 선체, 기관, 화물창, 용적처럼 물리적 객체와 직접 연결되는 항목 중심으로 생성합니다.")

    source_tab1, source_tab2 = st.tabs(["이전 사양서 기준", "직접 입력 기준"])

    with source_tab1:
        if not saved_specs:
            st.info("불러올 이전 사양서가 없습니다.")
        else:
            selected_spec_id = st.selectbox(
                "TAG를 생성할 사양서 선택",
                options=[item.spec_id for item in saved_specs],
                format_func=lambda spec_id: next(
                    f"{item.project_name} ({item.spec_id})"
                    for item in saved_specs
                    if item.spec_id == spec_id
                ),
                key="tag_saved_spec",
            )
            selected_document = next(item for item in saved_specs if item.spec_id == selected_spec_id)
            selected_result = generate_tags_from_attributes(selected_document.attributes)
            _render_tag_result(
                title="선택한 사양서 기준 TAG",
                source_name=selected_document.project_name,
                source_type="saved_spec",
                result=selected_result,
                registry_repository=registry_repository,
                save_key=f"save_{selected_document.spec_id}",
            )

    with source_tab2:
        spec_text = st.text_area(
            "TAG 생성용 주요 키워드 입력",
            height=220,
            value=(
                "LNG 운반선, 화물창 용적 241,000 cbm, "
                "주기관 ME-GI, 서비스 속력 19.5 knots, "
                "전장 299.0 m, 선폭 46.4 m, 만재흘수 11.5 m."
            ),
            help="건조사양서 초안이나 주요 키워드를 입력하면 바로 TAG를 만들어볼 수 있습니다.",
        )
        if spec_text.strip():
            input_result = generate_tags_from_text(spec_text)
            _render_tag_result(
                title="입력 내용 기준 TAG",
                source_name="직접 입력",
                source_type="manual_input",
                result=input_result,
                registry_repository=registry_repository,
                save_key="save_manual_input",
            )
        else:
            st.info("TAG를 만들 키워드를 입력해 주세요.")

    st.divider()
    _render_registry_section(registry_repository)


def _render_tag_result(
    title: str,
    source_name: str,
    source_type: str,
    result: dict,
    registry_repository: TagRegistryRepository,
    save_key: str,
) -> None:
    st.divider()
    st.subheader(
        title,
        help="추출된 항목별로 TAG를 만들고, 이후 POS, 모델, BOM, 생산 데이터에 같은 TAG를 연결하는 방식으로 확장할 수 있습니다.",
    )
    st.write(f"- 기준: `{source_name}`")
    st.write(f"- 추출 항목 수: `{len(result['flat_attributes'])}`")
    st.write(f"- 생성 TAG 수: `{len(result['tags'])}`")

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("기본정보 TAG", _count_section(result["tags"], "basic_info"))
    metric_col2.metric("주요치수 TAG", _count_section(result["tags"], "principal_dimensions"))
    metric_col3.metric("기관/화물 TAG", _count_section(result["tags"], "machinery") + _count_section(result["tags"], "cargo_system"))

    tag_rows = []
    for item in result["tags"]:
        tag_rows.append(
            {
                "분류": SECTION_LABELS.get(item["section"], item["section"]),
                "항목명": item["field_name"],
                "값": item["value"],
                "TAG": item["tag_name"],
            }
        )
    st.dataframe(pd.DataFrame(tag_rows), use_container_width=True, hide_index=True)

    with st.expander("이 TAG를 어떻게 활용할 수 있나요?", expanded=False):
        st.write("이 TAG를 POS, 모델, BOM, 생산 데이터에 공통으로 붙이면 같은 스펙에서 시작된 흐름을 한 줄로 추적하기 쉬워집니다.")
        st.write("현재는 물리적 객체에 가까운 항목만 TAG로 만들고 있습니다.")
        st.write("다음 단계에서는 이 저장된 TAG를 기준으로 기존 POS를 찾아 재활용하는 흐름으로 이어집니다.")

    if st.button("현재 TAG 저장", key=save_key, type="primary", use_container_width=True):
        saved_path = registry_repository.save(
            source_type=source_type,
            source_name=source_name,
            result=result,
        )
        st.success(f"TAG 레지스트리에 저장했습니다: `{saved_path.name}`")


def _render_registry_section(registry_repository: TagRegistryRepository) -> None:
    registry_items = registry_repository.list_all()

    st.subheader(
        "저장된 TAG 레지스트리",
        help="저장해둔 TAG 묶음을 다시 불러와 기준 사양서별 TAG 체계를 확인할 수 있습니다.",
    )

    if not registry_items:
        st.info("저장된 TAG 레지스트리가 없습니다. 먼저 TAG를 생성한 뒤 저장해 주세요.")
        return

    summary_rows = []
    for item in registry_items:
        summary_rows.append(
            {
                "저장 ID": item["registry_id"],
                "기준": item["source_name"],
                "유형": item["source_type"],
                "TAG 수": item["tag_count"],
                "저장 시각": item["saved_at"],
            }
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_registry_id = st.selectbox(
        "확인할 레지스트리 선택",
        options=[item["registry_id"] for item in registry_items],
        format_func=lambda registry_id: next(
            f"{item['source_name']} ({item['registry_id']})"
            for item in registry_items
            if item["registry_id"] == registry_id
        ),
    )
    selected_item = next(item for item in registry_items if item["registry_id"] == selected_registry_id)

    st.write(f"- 기준: `{selected_item['source_name']}`")
    st.write(f"- 저장 시각: `{selected_item['saved_at']}`")
    st.write(f"- TAG 수: `{selected_item['tag_count']}`")
    st.dataframe(pd.DataFrame(selected_item["tags"]), use_container_width=True, hide_index=True)


def _count_section(tags: list[dict], section_name: str) -> int:
    return sum(1 for item in tags if item["section"] == section_name)
