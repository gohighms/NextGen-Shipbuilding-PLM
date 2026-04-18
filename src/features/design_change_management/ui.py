import pandas as pd
import streamlit as st

from src.common.paths import DESIGN_CHANGE_DIR, MODEL_DRAFT_DIR, POS_DRAFT_DIR
from src.features.design_change_management.repository import DesignChangeRepository
from src.features.design_change_management.service import (
    build_assumed_current_project_model,
    build_change_scenario,
)
from src.features.model_generation.draft_repository import ModelDraftRepository
from src.features.pos_generation.draft_repository import PosDraftRepository


def render_design_change_management_page() -> None:
    st.title("설계 변경 관리")
    st.caption(
        "편집설계를 통해 마련된 초기 구조를 바탕으로 현 프로젝트 설계 초안이 일정 수준 완성된 상태를 가정하고, "
        "이후 발생하는 변경 요청과 리비전 관리를 다룹니다."
    )
    st.info("이 화면은 Teamcenter식 변경 생애주기 개념을 참고해 `ECR → ECO → ECN` 흐름으로 구성했습니다.")

    model_draft_repository = ModelDraftRepository(MODEL_DRAFT_DIR)
    pos_draft_repository = PosDraftRepository(POS_DRAFT_DIR)
    change_repository = DesignChangeRepository(DESIGN_CHANGE_DIR)

    model_drafts = model_draft_repository.list_all()
    pos_drafts = pos_draft_repository.list_all()

    if not model_drafts:
        st.info("먼저 `실적선 기반 설계 재활용 > 유사 프로젝트 기반 모델 편집설계`에서 모델 시작 구조를 저장해 주세요.")
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
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 프로젝트명: `{assumed_model['project_name']}`")
        st.write(f"- 기준 실적선: `{assumed_model['source_project_name']}`")
        st.write(f"- 기준 모델: `{assumed_model['base_model_id']}`")
        st.write(f"- 설계 상태: `{assumed_model['design_status']}`")
    with top_col2:
        st.write(f"- 설계 분야: `{assumed_model['discipline']}`")
        st.write(f"- 모델 노드 수: `{len(assumed_model['model_hierarchy'])}`")
        st.write(f"- POS 참조: `{selected_pos_draft['draft_id'] if selected_pos_draft else '-'}`")
        st.write("- 가정: 설계자가 편집설계 이후 추가 설계를 진행한 상태")

    st.markdown("#### 현재 설계 초안 모델 구조")
    st.dataframe(
        pd.DataFrame(_build_model_rows(assumed_model["model_hierarchy"])),
        use_container_width=True,
        hide_index=True,
        height=640,
    )

    st.divider()
    st.subheader("ECR 등록")
    form_col1, form_col2 = st.columns([1, 1])
    with form_col1:
        request_title = st.text_input("ECR 제목", value="배관 통과용 hole 추가 요청")
        request_reason = st.text_area(
            "ECR 사유",
            height=120,
            value="배관설계 검토 결과, 현측 외판 통과 구간에 pipe passage hole이 누락되어 선체와 의장 협업 변경이 필요함.",
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
        requester = st.text_input("ECR 요청자", value="배관설계부")
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
    st.subheader("변경 전 / 후 비교")
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
    st.dataframe(
        pd.DataFrame(scenario["impacted_structures"]),
        use_container_width=True,
        hide_index=True,
        height=360,
    )

    st.divider()
    st.subheader("구매 / 생산 영향 검토")
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
    lifecycle_col1, lifecycle_col2 = st.columns([1, 1])
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
        {"검토 항목": "ECO 협업 검토", "상태": "진행중"},
        {"검토 항목": "ECN 발행", "상태": "대기"},
    ]
    st.dataframe(pd.DataFrame(review_rows), use_container_width=True, hide_index=True)

    if st.button("변경 요청 저장", type="primary", use_container_width=True):
        saved_path = change_repository.save(scenario)
        st.success(f"설계 변경 요청을 저장했습니다. `{saved_path.name}`")

    st.divider()
    _render_saved_change_requests(change_repository)


def _build_model_rows(hierarchy_items: list[dict]) -> list[dict]:
    rows = []
    for item in hierarchy_items:
        level = max(item["path"].count("/") - 1, 0)
        rows.append(
            {
                "구조레벨": level,
                "노드코드": item.get("node_code", item["path"].split("/")[-1]),
                "노드명": item.get("name", item["path"].split("/")[-1]),
                "설계구조": item.get("design_structure", item.get("type", "모델 구조")),
                "모델타입": item.get("model_type", item.get("type", "모델 항목")),
                "사양기준": item.get("spec_basis", "-"),
                "모델경로": item["path"],
                "생성조직": item.get("organization", "-"),
                "담당설계": item.get("designer", "-"),
                "개정": item.get("revision", "R01"),
            }
        )
    return rows


def _format_target_field(field_name: str) -> str:
    label_map = {
        "coordination.pipe_hole": "배관 통과용 hole 추가",
    }
    return label_map.get(field_name, field_name)


def _default_before_after_values(target_field: str) -> tuple[str, str]:
    value_map = {
        "coordination.pipe_hole": ("관통 hole 없음", "관통 hole 1EA 추가"),
    }
    return value_map[target_field]


def _style_status_rows(dataframe: pd.DataFrame, status_column: str, highlighted_statuses: set[str]):
    def highlight_row(row):
        if row[status_column] in highlighted_statuses:
            return ["background-color: #fff7cc; color: #111111"] * len(row)
        return [""] * len(row)

    return dataframe.style.apply(highlight_row, axis=1)


def _render_saved_change_requests(change_repository: DesignChangeRepository) -> None:
    st.subheader("저장된 변경 요청 이력")
    items = change_repository.list_all()
    if not items:
        st.info("저장된 설계 변경 요청이 없습니다.")
        return

    summary_rows = [
        {
            "요청 ID": item["request_id"],
            "프로젝트": item["project_name"],
            "변경 제목": item["request_title"],
            "요청자": item["requester"],
            "긴급도": item["urgency"],
            "저장 시각": item["saved_at"],
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_request_id = st.selectbox(
        "확인할 변경 요청 선택",
        options=[item["request_id"] for item in items],
        format_func=lambda request_id: next(
            f"{item['request_title']} ({item['request_id']})"
            for item in items
            if item["request_id"] == request_id
        ),
    )
    selected_item = next(item for item in items if item["request_id"] == selected_request_id)

    detail_col1, detail_col2 = st.columns([1, 1])
    with detail_col1:
        st.write(f"- 요청 ID: `{selected_item['request_id']}`")
        st.write(f"- 프로젝트: `{selected_item['project_name']}`")
        st.write(f"- 변경 제목: `{selected_item['request_title']}`")
        st.write(f"- 요청자: `{selected_item['requester']}`")
        st.write(f"- 긴급도: `{selected_item['urgency']}`")
    with detail_col2:
        st.write(f"- 변경 대상: `{_format_target_field(selected_item['target_field'])}`")
        st.write(f"- 변경 전: `{selected_item['before_value']}`")
        st.write(f"- 변경 후: `{selected_item['after_value']}`")
        st.write(f"- POS 참조: `{selected_item['pos_reference']}`")

    if selected_item.get("supply_decision"):
        st.markdown("#### 저장된 구매 / 생산 영향 검토")
        top_col1, top_col2, top_col3 = st.columns(3)
        top_col1.metric("변경 판단", selected_item["supply_decision"]["decision"])
        top_col2.metric("고위험 항목", selected_item["supply_decision"]["high_risk_count"])
        top_col3.metric("영향 항목 수", len(selected_item.get("supply_impact_rows", [])))
        st.info(selected_item["supply_decision"]["summary"])
        st.dataframe(
            _style_status_rows(
                pd.DataFrame(selected_item.get("supply_impact_rows", [])),
                "변경 위험도",
                {"높음"},
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("#### 저장된 ECO 검토 내용")
    st.dataframe(
        _style_status_rows(pd.DataFrame(selected_item["impact_rows"]), "영향도", {"상"}),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### 저장된 ECR / ECO / ECN")
    st.dataframe(
        _style_status_rows(pd.DataFrame(selected_item["lifecycle_rows"]), "상태", {"진행중"}),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### 저장된 Rev 이력")
    st.dataframe(pd.DataFrame(selected_item["revision_rows"]), use_container_width=True, hide_index=True)
