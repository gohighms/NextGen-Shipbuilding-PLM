import pandas as pd
import streamlit as st

from src.common.paths import BLOCK_DIVISION_DIR, MBOM_DIR, MODEL_DRAFT_DIR, WBOM_DIR, WORK_INSTRUCTION_DIR
from src.features.bom_management.mbom_repository import MbomRepository
from src.features.bom_management.repository import BlockDivisionRepository
from src.features.bom_management.service import (
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
    st.title("Block Division")
    st.caption("선체 SFD 모델에서 logical block division이 확정되고, 그 결과를 바탕으로 SDD solid block 모델로 이어지는 흐름을 단순하게 보여줍니다.")

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
        st.write("- 설명: `의장 모델은 다음 MBOM 단계에서 블록별로 정리된 것으로 가정`")

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
    st.caption("여기서는 사용자가 선택하는 제안 단계가 아니라, 어느 시점에 확정된 logical block division 결과를 기준으로 이어갑니다.")

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
    st.title("MBOM 생성")
    st.caption("Block Division 이후에는 선체와 의장 전체 모델이 블록 기준으로 정리되었다고 가정하고, 생산 목적의 MBOM view를 구성합니다.")

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

    full_model_rows = build_model_structure_rows(source_model_draft.get("model_hierarchy", []))
    mbom_rows = build_mbom_rows(selected_item, full_model_rows)
    summary_rows = build_mbom_summary_rows(mbom_rows)

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{selected_item['project_name']}`")
        st.write(f"- 기준 Block Division: `{selected_item['division_id']}`")
    with top_col2:
        st.write(f"- 연결 모델 초안: `{selected_item['source_model_draft_id']}`")
        st.write("- 가정: `선체 + 의장 전체 모델이 블록별로 정리 완료`")

    st.divider()
    st.subheader("1. 전체 모델 구조")
    st.dataframe(pd.DataFrame(full_model_rows), use_container_width=True, hide_index=True, height=520)

    st.divider()
    st.subheader("2. Block 기준 MBOM View")
    summary_col1, summary_col2 = st.columns([0.33, 0.67])
    with summary_col1:
        st.write(f"- MBOM 품목 수: `{len(mbom_rows)}`")
        st.write(f"- 블록 수: `{len(summary_rows)}`")
        st.write("- 표시 범위: `대조 / 중조 / 소조`")
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
    with summary_col2:
        st.markdown("#### MBOM 단계별 요약")
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    st.markdown("#### MBOM 상세 View")
    st.dataframe(pd.DataFrame(mbom_rows), use_container_width=True, hide_index=True, height=520)

    st.divider()
    _render_saved_mbom(mbom_repository, selected_item["project_name"])


def render_wbom_page() -> None:
    st.title("WBOM 생성")
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
    st.subheader("1. MBOM 기준 품목")
    st.dataframe(pd.DataFrame(selected_item["mbom_rows"]), use_container_width=True, hide_index=True, height=420)

    st.divider()
    st.subheader("2. WBOM 작업 View")
    wbom_rows = build_wbom_rows(selected_item)
    summary_rows = build_wbom_summary_rows(wbom_rows)

    summary_col1, summary_col2 = st.columns([0.33, 0.67])
    with summary_col1:
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
    with summary_col2:
        st.markdown("#### WBOM 작업 패키지 요약")
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    st.markdown("#### WBOM 상세 View")
    st.dataframe(pd.DataFrame(wbom_rows), use_container_width=True, hide_index=True, height=520)

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
    st.subheader("1. 작업지시서 요약")
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("2. 작업지시서 상세")
    st.dataframe(pd.DataFrame(instruction_rows), use_container_width=True, hide_index=True, height=520)

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
