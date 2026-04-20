import pandas as pd
import streamlit as st

from src.common.paths import POS_DATA_DIR, POS_DRAFT_DIR
from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.pos_generation.draft_repository import PosDraftRepository
from src.features.pos_generation.repository import PosRepository
from src.features.pos_generation.service import (
    build_pos_document_text,
    build_pos_draft,
    build_pos_edit_direction,
    find_pos_documents_for_project,
)


def render_pos_generation_page() -> None:
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

    st.title("POS 사양 재구성")
    st.caption("선택한 유사 프로젝트의 POS를 기준으로 현재 프로젝트 POS 초안을 재구성합니다.")

    selected_project = get_selected_project()
    current_spec = get_current_spec()

    if not selected_project or not current_spec:
        st.info("먼저 `유사 프로젝트 탐색`에서 기준 프로젝트를 선택해 주세요.")
        return

    pos_repository = PosRepository(POS_DATA_DIR)
    draft_repository = PosDraftRepository(POS_DRAFT_DIR)
    pos_items = find_pos_documents_for_project(selected_project, pos_repository.list_all())

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{current_spec['project_name']}`")
        st.write(f"- 선택한 기준 프로젝트: `{selected_project['project_name']}`")
        st.write(f"- 기준 사양서 ID: `{selected_project['spec_id']}`")
    with top_col2:
        st.write(f"- 현재 프로젝트 추출 항목 수: `{len(current_spec.get('attributes', {}))}`")
        st.write(f"- 기준 프로젝트 선종: `{selected_project.get('ship_type', '-')}`")
        st.write("- 활용 방식: `선택한 유사 프로젝트 POS를 기준으로 편집설계`")

    if not pos_items:
        st.divider()
        st.warning("선택한 기준 프로젝트와 연결된 POS 샘플이 아직 없습니다.")
        return

    st.divider()
    st.subheader("기준 프로젝트 POS")
    pos_rows = [
        {
            "POS ID": item["pos_id"],
            "문서명": item["title"],
            "담당부서": item["department"],
            "기준 프로젝트": item.get("source_project_name", "-"),
        }
        for item in pos_items
    ]
    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)

    selected_pos_id = st.selectbox(
        "편집설계 기준 POS 선택",
        options=[item["pos_id"] for item in pos_items],
        format_func=lambda pos_id: next(
            f"{item['title']} ({item['pos_id']})"
            for item in pos_items
            if item["pos_id"] == pos_id
        ),
    )
    selected_pos = next(item for item in pos_items if item["pos_id"] == selected_pos_id)
    draft = build_pos_draft(current_spec, selected_project, selected_pos)

    st.divider()
    baseline_col1, baseline_col2 = st.columns([1, 1])
    with baseline_col1:
        st.markdown("#### 기준 POS 미리보기")
        st.write(f"- POS ID: `{selected_pos['pos_id']}`")
        st.write(f"- 문서명: `{selected_pos['title']}`")
        st.write(f"- 담당부서: `{selected_pos['department']}`")
        st.dataframe(pd.DataFrame(selected_pos["sections"]), use_container_width=True, hide_index=True, height=420)

    with baseline_col2:
        st.markdown("#### 기준 POS 원문")
        st.text_area(
            "기준 POS 원문",
            value=build_pos_document_text(selected_pos),
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )

    st.divider()
    current_col1, current_col2 = st.columns([1, 1])
    with current_col1:
        st.markdown("#### 현재 프로젝트 POS 편집")
        edited_title = st.text_input("초안 문서명", value=draft["title"])
        edited_department = st.text_input("담당 부서", value=draft["department"], disabled=True)
        change_note = st.text_area(
            "Change Note",
            height=180,
            value=(
                f"{selected_project['project_name']} POS를 기준으로 가져오고 "
                f"{current_spec['project_name']} 사양 차이를 반영해 문구를 수정할 예정."
            ),
        )

        st.write(f"- 새 POS ID: `{draft['new_pos_id']}`")
        st.write(f"- 기준 프로젝트: `{draft['source_project_name']}`")
        st.write(f"- 재활용한 POS: `{draft['based_on_pos_id']}`")

    with current_col2:
        st.markdown("#### 현재 프로젝트 POS 초안")
        final_draft = {
            **draft,
            "title": edited_title,
            "department": edited_department,
            "document_text": build_pos_document_text(
                {
                    **draft,
                    "title": edited_title,
                    "department": edited_department,
                    "_force_regenerate": True,
                },
                change_note=change_note,
            ),
        }
        st.text_area(
            "현재 프로젝트 POS 초안",
            value=final_draft["document_text"],
            height=300,
            disabled=True,
            label_visibility="collapsed",
        )
        if st.button("현재 POS 초안 저장", type="primary", use_container_width=True):
            saved_path = draft_repository.save(final_draft, change_note=change_note)
            st.success(f"POS 초안을 저장했습니다. `{saved_path.name}`")

    draft_rows = []
    for section in draft["sections"]:
        edit_direction = build_pos_edit_direction(section["section"], current_spec.get("attributes", {}))
        needs_change = any(keyword in edit_direction for keyword in ["조정", "다시 정리", "보완", "차이"])
        draft_rows.append(
            {
                "섹션": section["section"],
                "기준 내용": section["content"],
                "편집 방향": edit_direction,
                "판정": "검토 필요" if needs_change else "유지 가능",
            }
        )

    st.markdown("#### 현재 프로젝트 POS 편집 검토표")
    st.dataframe(pd.DataFrame(draft_rows), use_container_width=True, hide_index=True, height=260)

    st.divider()
    _render_saved_drafts(draft_repository, current_spec["project_name"])
def _render_saved_drafts(draft_repository: PosDraftRepository, current_project_name: str) -> None:
    st.subheader("저장된 POS 초안 및 이력")

    draft_items = [
        item
        for item in draft_repository.list_all()
        if item.get("current_project_name") == current_project_name
    ]
    if not draft_items:
        st.info("현재 프로젝트 기준으로 저장된 POS 초안이 없습니다.")
        return

    summary_rows = [
        {
            "초안 ID": item["draft_id"],
            "문서명": item["title"],
            "기준 프로젝트": item.get("source_project_name", "-"),
            "재활용 POS": item["based_on_pos_id"],
            "저장 시각": item["saved_at"],
        }
        for item in draft_items
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_draft_id = st.selectbox(
        "확인할 POS 초안 선택",
        options=[item["draft_id"] for item in draft_items],
        format_func=lambda draft_id: next(
            f"{item['title']} ({item['draft_id']})"
            for item in draft_items
            if item["draft_id"] == draft_id
        ),
    )
    selected_item = next(item for item in draft_items if item["draft_id"] == selected_draft_id)

    detail_col1, detail_col2 = st.columns([1, 1])
    with detail_col1:
        st.write(f"- 초안 ID: `{selected_item['draft_id']}`")
        st.write(f"- 문서명: `{selected_item['title']}`")
        st.write(f"- 기준 프로젝트: `{selected_item.get('source_project_name', '-')}`")
        st.write(f"- 재활용 POS: `{selected_item['based_on_pos_id']}`")
        st.write(f"- 저장 시각: `{selected_item['saved_at']}`")
    with detail_col2:
        st.markdown("#### Change Note")
        st.write(selected_item["change_note"])

    st.markdown("#### 저장된 POS 초안 섹션")
    st.dataframe(pd.DataFrame(selected_item["sections"]), use_container_width=True, hide_index=True)

    st.markdown("#### 저장된 POS 초안 원문")
    st.text_area(
        "저장된 POS 초안 원문",
        value=selected_item.get("document_text", build_pos_document_text(selected_item, selected_item["change_note"])),
        height=420,
        disabled=True,
        label_visibility="collapsed",
    )
