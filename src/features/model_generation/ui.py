import pandas as pd
import streamlit as st

from src.common.paths import MODEL_DATA_DIR, MODEL_DRAFT_DIR, POS_DRAFT_DIR
from src.features.model_generation.draft_repository import ModelDraftRepository
from src.features.model_generation.repository import ModelRepository
from src.features.model_generation.service import (
    build_model_document_text,
    build_model_draft,
    recommend_models,
)
from src.features.pos_generation.draft_repository import PosDraftRepository


def render_model_generation_page() -> None:
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

    st.title("모델(EBOM) 생성")
    st.caption("저장된 POS 초안을 기준으로 기존 실적선 모델을 재활용하고, 편집설계용 모델(EBOM) 초안을 생성합니다.")

    pos_draft_repository = PosDraftRepository(POS_DRAFT_DIR)
    model_repository = ModelRepository(MODEL_DATA_DIR)
    model_draft_repository = ModelDraftRepository(MODEL_DRAFT_DIR)

    pos_draft_items = pos_draft_repository.list_all()
    model_items = model_repository.list_all()

    if not pos_draft_items:
        st.info("먼저 POS 생성 메뉴에서 POS 초안을 저장해 주세요. 저장된 POS 초안이 있어야 모델 추천이 가능합니다.")
        return

    if not model_items:
        st.info("비교할 기존 실적선 모델 샘플이 없습니다.")
        return

    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        selected_pos_draft_id = st.selectbox(
            "기준 POS 초안 선택",
            options=[item["draft_id"] for item in pos_draft_items],
            format_func=lambda draft_id: next(
                f"{item['title']} ({item['draft_id']})"
                for item in pos_draft_items
                if item["draft_id"] == draft_id
            ),
        )
        selected_pos_draft = next(item for item in pos_draft_items if item["draft_id"] == selected_pos_draft_id)
        st.write(f"- 기준 POS 초안: `{selected_pos_draft['title']}`")
        st.write(f"- 원본 POS: `{selected_pos_draft['based_on_pos_id']}`")
        st.write(f"- TAG 수: `{len(selected_pos_draft.get('tags', []))}`")

    with top_col2:
        st.subheader(
            "모델 생성 흐름",
            help="POS 초안과 연결된 TAG를 기준으로 기존 실적선 모델을 추천하고, 가장 가까운 모델을 편집설계 초안으로 재활용합니다.",
        )
        st.write("1. 기준 POS 초안 선택")
        st.write("2. 기존 실적선 모델 추천")
        st.write("3. 재활용할 모델 선택")
        st.write("4. 모델(EBOM) 초안 저장")

    st.divider()
    st.subheader(
        "추천 모델 후보",
        help="POS 초안의 TAG와 많이 겹치는 기존 실적선 모델을 우선적으로 보여줍니다.",
    )

    recommended_items = recommend_models(selected_pos_draft, model_items, top_k=3)
    recommendation_rows = []
    for item in recommended_items:
        recommendation_rows.append(
            {
                "모델 ID": item["model_id"],
                "모델명": item["title"],
                "분야": item["discipline"],
                "일치 TAG 수": item["score"],
                "공통 TAG": ", ".join(item["matched_tags"]) if item["matched_tags"] else "-",
            }
        )
    st.dataframe(pd.DataFrame(recommendation_rows), use_container_width=True, hide_index=True)

    selected_model_id = st.selectbox(
        "재활용할 모델 선택",
        options=[item["model_id"] for item in recommended_items],
        format_func=lambda model_id: next(
            f"{item['title']} ({item['model_id']})"
            for item in recommended_items
            if item["model_id"] == model_id
        ),
    )
    selected_model = next(item for item in recommended_items if item["model_id"] == selected_model_id)["document"]
    draft = build_model_draft(selected_pos_draft, selected_model)

    st.divider()
    preview_col1, preview_col2 = st.columns([1, 1])
    with preview_col1:
        st.markdown("#### 선택한 기존 모델 미리보기")
        st.write(f"- 모델 ID: `{selected_model['model_id']}`")
        st.write(f"- 모델명: `{selected_model['title']}`")
        st.write(f"- 분야: `{selected_model['discipline']}`")
        st.write(f"- EBOM 항목 수: `{len(selected_model.get('ebom_items', []))}`")
        st.dataframe(pd.DataFrame(selected_model["ebom_items"]), use_container_width=True, hide_index=True)

    with preview_col2:
        st.markdown("#### 모델(EBOM) 초안 작성")
        edited_title = st.text_input("초안 모델명", value=draft["title"])
        edited_discipline = st.text_input("설계 분야", value=draft["discipline"])
        change_note = st.text_area(
            "편집설계 메모",
            height=180,
            value="POS 변경사항을 반영해 주기관 및 화물 관련 EBOM 항목을 우선 수정 예정.",
        )

        st.write(f"- 새 모델 초안 ID: `{draft['new_model_id']}`")
        st.write(f"- 기준 POS 초안: `{draft['source_pos_draft_id']}`")
        st.write(f"- 재활용 원본 모델: `{draft['based_on_model_id']}`")

        ebom_rows = []
        for item in draft["ebom_items"]:
            ebom_rows.append(
                {
                    "품목코드": item["item_code"],
                    "설명": item["description"],
                    "수량": item["quantity"],
                    "편집 방향": _build_ebom_edit_hint(item["description"], selected_pos_draft.get("tags", [])),
                }
            )
        st.dataframe(pd.DataFrame(ebom_rows), use_container_width=True, hide_index=True)

        st.info("이 화면은 기존 실적선 모델을 완전히 새로 만드는 것이 아니라, POS 초안을 기준으로 가까운 모델을 재활용해 편집설계하는 흐름입니다.")

        final_draft = {
            **draft,
            "title": edited_title,
            "discipline": edited_discipline,
            "document_text": build_model_document_text(
                {
                    **draft,
                    "title": edited_title,
                    "discipline": edited_discipline,
                },
                change_note=change_note,
            ),
        }

        if st.button("모델(EBOM) 초안 저장", type="primary", use_container_width=True):
            saved_path = model_draft_repository.save(final_draft, change_note=change_note)
            st.success(f"모델(EBOM) 초안을 저장했습니다: `{saved_path.name}`")

    st.divider()
    st.subheader(
        "모델(EBOM) 원문 보기",
        help="구조화된 EBOM 목록과 함께 실제 편집설계 문서처럼 읽을 수 있는 원문 형태를 제공합니다.",
    )
    text_col1, text_col2 = st.columns([1, 1])
    with text_col1:
        st.markdown("#### 기존 모델 원문")
        st.text_area(
            "기존 모델 원문",
            value=build_model_document_text(selected_model),
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )
    with text_col2:
        st.markdown("#### 새 모델(EBOM) 초안 원문")
        draft_preview_text = build_model_document_text(
            {
                **draft,
                "title": edited_title,
                "discipline": edited_discipline,
            },
            change_note=change_note,
        )
        st.text_area(
            "새 모델(EBOM) 초안 원문",
            value=draft_preview_text,
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )

    st.divider()
    _render_saved_model_draft_section(model_draft_repository)


def _render_saved_model_draft_section(model_draft_repository: ModelDraftRepository) -> None:
    st.subheader(
        "저장된 모델(EBOM) 초안 및 이력",
        help="저장한 모델 초안을 다시 불러와 기준 POS 초안, 원본 모델, 편집 메모를 함께 확인할 수 있습니다.",
    )

    draft_items = model_draft_repository.list_all()
    if not draft_items:
        st.info("저장된 모델 초안이 없습니다. 위에서 모델(EBOM) 초안을 저장해 주세요.")
        return

    summary_rows = []
    for item in draft_items:
        summary_rows.append(
            {
                "초안 ID": item["draft_id"],
                "모델명": item["title"],
                "기준 POS": item["source_pos_draft_id"],
                "원본 모델": item["based_on_model_id"],
                "저장 시각": item["saved_at"],
            }
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_draft_id = st.selectbox(
        "확인할 모델 초안 선택",
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
        st.write(f"- 모델명: `{selected_item['title']}`")
        st.write(f"- 기준 POS 초안: `{selected_item['source_pos_draft_id']}`")
        st.write(f"- 원본 모델: `{selected_item['based_on_model_id']}`")
        st.write(f"- 분야: `{selected_item['discipline']}`")
        st.write(f"- 저장 시각: `{selected_item['saved_at']}`")
    with detail_col2:
        st.markdown("#### 편집설계 메모")
        st.write(selected_item["change_note"])

    st.markdown("#### 저장된 EBOM 항목")
    st.dataframe(pd.DataFrame(selected_item["ebom_items"]), use_container_width=True, hide_index=True)

    st.markdown("#### 저장된 모델(EBOM) 초안 원문")
    st.text_area(
        "저장된 모델(EBOM) 초안 원문",
        value=selected_item.get("document_text", build_model_document_text(selected_item, selected_item["change_note"])),
        height=420,
        disabled=True,
        label_visibility="collapsed",
    )


def _build_ebom_edit_hint(description: str, pos_tags: list[dict]) -> str:
    tag_names = [item["tag_name"] for item in pos_tags]
    description_lower = description.lower()

    if "engine" in description_lower and any("SB-MAC-" in tag for tag in tag_names):
        return "주기관 관련 POS 변경사항을 반영해 구성 재검토"
    if any(keyword in description_lower for keyword in ["cargo", "tank", "pump"]) and any("SB-CGO-" in tag for tag in tag_names):
        return "화물 시스템 관련 POS 변경사항 기준으로 항목 조정"
    if any("SB-DIM-" in tag for tag in tag_names):
        return "주요치수 변경 영향 여부를 함께 점검"
    return "기존 실적선 모델 기준 유지 후 차이 여부 검토"
