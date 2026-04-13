import pandas as pd
import streamlit as st

from src.common.paths import MODEL_DATA_DIR, MODEL_DRAFT_DIR, POS_DRAFT_DIR
from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.model_generation.draft_repository import ModelDraftRepository
from src.features.model_generation.repository import ModelRepository
from src.features.model_generation.service import (
    build_hierarchy_rows,
    build_model_draft,
    build_model_reuse_suggestions,
    find_models_for_project,
    summarize_model_similarity,
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

    st.title("유사 프로젝트 기반 모델 편집설계")
    st.caption("컨셉 시나리오 기준으로 `기준 구조 보기 → 재활용 제안 → 선택 구조 가져오기` 흐름을 직관적으로 보여줍니다.")

    selected_project = get_selected_project()
    current_spec = get_current_spec()

    if not selected_project or not current_spec:
        st.info("먼저 `건조사양서 기반 유사 프로젝트 찾기`에서 기준 프로젝트를 선택해 주세요.")
        return

    model_repository = ModelRepository(MODEL_DATA_DIR)
    model_draft_repository = ModelDraftRepository(MODEL_DRAFT_DIR)
    pos_draft_repository = PosDraftRepository(POS_DRAFT_DIR)

    model_items = find_models_for_project(selected_project, model_repository.list_all())
    if not model_items:
        st.warning("선택한 기준 프로젝트와 연결된 모델 샘플이 아직 없습니다.")
        return

    related_pos_drafts = [
        item
        for item in pos_draft_repository.list_all()
        if item.get("current_project_name") == current_spec["project_name"]
    ]

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{current_spec['project_name']}`")
        st.write(f"- 기준 프로젝트: `{selected_project['project_name']}`")
        st.write(f"- 기준 사양서 ID: `{selected_project['spec_id']}`")
    with top_col2:
        st.write(f"- 연결된 기준 모델 수: `{len(model_items)}`")
        st.write(f"- 관련 POS 초안 수: `{len(related_pos_drafts)}`")
        st.write("- 활용 방식: `재활용 의사결정 지원 중심 시나리오`")

    selected_pos_draft = None
    if related_pos_drafts:
        st.divider()
        pos_options = ["선택 안 함"] + [item["draft_id"] for item in related_pos_drafts]
        selected_pos_option = st.selectbox(
            "모델 편집설계에 함께 참조할 POS 초안",
            options=pos_options,
            format_func=lambda draft_id: "선택 안 함"
            if draft_id == "선택 안 함"
            else next(
                f"{item['title']} ({item['draft_id']})"
                for item in related_pos_drafts
                if item["draft_id"] == draft_id
            ),
        )
        if selected_pos_option != "선택 안 함":
            selected_pos_draft = next(item for item in related_pos_drafts if item["draft_id"] == selected_pos_option)

    selected_model_id = st.selectbox(
        "기준 실적선 모델 선택",
        options=[item["model_id"] for item in model_items],
        format_func=lambda model_id: next(
            f"{item['title']} ({item['model_id']})"
            for item in model_items
            if item["model_id"] == model_id
        ),
    )
    selected_model = next(item for item in model_items if item["model_id"] == selected_model_id)
    similarity = summarize_model_similarity(current_spec.get("attributes", {}), selected_model)

    st.divider()
    st.subheader("1. 기준 실적선 모델 구조 분석")
    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.metric("기준 모델", selected_model["model_id"])
    info_col2.metric("속성 적합도", f"{similarity['score']:.3f}")
    info_col3.metric("일치 항목 수", similarity["matched_count"])

    base_rows = build_hierarchy_rows(selected_model.get("model_hierarchy", []))
    st.dataframe(pd.DataFrame(base_rows), use_container_width=True, hide_index=True, height=720)

    st.divider()
    st.subheader("2. 모델 재활용 제안")
    suggestions = build_model_reuse_suggestions(current_spec.get("attributes", {}), selected_model)

    suggestion_rows = [
        {
            "제안 구조": item["name"],
            "판정": item["review_status"],
            "적합도": item["score"],
            "재활용 근거": item["evidence"],
        }
        for item in suggestions
    ]
    st.dataframe(
        _style_rows(pd.DataFrame(suggestion_rows), "판정", {"재활용 추천", "조건부 검토"}),
        use_container_width=True,
        hide_index=True,
    )

    default_selected_paths = []
    for item in suggestions:
        if item["review_status"] == "재활용 추천":
            default_selected_paths.extend(item["root_paths"])

    highlighted_paths = set(default_selected_paths)
    st.markdown("#### 시스템 추천 구조가 표시된 기준 모델 구조")
    highlighted_rows = build_hierarchy_rows(selected_model.get("model_hierarchy", []), highlighted_paths)
    st.dataframe(
        _style_rows(pd.DataFrame(highlighted_rows), "재활용 제안", {"선택 구조"}),
        use_container_width=True,
        hide_index=True,
        height=520,
    )

    st.markdown("#### 가져올 구조 선택")
    selectable_rows = []
    for row in highlighted_rows:
        selectable_rows.append(
            {
                "가져오기": row["재활용 제안"] == "선택 구조",
                "노드코드": row["노드코드"],
                "노드명": row["노드명"],
                "설계구조": row["설계구조"],
                "모델경로": row["모델경로"],
                "생성조직": row["생성조직"],
                "재활용 제안": row["재활용 제안"],
            }
        )

    selection_df = pd.DataFrame(selectable_rows)
    edited_selection_df = st.data_editor(
        selection_df,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "가져오기": st.column_config.CheckboxColumn(
                "가져오기",
                help="체크한 구조만 현재 프로젝트 모델 편집설계 시작 구조로 가져옵니다.",
            ),
        },
        disabled=["노드코드", "노드명", "설계구조", "모델경로", "생성조직", "재활용 제안"],
    )

    selected_root_paths = edited_selection_df.loc[edited_selection_df["가져오기"], "모델경로"].tolist()

    st.divider()
    st.subheader("3. 현재 프로젝트 모델 편집설계 시작")
    if not selected_root_paths:
        st.info("가져올 구조를 하나 이상 선택하면 아래에 현재 프로젝트용 구조가 생성됩니다.")
        return

    draft = build_model_draft(
        current_spec,
        selected_project,
        selected_model,
        approved_paths=selected_root_paths,
        pos_draft_item=selected_pos_draft,
    )

    start_col1, start_col2 = st.columns([0.35, 0.65])
    with start_col1:
        edited_title = st.text_input("초안 모델명", value=draft["title"])
        edited_discipline = st.text_input("설계 분야", value=draft["discipline"])
        change_note = st.text_area(
            "Change Note",
            height=180,
            value=(
                f"{selected_project['project_name']} 기준 모델에서 선택 구조를 가져와 "
                f"{current_spec['project_name']} 모델 편집설계를 시작."
            ),
        )
        st.write(f"- 새 모델 ID: `{draft['new_model_id']}`")
        st.write(f"- 기준 프로젝트: `{draft['source_project_name']}`")
        st.write(f"- 재활용 기준 모델: `{draft['based_on_model_id']}`")
        st.write(f"- 가져온 체크 구조 수: `{len(selected_root_paths)}`")
        st.write(f"- 최종 반영 노드 수: `{draft['selected_structure_count']}`")

        final_draft = {
            **draft,
            "title": edited_title,
            "discipline": edited_discipline,
            "selected_structure_paths": selected_root_paths,
        }
        if st.button("제안 구조 가져오기", type="primary", use_container_width=True):
            saved_path = model_draft_repository.save(final_draft, change_note=change_note)
            st.success(f"모델 편집설계 시작 구조를 저장했습니다. `{saved_path.name}`")

    with start_col2:
        st.markdown("#### 현재 프로젝트 최종 구조")
        converted_paths = set(
            path.replace(
                f"PROJECT/{selected_project['project_name']}",
                f"PROJECT/{current_spec['project_name']}",
                1,
            )
            for path in selected_root_paths
        )
        current_rows = build_hierarchy_rows(draft.get("model_hierarchy", []), converted_paths)
        st.dataframe(
            _style_rows(pd.DataFrame(current_rows), "재활용 제안", {"선택 구조"}),
            use_container_width=True,
            hide_index=True,
            height=720,
        )

    st.divider()
    _render_saved_model_drafts(model_draft_repository, current_spec["project_name"])


def _style_rows(dataframe: pd.DataFrame, status_column: str, highlighted_statuses: set[str]):
    def highlight_row(row):
        if row[status_column] in highlighted_statuses:
            return ["background-color: #fff7cc; color: #111111"] * len(row)
        return [""] * len(row)

    return dataframe.style.apply(highlight_row, axis=1)


def _render_saved_model_drafts(model_draft_repository: ModelDraftRepository, current_project_name: str) -> None:
    st.subheader("이력 및 최종 구조")

    draft_items = [
        item
        for item in model_draft_repository.list_all()
        if item.get("current_project_name") == current_project_name
    ]
    if not draft_items:
        st.info("현재 프로젝트 기준으로 저장된 모델 구조 이력이 없습니다.")
        return

    summary_rows = [
        {
            "초안 ID": item["draft_id"],
            "모델명": item["title"],
            "기준 프로젝트": item.get("source_project_name", "-"),
            "재활용 모델": item["based_on_model_id"],
            "저장 시각": item["saved_at"],
        }
        for item in draft_items
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_draft_id = st.selectbox(
        "확인할 모델 이력 선택",
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
        st.write(f"- 기준 프로젝트: `{selected_item.get('source_project_name', '-')}`")
        st.write(f"- 재활용 모델: `{selected_item['based_on_model_id']}`")
        st.write(f"- 저장 시각: `{selected_item['saved_at']}`")
    with detail_col2:
        st.markdown("#### Change Note")
        st.write(selected_item["change_note"])

    highlighted_paths = set(selected_item.get("selected_structure_paths", []))
    st.markdown("#### 저장된 최종 구조")
    saved_rows = build_hierarchy_rows(selected_item.get("model_hierarchy", []), highlighted_paths)
    st.dataframe(
        _style_rows(pd.DataFrame(saved_rows), "재활용 제안", {"선택 구조"}),
        use_container_width=True,
        hide_index=True,
        height=720,
    )
