import pandas as pd
import streamlit as st

from src.common.paths import MODEL_DRAFT_DIR, POS_DRAFT_DIR
from src.features.design_change_management.service import (
    build_assumed_current_project_model,
    build_change_scenario,
)
from src.features.model_generation.draft_repository import ModelDraftRepository
from src.features.pos_generation.draft_repository import PosDraftRepository


def render_design_change_management_page() -> None:
    st.title("설계 변경 관리")
    st.caption("설계가 일정 수준 완성된 상태를 가정하고, 이후 발생하는 변경 요청과 리비전 관리를 다룹니다.")

    model_draft_repository = ModelDraftRepository(MODEL_DRAFT_DIR)
    pos_draft_repository = PosDraftRepository(POS_DRAFT_DIR)
    model_drafts = model_draft_repository.list_all()
    pos_drafts = pos_draft_repository.list_all()

    if not model_drafts:
        st.info("먼저 `설계 자산 재활용 > 모델 편집설계`에서 모델 시작 구조를 저장해 주세요.")
        return

    selected_model_draft_id = st.selectbox(
        "변경 관리를 시작할 모델 초안 선택",
        options=[item["draft_id"] for item in model_drafts],
        format_func=lambda draft_id: next(
            f"{item['title']} ({item['draft_id']})"
            for item in model_drafts
            if item["draft_id"] == draft_id
        ),
    )
    selected_model_draft = next(item for item in model_drafts if item["draft_id"] == selected_model_draft_id)
    selected_pos_draft = next(
        (item for item in pos_drafts if item["draft_id"] == selected_model_draft.get("source_pos_draft_id")),
        None,
    )

    assumed_model = build_assumed_current_project_model(selected_model_draft)

    st.divider()
    st.subheader("현 프로젝트 설계 초안 상태")
    top_col1, top_col2 = st.columns(2)
    with top_col1:
        st.write(f"- 프로젝트명: `{assumed_model['project_name']}`")
        st.write(f"- 기준 실적선: `{assumed_model['source_project_name']}`")
        st.write(f"- 기준 모델: `{assumed_model['base_model_id']}`")
    with top_col2:
        st.write(f"- 설계 분야: `{assumed_model['discipline']}`")
        st.write(f"- 모델 부품 수: `{len(assumed_model['model_hierarchy'])}`")
        st.write(f"- POS 참조: `{selected_pos_draft['draft_id'] if selected_pos_draft else '-'}`")

    st.markdown("#### 현재 설계 초안 모델 구조")
    model_rows = _build_model_rows(assumed_model["model_hierarchy"])
    st.dataframe(
        pd.DataFrame(model_rows),
        use_container_width=True,
        hide_index=True,
        height=640,
    )

    st.divider()
    st.subheader("ECR 등록")
    form_col1, form_col2 = st.columns(2)
    with form_col1:
        request_title = st.text_input("ECR 제목", value="배관 통과용 hole 추가 요청")
        request_reason = st.text_area(
            "ECR 사유",
            height=120,
            value="배관 설계 검토 결과, 현측 외판 통과 구간에 pipe passage hole이 누락되어 선체와 의장 간 협업 변경이 필요함.",
        )
        target_field = st.selectbox(
            "변경 대상",
            options=["coordination.pipe_hole"],
            format_func=_format_target_field,
        )
    with form_col2:
        before_value, after_value = _default_before_after_values(target_field)
        current_before = st.text_input("변경 전 상태", value=before_value)
        current_after = st.text_input("변경 후 상태", value=after_value)
        requester = st.text_input("ECR 요청자", value="배관설계팀")
        urgency = st.selectbox("긴급도", options=["하", "중", "상"], index=1)

    scenario = build_change_scenario(
        assumed_model=assumed_model,
        pos_draft=selected_pos_draft,
        request_title=request_title,
        request_reason=request_reason,
        target_field=target_field,
        before_value=current_before,
        after_value=current_after,
        requester=requester,
        urgency=urgency,
    )

    st.divider()
    st.subheader("ECR 전 / 후 비교")
    comparison_rows = [
        {
            "변경 항목": _format_target_field(target_field),
            "변경 전": scenario["before_value"],
            "변경 후": scenario["after_value"],
            "변경 사유": scenario["request_reason"],
        }
    ]
    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

    st.markdown("#### 영향 예상 구조")
    st.caption("차후에는 지식 그래프 기반 관계 정보와 GNN 등의 영향 분석 방법을 함께 적용해 더 지능적으로 영향 범위를 추정할 수 있습니다.")
    st.dataframe(
        pd.DataFrame(scenario["impacted_structures"]),
        use_container_width=True,
        hide_index=True,
        height=360,
    )

    st.divider()
    st.subheader("구매 / 생산 영향 검토")
    st.caption("자재와 기자재의 상태를 TAG 기반으로 연결 추적하여, 구매 및 생산 진행 상태를 함께 파악하는 시나리오입니다.")
    decision_col1, decision_col2, decision_col3 = st.columns(3)
    decision_col1.metric("변경 판단", scenario["supply_decision"]["decision"])
    decision_col2.metric("고위험 항목", scenario["supply_decision"]["high_risk_count"])
    decision_col3.metric("영향 항목 수", len(scenario["supply_impact_rows"]))
    st.info(scenario["supply_decision"]["summary"])
    st.dataframe(
        _style_status_rows(pd.DataFrame(scenario["supply_impact_rows"]), "변경 위험도", {"높음"}),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("ECO 검토")
    st.dataframe(
        _style_status_rows(pd.DataFrame(scenario["impact_rows"]), "영향도", {"상"}),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("ECN 및 변경 생애주기")
    lifecycle_col1, lifecycle_col2 = st.columns(2)
    with lifecycle_col1:
        st.markdown("#### ECR / ECO / ECN")
        st.dataframe(
            _style_status_rows(pd.DataFrame(scenario["lifecycle_rows"]), "상태", {"진행중"}),
            use_container_width=True,
            hide_index=True,
        )
    with lifecycle_col2:
        st.markdown("#### Rev 이력")
        st.dataframe(pd.DataFrame(scenario["revision_rows"]), use_container_width=True, hide_index=True)

    st.markdown("#### 검토 상태")
    review_rows = [
        {"검토 항목": "ECR 등록", "상태": "완료"},
        {"검토 항목": "ECO 작업 검토", "상태": "진행중"},
        {"검토 항목": "ECN 발행", "상태": "대기"},
    ]
    st.dataframe(pd.DataFrame(review_rows), use_container_width=True, hide_index=True)

def _build_model_rows(hierarchy_items: list[dict]) -> list[dict]:
    rows = []
    for item in hierarchy_items:
        level = max(item["path"].count("/") - 1, 0)
        design_structure = item.get("design_structure", item.get("type", "모델 구조"))
        rows.append(
            {
                "구조레벨": level,
                "ID": item.get("node_code", item["path"].split("/")[-1]),
                "모델명": item.get("name", item["path"].split("/")[-1]),
                "설계구조": design_structure,
                "모델타입": item.get("model_type", item.get("type", "모델 항목")),
                "모델경로": item["path"],
                "생성조직": item.get("organization") or _default_organization(design_structure),
                "담당 설계": item.get("designer") or _default_designer(design_structure),
                "개정": item.get("revision", "R01"),
            }
        )
    return rows


def _default_organization(design_structure: str) -> str:
    mapping = {
        "선체": "선체설계팀",
        "의장-철의": "철의설계팀",
        "의장-목의": "목의설계팀",
        "의장-배관": "배관설계팀",
        "의장-전장": "전장설계팀",
        "의장-기계": "기계설계팀",
    }
    return mapping.get(design_structure, "설계팀")


def _default_designer(design_structure: str) -> str:
    mapping = {
        "선체": "선체설계 담당",
        "의장-철의": "철의설계 담당",
        "의장-목의": "목의설계 담당",
        "의장-배관": "배관설계 담당",
        "의장-전장": "전장설계 담당",
        "의장-기계": "기계설계 담당",
    }
    return mapping.get(design_structure, "설계 담당")


def _format_target_field(field_name: str) -> str:
    label_map = {
        "coordination.pipe_hole": "배관 통과용 hole 추가",
    }
    return label_map.get(field_name, field_name)


def _default_before_after_values(target_field: str) -> tuple[str, str]:
    value_map = {
        "coordination.pipe_hole": ("관련 hole 없음", "관련 hole 1EA 추가"),
    }
    return value_map[target_field]


def _style_status_rows(dataframe: pd.DataFrame, status_column: str, highlighted_statuses: set[str]):
    def highlight_row(row: pd.Series) -> list[str]:
        if row[status_column] in highlighted_statuses:
            return ["background-color: #fff7cc; color: #111111"] * len(row)
        return [""] * len(row)

    return dataframe.style.apply(highlight_row, axis=1)
