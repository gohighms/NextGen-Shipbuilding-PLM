import altair as alt
import pandas as pd
import streamlit as st

from src.common.paths import BLOCK_DIVISION_DIR, MBOM_DIR, MODEL_DRAFT_DIR, WBOM_DIR, WORK_INSTRUCTION_DIR
from src.features.bom_management.mbom_repository import MbomRepository
from src.features.bom_management.repository import BlockDivisionRepository
from src.features.bom_management.service import (
    build_bom_model_structure_rows,
    build_block_division_result,
    build_mbom_rows,
    build_mbom_summary_rows,
    build_model_structure_rows,
    build_wbom_rows,
    build_wbom_summary_rows,
    build_work_instruction_rows,
    build_work_instruction_summary_rows,
)
from src.features.bom_management.wbom_repository import WbomRepository
from src.features.bom_management.work_instruction_repository import WorkInstructionRepository
from src.features.model_generation.draft_repository import ModelDraftRepository


def render_block_division_page() -> None:
    st.title("블록 분할 정의")
    st.caption("선체 SFD 모델에서 logical block division이 확정되고, 그 결과를 바탕으로 SDD solid block 모델로 이어지는 흐름을 보여줍니다.")

    model_draft_repository = ModelDraftRepository(MODEL_DRAFT_DIR)
    block_division_repository = BlockDivisionRepository(BLOCK_DIVISION_DIR)
    model_drafts = model_draft_repository.list_all()

    if not model_drafts:
        st.info("먼저 `유사 프로젝트 기반 모델 편집설계`에서 현재 프로젝트 모델 구조를 저장해 주세요.")
        return

    selected_draft_id = st.selectbox(
        "기준 모델 초안 선택",
        options=[item["draft_id"] for item in model_drafts],
        format_func=lambda draft_id: next(
            f"{item['title']} ({item['draft_id']})"
            for item in model_drafts
            if item["draft_id"] == draft_id
        ),
    )
    selected_draft = next(item for item in model_drafts if item["draft_id"] == selected_draft_id)
    result = build_block_division_result(selected_draft)

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{selected_draft['current_project_name']}`")
        st.write(f"- 기준 프로젝트: `{selected_draft['source_project_name']}`")
        st.write(f"- 기준 모델: `{selected_draft['based_on_model_id']}`")
    with top_col2:
        st.write(f"- 모델 초안 ID: `{selected_draft['draft_id']}`")
        st.write("- 적용 범위: `선체 모델 중심`")
        # st.write("- 설명: `의장 모델은 다음 MBOM 단계에서 블록별로 정리된 것으로 가정`")

    st.divider()
    st.subheader("1. 선체 SFD 모델 구조")
    hull_rows = [
        row
        for row in build_model_structure_rows(selected_draft.get("model_hierarchy", []))
        if row["설계구조"] == "선체"
    ]
    st.dataframe(pd.DataFrame(hull_rows), use_container_width=True, hide_index=True, height=620)

    st.divider()
    st.subheader("2. 확정된 Logical Block Division")
    st.dataframe(pd.DataFrame(result["logical_rows"]), use_container_width=True, hide_index=True, height=460)
    # st.caption("여기서는 사용자가 선택하는 제안 단계가 아니라, 어느 시점에 확정된 logical block division 결과를 기준으로 이어갑니다.")

    st.divider()
    st.subheader("3. SDD Solid Block Model 연결")
    result_col1, result_col2 = st.columns([0.33, 0.67])
    with result_col1:
        st.write(f"- 현재 프로젝트: `{result['project_name']}`")
        st.write(f"- 기준 모델 초안: `{result['source_model_draft_id']}`")
        st.write(f"- 기준 모델: `{result['source_model_id']}`")
        st.write(f"- 반영 항목 수: `{len(result['logical_rows'])}`")
        if st.button("Block Division 초안 저장", type="primary", use_container_width=True):
            saved_path = block_division_repository.save(result)
            st.success(f"Block Division 초안을 저장했습니다. `{saved_path.name}`")
    with result_col2:
        st.markdown("#### 논리 블록 요약")
        st.dataframe(pd.DataFrame(result["summary_rows"]), use_container_width=True, hide_index=True)

    st.markdown("#### SDD Solid Block Model 연결")
    st.dataframe(pd.DataFrame(result["sdd_rows"]), use_container_width=True, hide_index=True, height=420)

    st.divider()
    _render_saved_block_divisions(block_division_repository, selected_draft["current_project_name"])


def render_mbom_page() -> None:
    st.title("생산 BOM 구축")
    st.caption("Block Division 이후, 선체와 의장 모델이 블록 기준으로 정리되었다고 가정하고, MBOM view를 구성합니다.")

    block_division_repository = BlockDivisionRepository(BLOCK_DIVISION_DIR)
    model_draft_repository = ModelDraftRepository(MODEL_DRAFT_DIR)
    mbom_repository = MbomRepository(MBOM_DIR)
    block_items = block_division_repository.list_all()

    if not block_items:
        st.info("먼저 `Block Division`에서 논리 블록 초안을 저장해 주세요.")
        return

    selected_division_id = st.selectbox(
        "기준 Block Division 선택",
        options=[item["division_id"] for item in block_items],
        format_func=lambda division_id: next(
            f"{item['title']} ({item['division_id']})"
            for item in block_items
            if item["division_id"] == division_id
        ),
    )
    selected_item = next(item for item in block_items if item["division_id"] == selected_division_id)
    source_model_draft = next(
        item for item in model_draft_repository.list_all() if item["draft_id"] == selected_item["source_model_draft_id"]
    )

    full_model_rows = build_bom_model_structure_rows(source_model_draft.get("model_hierarchy", []))
    mbom_rows = build_mbom_rows(selected_item, full_model_rows)
    summary_rows = build_mbom_summary_rows(mbom_rows)

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{selected_item['project_name']}`")
        st.write(f"- 기준 Block Division: `{selected_item['division_id']}`")
    with top_col2:
        st.write(f"- 연결 모델 초안: `{selected_item['source_model_draft_id']}`")
        # st.write("- 가정: `선체 + 의장 전체 모델이 블록별로 정리 완료`")

    st.divider()
    st.subheader("1. 전체 모델 구조")
    model_structure_df = (
        pd.DataFrame(full_model_rows)
        .rename(
            columns={
                "노드코드": "모델ID",
                "노드명": "모델명",
            }
        )
        .loc[:, ["구조레벨", "모델ID", "모델명", "설계구조", "모델타입", "생성조직", "개정"]]
    )
    st.dataframe(model_structure_df, use_container_width=True, hide_index=True, height=520)

    st.divider()
    st.subheader("2. MBOM view")
    st.write(f"- MBOM 품목 수: `{len(mbom_rows)}`")
    st.write(f"- 블록 수: `{len({row['블록'] for row in mbom_rows})}`")
    st.write("- 표시 범위: `소조 / 중조 / 대조 / PE`")
    if st.button("MBOM 초안 저장", type="primary", use_container_width=True):
        payload = {
            "project_name": selected_item["project_name"],
            "source_division_id": selected_item["division_id"],
            "title": f"{selected_item['project_name']} MBOM 초안",
            "summary_rows": summary_rows,
            "mbom_rows": mbom_rows,
        }
        saved_path = mbom_repository.save(payload)
        st.success(f"MBOM 초안을 저장했습니다. `{saved_path.name}`")

    st.markdown("#### MBOM 클러스터 View")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    all_blocks = ["전체"] + sorted({row["블록"] for row in mbom_rows})
    all_stages = ["전체"] + ["소조", "중조", "대조", "PE"]
    all_structures = ["전체"] + sorted({row["설계구조"] for row in mbom_rows})
    with filter_col1:
        selected_block = st.selectbox("Block 필터", options=all_blocks)
    with filter_col2:
        selected_stage = st.selectbox("조립단계 필터", options=all_stages)
    with filter_col3:
        selected_structure = st.selectbox("설계구조 필터", options=all_structures)

    filtered_mbom_rows = _filter_mbom_rows(
        mbom_rows,
        selected_block=selected_block,
        selected_stage=selected_stage,
        selected_structure=selected_structure,
    )
    st.caption("모델 구조를 Block, 조립단계, 설계구조 기준으로 다시 묶어 보는 MBOM 그리드 view입니다.")

    cluster_view_df = (
        pd.DataFrame(filtered_mbom_rows)
        .rename(
            columns={
                "MBOM 단계": "조립단계",
                "원천 모델": "모델ID",
                "품목명": "모델명",
                "품목군": "모델타입",
            }
        )
        .loc[:, ["블록", "조립단계", "설계구조", "모델ID", "모델명", "모델타입"]]
        .sort_values(by=["블록", "조립단계", "설계구조", "모델ID"], kind="stable")
    )
    block_palette = [
        "#fff7ed",
        "#fefce8",
        "#f0fdf4",
        "#ecfeff",
        "#eff6ff",
        "#f5f3ff",
        "#fdf2f8",
        "#f8fafc",
        "#fef2f2",
        "#f0f9ff",
    ]
    block_colors = {
        block_name: block_palette[index % len(block_palette)]
        for index, block_name in enumerate(cluster_view_df["블록"].drop_duplicates().tolist())
    }

    def _highlight_block_rows(row: pd.Series) -> list[str]:
        background = block_colors.get(row["블록"], "#ffffff")
        return [f"background-color: {background}; color: #111827;" for _ in row]

    st.table(cluster_view_df.style.apply(_highlight_block_rows, axis=1))

    st.divider()
    _render_saved_mbom(mbom_repository, selected_item["project_name"])


def render_wbom_page() -> None:
    st.title("작업 패키지 BOM")
    st.caption("MBOM을 작업 관점으로 다시 구성하고, 실제 작업에 필요한 발판·지그·임시 지지대 같은 보조 항목까지 포함한 WBOM view를 보여줍니다.")

    mbom_repository = MbomRepository(MBOM_DIR)
    wbom_repository = WbomRepository(WBOM_DIR)
    mbom_items = mbom_repository.list_all()

    if not mbom_items:
        st.info("먼저 `MBOM 생성`에서 MBOM 초안을 저장해 주세요.")
        return

    selected_mbom_id = st.selectbox(
        "기준 MBOM 선택",
        options=[item["mbom_id"] for item in mbom_items],
        format_func=lambda mbom_id: next(
            f"{item['title']} ({item['mbom_id']})"
            for item in mbom_items
            if item["mbom_id"] == mbom_id
        ),
    )
    selected_item = next(item for item in mbom_items if item["mbom_id"] == selected_mbom_id)

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{selected_item['project_name']}`")
        st.write(f"- 기준 MBOM: `{selected_item['mbom_id']}`")
    with top_col2:
        st.write(f"- 기준 Block Division: `{selected_item['source_division_id']}`")
        st.write("- 설명: `본체 품목 + 작업 지원 항목을 함께 구성`")

    st.divider()
    st.subheader("1. MBOM과의 연결")
    mbom_link_df = (
        pd.DataFrame(selected_item["mbom_rows"])
        .rename(
            columns={
                "MBOM 단계": "조립단계",
                "원천 모델": "모델ID",
                "품목명": "모델명",
                "품목군": "모델타입",
            }
        )
        .loc[:, ["블록", "조립단계", "설계구조", "모델ID", "모델명", "모델타입"]]
        .sort_values(by=["블록", "조립단계", "설계구조", "모델ID"], kind="stable")
    )
    st.caption("WBOM은 MBOM을 기준으로 작업 지원 항목이 추가된 view입니다.")
    st.table(mbom_link_df)

    st.divider()
    st.subheader("2. WBOM 구성 View")
    wbom_rows = build_wbom_rows(selected_item)
    summary_rows = build_wbom_summary_rows(wbom_rows)

    st.write(f"- WBOM 항목 수: `{len(wbom_rows)}`")
    st.write(f"- 작업 패키지 수: `{len({row['작업 패키지'] for row in wbom_rows})}`")
    st.write("- 포함 항목: `본체 작업 + 작업 지원`")
    if st.button("WBOM 초안 저장", type="primary", use_container_width=True):
        payload = {
            "project_name": selected_item["project_name"],
            "source_mbom_id": selected_item["mbom_id"],
            "title": f"{selected_item['project_name']} WBOM 초안",
            "summary_rows": summary_rows,
            "wbom_rows": wbom_rows,
        }
        saved_path = wbom_repository.save(payload)
        st.success(f"WBOM 초안을 저장했습니다. `{saved_path.name}`")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    all_blocks = ["전체"] + sorted({row["블록"] for row in wbom_rows})
    all_stages = ["전체"] + sorted({row["조립단계"] for row in wbom_rows})
    all_structures = ["전체"] + sorted({row["설계구조"] for row in wbom_rows})
    all_divisions = ["전체"] + sorted({row["WBOM 구분"] for row in wbom_rows})
    with filter_col1:
        selected_block = st.selectbox("Block 필터", options=all_blocks, key="wbom_block")
    with filter_col2:
        selected_stage = st.selectbox("조립단계 필터", options=all_stages, key="wbom_stage")
    with filter_col3:
        selected_structure = st.selectbox("설계구조 필터", options=all_structures, key="wbom_structure")
    with filter_col4:
        selected_division = st.selectbox("WBOM 구분 필터", options=all_divisions, key="wbom_division")

    filtered_wbom_rows = []
    for row in wbom_rows:
        if selected_block != "전체" and row["블록"] != selected_block:
            continue
        if selected_stage != "전체" and row["조립단계"] != selected_stage:
            continue
        if selected_structure != "전체" and row["설계구조"] != selected_structure:
            continue
        if selected_division != "전체" and row["WBOM 구분"] != selected_division:
            continue
        filtered_wbom_rows.append(row)

    wbom_view_df = (
        pd.DataFrame(filtered_wbom_rows)
        .loc[:, ["블록", "조립단계", "설계구조", "WBOM 구분", "모델ID", "품목명", "모델타입", "작업 목적"]]
        .rename(columns={"품목명": "모델명"})
        .sort_values(by=["블록", "조립단계", "설계구조", "WBOM 구분", "모델ID"], kind="stable")
    )
    st.caption("MBOM 클러스터 View를 기준으로 WBOM 구성 요소와 작업 지원 항목을 함께 보는 화면입니다.")
    st.dataframe(wbom_view_df, use_container_width=True, hide_index=True, height=520)

    st.divider()
    _render_saved_wbom(wbom_repository, selected_item["project_name"])


def render_work_instruction_page() -> None:
    st.title("작업지시서")
    st.caption("WBOM을 바탕으로 작업 패키지별 간단한 작업지시서를 생성합니다. 이 화면으로 목적별 BOM 관리 영역을 마무리합니다.")

    wbom_repository = WbomRepository(WBOM_DIR)
    instruction_repository = WorkInstructionRepository(WORK_INSTRUCTION_DIR)
    wbom_items = wbom_repository.list_all()

    if not wbom_items:
        st.info("먼저 `WBOM 생성`에서 WBOM 초안을 저장해 주세요.")
        return

    selected_wbom_id = st.selectbox(
        "기준 WBOM 선택",
        options=[item["wbom_id"] for item in wbom_items],
        format_func=lambda wbom_id: next(
            f"{item['title']} ({item['wbom_id']})"
            for item in wbom_items
            if item["wbom_id"] == wbom_id
        ),
    )
    selected_item = next(item for item in wbom_items if item["wbom_id"] == selected_wbom_id)

    instruction_rows = build_work_instruction_rows(selected_item)
    summary_rows = build_work_instruction_summary_rows(instruction_rows)

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{selected_item['project_name']}`")
        st.write(f"- 기준 WBOM: `{selected_item['wbom_id']}`")
    with top_col2:
        st.write(f"- 작업지시 대상 패키지 수: `{len(instruction_rows)}`")
        st.write("- 설명: `작업 패키지별 기본 지시 정보 생성`")

    st.divider()
    st.subheader("1. WBOM과의 연결")
    wbom_link_df = (
        pd.DataFrame(selected_item["wbom_rows"])
        .loc[:, ["블록", "조립단계", "설계구조", "WBOM 구분", "모델ID", "품목명", "모델타입", "작업 목적"]]
        .rename(columns={"품목명": "모델명"})
        .sort_values(by=["블록", "조립단계", "설계구조", "WBOM 구분", "모델ID"], kind="stable")
    )
    st.caption("작업지시서는 WBOM 작업 패키지를 기준으로 생성되는 실행 view입니다.")
    st.table(wbom_link_df)

    st.divider()
    st.subheader("2. 작업지시서 View")
    st.write(f"- 작업지시 수: `{len(instruction_rows)}`")
    st.write(f"- 작업 패키지 수: `{len({row['작업 패키지'] for row in instruction_rows})}`")
    if st.button("작업지시서 저장", type="primary", use_container_width=True):
        payload = {
            "project_name": selected_item["project_name"],
            "source_wbom_id": selected_item["wbom_id"],
            "title": f"{selected_item['project_name']} 작업지시서 초안",
            "summary_rows": summary_rows,
            "instruction_rows": instruction_rows,
        }
        saved_path = instruction_repository.save(payload)
        st.success(f"작업지시서 초안을 저장했습니다. `{saved_path.name}`")

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    all_blocks = ["전체"] + sorted({row["블록"] for row in instruction_rows})
    all_stages = ["전체"] + sorted({row["조립단계"] for row in instruction_rows})
    all_teams = ["전체"] + sorted({row["담당 조직"] for row in instruction_rows})
    with filter_col1:
        selected_block = st.selectbox("Block 필터", options=all_blocks, key="wi_block")
    with filter_col2:
        selected_stage = st.selectbox("조립단계 필터", options=all_stages, key="wi_stage")
    with filter_col3:
        selected_team = st.selectbox("담당조직 필터", options=all_teams, key="wi_team")

    filtered_instruction_rows = []
    for row in instruction_rows:
        if selected_block != "전체" and row["블록"] != selected_block:
            continue
        if selected_stage != "전체" and row["조립단계"] != selected_stage:
            continue
        if selected_team != "전체" and row["담당 조직"] != selected_team:
            continue
        filtered_instruction_rows.append(row)

    instruction_view_df = (
        pd.DataFrame(filtered_instruction_rows)
        .loc[:, ["블록", "조립단계", "작업 패키지", "주 작업", "준비 항목", "담당 조직"]]
        .sort_values(by=["블록", "조립단계", "작업 패키지"], kind="stable")
    )
    st.dataframe(instruction_view_df, use_container_width=True, hide_index=True, height=520)

    st.divider()
    _render_saved_work_instructions(instruction_repository, selected_item["project_name"])


def _render_saved_block_divisions(repository: BlockDivisionRepository, project_name: str) -> None:
    st.subheader("저장된 Block Division 이력")
    items = [item for item in repository.list_all() if item.get("project_name") == project_name]
    if not items:
        st.info("현재 프로젝트 기준으로 저장된 Block Division 이력이 없습니다.")
        return

    summary_rows = [
        {
            "초안 ID": item["division_id"],
            "제목": item["title"],
            "기준 모델 초안": item["source_model_draft_id"],
            "저장 시각": item["saved_at"],
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    selected_id = st.selectbox(
        "저장된 Block Division 선택",
        options=[item["division_id"] for item in items],
        format_func=lambda division_id: next(
            f"{item['title']} ({item['division_id']})"
            for item in items
            if item["division_id"] == division_id
        ),
    )
    selected_item = next(item for item in items if item["division_id"] == selected_id)
    st.markdown("#### Surface Model → Solid Model → Block")
    st.caption("노드 위에 마우스를 올리면 상세 정보를 볼 수 있습니다.")
    st.altair_chart(_build_block_division_graph(selected_item), use_container_width=True)


def _render_saved_mbom(repository: MbomRepository, project_name: str) -> None:
    st.subheader("저장된 MBOM 이력")
    items = [item for item in repository.list_all() if item.get("project_name") == project_name]
    if not items:
        st.info("현재 프로젝트 기준으로 저장된 MBOM 이력이 없습니다.")
        return

    summary_rows = [
        {
            "MBOM ID": item["mbom_id"],
            "제목": item["title"],
            "기준 Block Division": item["source_division_id"],
            "저장 시각": item["saved_at"],
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_id = st.selectbox(
        "확인할 MBOM 이력 선택",
        options=[item["mbom_id"] for item in items],
        format_func=lambda mbom_id: next(
            f"{item['title']} ({item['mbom_id']})"
            for item in items
            if item["mbom_id"] == mbom_id
        ),
    )
    selected_item = next(item for item in items if item["mbom_id"] == selected_id)

    st.markdown("#### 저장된 MBOM 단계별 요약")
    st.dataframe(pd.DataFrame(selected_item["summary_rows"]), use_container_width=True, hide_index=True)
    st.markdown("#### 저장된 MBOM 상세 View")
    st.dataframe(pd.DataFrame(selected_item["mbom_rows"]), use_container_width=True, hide_index=True, height=520)


def _render_saved_wbom(repository: WbomRepository, project_name: str) -> None:
    st.subheader("저장된 WBOM 이력")
    items = [item for item in repository.list_all() if item.get("project_name") == project_name]
    if not items:
        st.info("현재 프로젝트 기준으로 저장된 WBOM 이력이 없습니다.")
        return

    summary_rows = [
        {
            "WBOM ID": item["wbom_id"],
            "제목": item["title"],
            "기준 MBOM": item["source_mbom_id"],
            "저장 시각": item["saved_at"],
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_id = st.selectbox(
        "확인할 WBOM 이력 선택",
        options=[item["wbom_id"] for item in items],
        format_func=lambda wbom_id: next(
            f"{item['title']} ({item['wbom_id']})"
            for item in items
            if item["wbom_id"] == wbom_id
        ),
    )
    selected_item = next(item for item in items if item["wbom_id"] == selected_id)

    st.markdown("#### 저장된 WBOM 작업 패키지 요약")
    st.dataframe(pd.DataFrame(selected_item["summary_rows"]), use_container_width=True, hide_index=True)
    st.markdown("#### 저장된 WBOM 상세 View")
    st.dataframe(pd.DataFrame(selected_item["wbom_rows"]), use_container_width=True, hide_index=True, height=520)


def _render_saved_work_instructions(repository: WorkInstructionRepository, project_name: str) -> None:
    st.subheader("저장된 작업지시서 이력")
    items = [item for item in repository.list_all() if item.get("project_name") == project_name]
    if not items:
        st.info("현재 프로젝트 기준으로 저장된 작업지시서 이력이 없습니다.")
        return

    summary_rows = [
        {
            "지시서 ID": item["instruction_id"],
            "제목": item["title"],
            "기준 WBOM": item["source_wbom_id"],
            "저장 시각": item["saved_at"],
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    selected_id = st.selectbox(
        "확인할 작업지시서 이력 선택",
        options=[item["instruction_id"] for item in items],
        format_func=lambda instruction_id: next(
            f"{item['title']} ({item['instruction_id']})"
            for item in items
            if item["instruction_id"] == instruction_id
        ),
    )
    selected_item = next(item for item in items if item["instruction_id"] == selected_id)

    st.markdown("#### 저장된 작업지시서 요약")
    st.dataframe(pd.DataFrame(selected_item["summary_rows"]), use_container_width=True, hide_index=True)
    st.markdown("#### 저장된 작업지시서 상세")
    st.dataframe(pd.DataFrame(selected_item["instruction_rows"]), use_container_width=True, hide_index=True, height=520)


def _build_block_division_graph(block_item: dict) -> alt.Chart:
    logical_rows = block_item.get("logical_rows", [])
    sdd_rows = block_item.get("sdd_rows", [])
    sdd_map = {row.get("기준 항목", ""): row for row in sdd_rows}

    graph_rows = []
    block_y_map: dict[str, list[float]] = {}
    block_counts: dict[str, int] = {}

    for logical_row in logical_rows:
        block_code = logical_row.get("논리 블록", "-")
        node_id = logical_row.get("노드코드", "-")
        node_name = logical_row.get("노드명", "-")
        surface_type = logical_row.get("SFD 타입", "-")
        model_path = logical_row.get("모델경로", "-")
        solid_row = sdd_map.get(node_name, {})
        solid_id = solid_row.get("분리된 모델명", f"{block_code}-{node_id}")

        row_index = block_counts.get(block_code, 0)
        block_counts[block_code] = row_index + 1
        y_pos = -1.8 * row_index - (len(block_y_map) * 0.55)
        block_y_map.setdefault(block_code, []).append(y_pos)

        graph_rows.append(
            {
                "surface_id": node_id,
                "surface_name": node_name,
                "surface_type": surface_type,
                "surface_path": model_path,
                "solid_id": solid_id,
                "block_code": block_code,
                "reason_text": logical_row.get("분류 근거", "-"),
                "y_pos": y_pos,
            }
        )

    if not graph_rows:
        return alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_point()

    block_positions = {
        block_code: sum(values) / len(values)
        for block_code, values in block_y_map.items()
    }

    edge_rows = []
    for row in graph_rows:
        edge_rows.append(
            {"x": 0.0, "y": row["y_pos"], "x2": 1.0, "y2": row["y_pos"], "edge_type": "surface_to_solid"}
        )
        edge_rows.append(
            {
                "x": 1.0,
                "y": row["y_pos"],
                "x2": 2.0,
                "y2": block_positions[row["block_code"]],
                "edge_type": "solid_to_block",
            }
        )

    surface_nodes = pd.DataFrame(
        [
            {
                "x": 0.0,
                "y": row["y_pos"],
                "label": row["surface_id"],
                "group": "Surface Model",
                "detail_id": row["surface_id"],
                "detail_name": row["surface_name"],
                "detail_type": row["surface_type"],
                "detail_extra": row["surface_path"],
            }
            for row in graph_rows
        ]
    )
    solid_nodes = pd.DataFrame(
        [
            {
                "x": 1.0,
                "y": row["y_pos"],
                "label": row["solid_id"],
                "group": "Solid Model",
                "detail_id": row["solid_id"],
                "detail_name": row["surface_name"],
                "detail_type": "Solid Model",
                "detail_extra": row["reason_text"],
            }
            for row in graph_rows
        ]
    )
    block_nodes = pd.DataFrame(
        [
            {
                "x": 2.0,
                "y": y_pos,
                "label": block_code,
                "group": "Block",
                "detail_id": block_code,
                "detail_name": block_code,
                "detail_type": "Block",
                "detail_extra": f"포함 모델 수 {len([row for row in graph_rows if row['block_code'] == block_code])}",
            }
            for block_code, y_pos in block_positions.items()
        ]
    )
    node_df = pd.concat([surface_nodes, solid_nodes, block_nodes], ignore_index=True)
    edge_df = pd.DataFrame(edge_rows)

    edge_layer = (
        alt.Chart(edge_df)
        .mark_rule(color="#cbd5e1", strokeWidth=2)
        .encode(
            x=alt.X("x:Q", axis=alt.Axis(values=[0, 1, 2], labelAngle=0, title=None, labels=False, ticks=False)),
            y=alt.Y("y:Q", axis=None),
            x2="x2:Q",
            y2="y2:Q",
        )
    )

    node_layer = (
        alt.Chart(node_df)
        .mark_circle(size=900, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("x:Q", axis=alt.Axis(values=[0, 1, 2], labelAngle=0, title=None, labels=False, ticks=False)),
            y=alt.Y("y:Q", axis=None),
            color=alt.Color(
                "group:N",
                scale=alt.Scale(
                    domain=["Surface Model", "Solid Model", "Block"],
                    range=["#2563eb", "#f59e0b", "#10b981"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("group:N", title="구분"),
                alt.Tooltip("detail_id:N", title="ID"),
                alt.Tooltip("detail_name:N", title="이름"),
                alt.Tooltip("detail_type:N", title="타입"),
                alt.Tooltip("detail_extra:N", title="상세"),
            ],
        )
    )

    text_layer = (
        alt.Chart(node_df)
        .mark_text(color="gray", fontSize=10, fontWeight="bold")
        .encode(
            x="x:Q",
            y="y:Q",
            text="label:N",
        )
    )

    header_df = pd.DataFrame(
        [
            {"x": 0.0, "y": 1.5, "title": "SDD (Surface model)"},
            {"x": 1.0, "y": 1.5, "title": "SFD (Solid model)"},
            {"x": 2.0, "y": 1.1, "title": "Block"},
        ]
    )
    header_layer = (
        alt.Chart(header_df)
        .mark_text(fontSize=12, fontWeight="bold", color="#334155")
        .encode(x="x:Q", y="y:Q", text="title:N")
    )

    return (edge_layer + node_layer + text_layer + header_layer).properties(height=max(420, 160 + len(graph_rows) * 44))


def _filter_mbom_rows(
    mbom_rows: list[dict],
    selected_block: str,
    selected_stage: str,
    selected_structure: str,
) -> list[dict]:
    filtered_rows = []
    for row in mbom_rows:
        if selected_block != "전체" and row["블록"] != selected_block:
            continue
        if selected_stage != "전체" and row["MBOM 단계"] != selected_stage:
            continue
        if selected_structure != "전체" and row["설계구조"] != selected_structure:
            continue
        filtered_rows.append(row)
    return filtered_rows


def _build_mbom_cluster_chart(mbom_rows: list[dict]) -> alt.Chart:
    if not mbom_rows:
        empty_df = pd.DataFrame([{"x": 1, "y": 1, "label": "데이터 없음"}])
        return alt.Chart(empty_df).mark_text(fontSize=14, color="#64748b").encode(x="x:Q", y="y:Q", text="label:N")

    graph_rows = []
    block_offsets: dict[tuple[str, str, str], int] = {}
    stage_order = {"소조": 0, "중조": 1, "대조": 2, "PE": 3}
    block_order = sorted({row["블록"] for row in mbom_rows})

    for row in mbom_rows:
        block_code = row["블록"]
        stage_name = row["MBOM 단계"]
        structure_name = row["설계구조"]
        model_id = row["원천 모델"]
        model_name = row["품목명"]
        item_code = row["품목코드"]

        key = (block_code, stage_name, structure_name)
        item_index = block_offsets.get(key, 0)
        block_offsets[key] = item_index + 1

        block_index = block_order.index(block_code)
        y_pos = -(block_index * 6.0 + stage_order.get(stage_name, 0) * 1.8 + item_index * 0.55)

        graph_rows.append(
            {
                "block": block_code,
                "stage": stage_name,
                "structure": structure_name,
                "model_id": model_id,
                "model_name": model_name,
                "item_code": item_code,
                "y": y_pos,
            }
        )

    block_positions: dict[str, list[float]] = {}
    stage_positions: dict[tuple[str, str], list[float]] = {}
    structure_positions: dict[tuple[str, str, str], list[float]] = {}
    for row in graph_rows:
        block_positions.setdefault(row["block"], []).append(row["y"])
        stage_positions.setdefault((row["block"], row["stage"]), []).append(row["y"])
        structure_positions.setdefault((row["block"], row["stage"], row["structure"]), []).append(row["y"])

    edge_rows = []
    for row in graph_rows:
        block_y = sum(block_positions[row["block"]]) / len(block_positions[row["block"]])
        stage_y = sum(stage_positions[(row["block"], row["stage"])]) / len(stage_positions[(row["block"], row["stage"])])
        structure_y = sum(
            structure_positions[(row["block"], row["stage"], row["structure"])]
        ) / len(structure_positions[(row["block"], row["stage"], row["structure"])])

        edge_rows.append({"x": 0.0, "y": block_y, "x2": 1.0, "y2": stage_y})
        edge_rows.append({"x": 1.0, "y": stage_y, "x2": 2.0, "y2": structure_y})
        edge_rows.append({"x": 2.0, "y": structure_y, "x2": 3.0, "y2": row["y"]})

    edge_df = pd.DataFrame(edge_rows).drop_duplicates()
    edge_layer = (
        alt.Chart(edge_df)
        .mark_rule(color="#cbd5e1", strokeWidth=1.5)
        .encode(
            x=alt.X("x:Q", axis=alt.Axis(values=[0, 1, 2, 3], labels=False, ticks=False, title=None)),
            y=alt.Y("y:Q", axis=None),
            x2="x2:Q",
            y2="y2:Q",
        )
    )

    block_df = pd.DataFrame(
        [
            {
                "x": 0.0,
                "y": sum(values) / len(values),
                "label": block_code,
                "group": "Block",
                "detail": f"{block_code} / 포함 모델 {len([row for row in graph_rows if row['block'] == block_code])}개",
            }
            for block_code, values in block_positions.items()
        ]
    )
    stage_df = pd.DataFrame(
        [
            {
                "x": 1.0,
                "y": sum(values) / len(values),
                "label": stage_name,
                "group": "조립단계",
                "detail": f"{block_code} / {stage_name}",
            }
            for (block_code, stage_name), values in stage_positions.items()
        ]
    )
    structure_df = pd.DataFrame(
        [
            {
                "x": 2.0,
                "y": sum(values) / len(values),
                "label": structure_name,
                "group": "설계구조",
                "detail": f"{block_code} / {stage_name} / {structure_name}",
            }
            for (block_code, stage_name, structure_name), values in structure_positions.items()
        ]
    )
    model_df = pd.DataFrame(
        [
            {
                "x": 3.0,
                "y": row["y"],
                "label": row["model_id"],
                "group": "모델",
                "detail": f"{row['model_id']} / {row['model_name']} / {row['item_code']}",
            }
            for row in graph_rows
        ]
    )
    node_df = pd.concat([block_df, stage_df, structure_df, model_df], ignore_index=True)

    node_layer = (
        alt.Chart(node_df)
        .mark_circle(size=850, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("x:Q", axis=alt.Axis(values=[0, 1, 2, 3], labels=False, ticks=False, title=None)),
            y=alt.Y("y:Q", axis=None),
            color=alt.Color(
                "group:N",
                scale=alt.Scale(
                    domain=["Block", "조립단계", "설계구조", "모델"],
                    range=["#2563eb", "#f59e0b", "#7c3aed", "#10b981"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("group:N", title="구분"),
                alt.Tooltip("label:N", title="ID"),
                alt.Tooltip("detail:N", title="상세"),
            ],
        )
    )

    text_layer = (
        alt.Chart(node_df)
        .mark_text(color="white", fontSize=10, fontWeight="bold")
        .encode(x="x:Q", y="y:Q", text="label:N")
    )

    header_df = pd.DataFrame(
        [
            {"x": 0.0, "y": 1.8, "title": "Block"},
            {"x": 1.0, "y": 1.8, "title": "조립단계"},
            {"x": 2.0, "y": 1.8, "title": "설계구조"},
            {"x": 3.0, "y": 1.8, "title": "모델"},
        ]
    )
    header_layer = (
        alt.Chart(header_df)
        .mark_text(fontSize=12, fontWeight="bold", color="#334155")
        .encode(x="x:Q", y="y:Q", text="title:N")
    )

    return (edge_layer + node_layer + text_layer + header_layer).properties(height=max(420, 180 + len(graph_rows) * 22))
