import pandas as pd
import streamlit as st

from src.common.paths import POS_DATA_DIR, POS_DRAFT_DIR, TAG_REGISTRY_DIR
from src.features.pos_generation.draft_repository import PosDraftRepository
from src.features.pos_generation.repository import PosRepository
from src.features.pos_generation.service import (
    build_pos_document_text,
    build_pos_draft,
    recommend_pos_documents,
)
from src.features.tag_management.registry_repository import TagRegistryRepository


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

    st.title("POS 생성")
    st.caption("저장된 TAG를 기준으로 기존 POS를 재활용하고, 수정 초안과 이력을 관리합니다.")

    registry_repository = TagRegistryRepository(TAG_REGISTRY_DIR)
    pos_repository = PosRepository(POS_DATA_DIR)
    draft_repository = PosDraftRepository(POS_DRAFT_DIR)

    registry_items = registry_repository.list_all()
    pos_items = pos_repository.list_all()

    if not registry_items:
        st.info("먼저 TAG 관리 메뉴에서 TAG를 저장해 주세요. 저장된 TAG 레지스트리가 있어야 POS 추천이 가능합니다.")
        return

    if not pos_items:
        st.info("비교할 기존 POS 샘플이 없습니다.")
        return

    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        selected_registry_id = st.selectbox(
            "기준 TAG 레지스트리 선택",
            options=[item["registry_id"] for item in registry_items],
            format_func=lambda registry_id: next(
                f"{item['source_name']} ({item['registry_id']})"
                for item in registry_items
                if item["registry_id"] == registry_id
            ),
        )
        selected_registry = next(item for item in registry_items if item["registry_id"] == selected_registry_id)
        st.write(f"- 기준 사양: `{selected_registry['source_name']}`")
        st.write(f"- TAG 수: `{selected_registry['tag_count']}`")

    with top_col2:
        st.subheader(
            "POS 생성 흐름",
            help="저장된 TAG와 일치하는 기존 POS를 먼저 추천한 뒤, 적합한 문서를 복사해 수정 초안을 만드는 방식입니다.",
        )
        st.write("1. 기준 TAG 선택")
        st.write("2. 기존 POS 추천 확인")
        st.write("3. 재활용할 POS 선택")
        st.write("4. 수정 초안 저장")

    st.divider()
    st.subheader(
        "추천 POS 후보",
        help="선택한 TAG와 많이 겹치는 기존 POS를 우선적으로 보여줍니다. 공통 TAG가 많을수록 재활용 가능성이 높습니다.",
    )

    recommended_items = recommend_pos_documents(selected_registry, pos_items, top_k=3)
    recommendation_rows = []
    for item in recommended_items:
        recommendation_rows.append(
            {
                "POS ID": item["pos_id"],
                "문서명": item["title"],
                "부서": item["department"],
                "일치 TAG 수": item["score"],
                "공통 TAG": ", ".join(item["matched_tags"]) if item["matched_tags"] else "-",
            }
        )
    st.dataframe(pd.DataFrame(recommendation_rows), use_container_width=True, hide_index=True)

    selected_pos_id = st.selectbox(
        "재활용할 POS 선택",
        options=[item["pos_id"] for item in recommended_items],
        format_func=lambda pos_id: next(
            f"{item['title']} ({item['pos_id']})"
            for item in recommended_items
            if item["pos_id"] == pos_id
        ),
    )
    selected_pos = next(item for item in recommended_items if item["pos_id"] == selected_pos_id)["document"]
    draft = build_pos_draft(selected_registry, selected_pos)

    st.divider()
    preview_col1, preview_col2 = st.columns([1, 1])
    with preview_col1:
        st.markdown("#### 선택한 기존 POS 미리보기")
        st.write(f"- POS ID: `{selected_pos['pos_id']}`")
        st.write(f"- 문서명: `{selected_pos['title']}`")
        st.write(f"- 부서: `{selected_pos['department']}`")
        st.write(f"- 적용 TAG 수: `{len(selected_pos.get('tags', []))}`")
        st.dataframe(pd.DataFrame(selected_pos["sections"]), use_container_width=True, hide_index=True)

    with preview_col2:
        st.markdown("#### 수정 초안 작성")
        edited_title = st.text_input("초안 문서명", value=draft["title"])
        edited_department = st.text_input("담당 부서", value=draft["department"])
        change_note = st.text_area(
            "수정 메모",
            height=180,
            value="주요 사양 변경사항을 반영해 기관/화물 시스템 관련 항목을 우선 수정 예정.",
        )

        st.write(f"- 새 POS 초안 ID: `{draft['new_pos_id']}`")
        st.write(f"- 기준 TAG 레지스트리: `{draft['source_registry_id']}`")
        st.write(f"- 재활용 원본 POS: `{draft['based_on_pos_id']}`")

        draft_rows = []
        for section in draft["sections"]:
            draft_rows.append(
                {
                    "섹션": section["section"],
                    "기존 내용": section["content"],
                    "수정 방향": _build_edit_hint(section["section"], selected_registry["tags"]),
                }
            )
        st.dataframe(pd.DataFrame(draft_rows), use_container_width=True, hide_index=True)

        st.info("기존 POS를 완전히 새로 작성하기보다, TAG 기준으로 가까운 문서를 가져와 재편집하는 시나리오입니다.")

        final_draft = {
            **draft,
            "title": edited_title,
            "department": edited_department,
            "document_text": build_pos_document_text(
                {
                    **draft,
                    "title": edited_title,
                    "department": edited_department,
                },
                change_note=change_note,
            ),
        }

        if st.button("POS 초안 저장", type="primary", use_container_width=True):
            saved_path = draft_repository.save(final_draft, change_note=change_note)
            st.success(f"POS 초안을 저장했습니다: `{saved_path.name}`")

    st.divider()
    st.subheader(
        "POS 원문 보기",
        help="표 형태의 구조화 정보뿐 아니라, 실제 POS 문서처럼 읽을 수 있는 본문 형태를 함께 확인합니다.",
    )
    text_col1, text_col2 = st.columns([1, 1])
    with text_col1:
        st.markdown("#### 기존 POS 원문")
        st.text_area(
            "기존 POS 문서 본문",
            value=build_pos_document_text(selected_pos),
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )
    with text_col2:
        st.markdown("#### 새 POS 초안 원문")
        draft_preview_text = build_pos_document_text(
            {
                **draft,
                "title": edited_title,
                "department": edited_department,
            },
            change_note=change_note,
        )
        st.text_area(
            "새 POS 초안 문서 본문",
            value=draft_preview_text,
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )

    st.divider()
    _render_saved_draft_section(draft_repository)


def _render_saved_draft_section(draft_repository: PosDraftRepository) -> None:
    st.subheader(
        "저장된 POS 초안 및 이력",
        help="저장한 POS 초안을 다시 불러와 기준 TAG, 원본 POS, 수정 메모를 함께 확인할 수 있습니다.",
    )

    draft_items = draft_repository.list_all()
    if not draft_items:
        st.info("저장된 POS 초안이 없습니다. 위에서 수정 초안을 저장해 주세요.")
        return

    summary_rows = []
    for item in draft_items:
        summary_rows.append(
            {
                "초안 ID": item["draft_id"],
                "문서명": item["title"],
                "기준 TAG": item["source_registry_id"],
                "원본 POS": item["based_on_pos_id"],
                "저장 시각": item["saved_at"],
            }
        )
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
        st.write(f"- 기준 TAG 레지스트리: `{selected_item['source_registry_id']}`")
        st.write(f"- 원본 POS: `{selected_item['based_on_pos_id']}`")
        st.write(f"- 담당 부서: `{selected_item['department']}`")
        st.write(f"- 저장 시각: `{selected_item['saved_at']}`")
    with detail_col2:
        st.markdown("#### 수정 메모")
        st.write(selected_item["change_note"])

    st.markdown("#### 저장된 초안 섹션")
    st.dataframe(pd.DataFrame(selected_item["sections"]), use_container_width=True, hide_index=True)

    st.markdown("#### 저장된 POS 초안 원문")
    st.text_area(
        "저장된 POS 초안 원문",
        value=selected_item.get("document_text", build_pos_document_text(selected_item, selected_item["change_note"])),
        height=420,
        disabled=True,
        label_visibility="collapsed",
    )


def _build_edit_hint(section_name: str, registry_tags: list[dict]) -> str:
    tag_names = [item["tag_name"] for item in registry_tags]

    if section_name == "주요치수" and any("SB-DIM-" in tag for tag in tag_names):
        return "기준 TAG의 주요치수 값을 반영해 수치 검토"
    if section_name == "기관" and any("SB-MAC-" in tag for tag in tag_names):
        return "주기관 관련 TAG 기준으로 기관부 기술내용 수정"
    if section_name == "화물시스템" and any("SB-CGO-" in tag for tag in tag_names):
        return "화물창/용적 TAG 기준으로 화물 시스템 내용 보완"
    return "기존 내용을 유지하되 기준 TAG와 차이 여부 점검"
