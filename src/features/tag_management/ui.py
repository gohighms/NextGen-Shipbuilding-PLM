from __future__ import annotations

from copy import deepcopy

import pandas as pd
import streamlit as st

from src.common.paths import TAG_REGISTRY_DIR
from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.tag_management.registry_repository import TagRegistryRepository
from src.features.tag_management.tag_generator import generate_tags_from_attributes


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

    st.title("통합 TAG 관리")
    st.caption("건조사양서로부터 생성된 TAG로 건조사양서, POS, 모델, BOM을 잇습니다. CFIHOS 2.0 을 참조합니다.")

    current_spec = get_current_spec()
    selected_project = get_selected_project()
    registry_repository = TagRegistryRepository(TAG_REGISTRY_DIR)

    if not current_spec or not selected_project:
        st.info("먼저 `유사 프로젝트 탐색`에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

    base_result = generate_tags_from_attributes(current_spec.get("attributes", {}))
    tag_result = _build_extended_tag_result(base_result, current_spec, selected_project)

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 현재 프로젝트: `{current_spec['project_name']}`")
        st.write(f"- 기준 실적선: `{selected_project['project_name']}`")
    with top_col2:
        st.write(f"- 기준 사양서 ID: `{selected_project['spec_id']}`")
        # st.write("- 설명: `현재 프로젝트 사양에서 많은 TAG 사례를 만들고, 그 TAG가 후속 산출물을 잇는 매개체가 되는 모습을 확인`")

    st.divider()
    st.subheader("1. TAG 생성")
    st.caption("현재 프로젝트 사양을 바탕으로 TAG를 생성합니다.")

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("현재 프로젝트", current_spec["project_name"])
    metric_col2.metric("기준 실적선", selected_project["project_name"])
    metric_col3.metric("생성 TAG 수", len(tag_result["tags"]))

    tag_rows = [
        {
            "분류": item["section"],
            "항목": item["field_name"],
            "값": item["value"],
            "TAG": item["tag_name"],
        }
        for item in tag_result["tags"]
    ]
    st.dataframe(pd.DataFrame(tag_rows), use_container_width=True, hide_index=True, height=420)

    if st.button("현재 프로젝트 TAG 저장", type="primary", use_container_width=True):
        saved_path = registry_repository.save(
            source_type="reuse_flow",
            source_name=current_spec["project_name"],
            result=tag_result,
        )
        st.success(f"현재 프로젝트 TAG를 저장했습니다. `{saved_path.name}`")

    st.divider()
    st.subheader("2. TAG 연결 사례")
    st.caption("TAG가 건조사양서 문구, POS 문구, 모델 객체, BOM 항목을 어떻게 이어주는지 항목 단위로 보여줍니다.")

    linkage_df = pd.DataFrame(tag_result["tag_link_rows"])
    st.dataframe(linkage_df, use_container_width=True, hide_index=True, height=620)

    st.divider()
    st.subheader("3. 최근 저장된 TAG")
    recent_items = [
        item for item in registry_repository.list_all() if item.get("source_name") == current_spec["project_name"]
    ]
    if not recent_items:
        st.info("현재 프로젝트 기준으로 저장된 TAG가 아직 없습니다.")
        return

    latest_item = recent_items[0]
    st.write(f"- 저장 ID: `{latest_item['registry_id']}`")
    st.write(f"- 저장 시각: `{latest_item['saved_at']}`")
    st.write(f"- TAG 수: `{latest_item['tag_count']}`")
    st.dataframe(pd.DataFrame(latest_item["tags"]), use_container_width=True, hide_index=True, height=320)


def _build_extended_tag_result(base_result: dict, current_spec: dict, selected_project: dict) -> dict:
    result = deepcopy(base_result)
    project_name = current_spec["project_name"]
    baseline_name = selected_project["project_name"]

    base_tags = list(result["tags"])
    seen_tag_names = {item["tag_name"] for item in base_tags}

    templates = _build_tag_case_templates(current_spec, baseline_name)
    extended_tags = list(base_tags)
    link_rows = []

    for template in templates:
        tag_name = template["tag_name"]
        if tag_name in seen_tag_names:
            section = template["section"]
            field_name = template["field_name"]
            value = template["value"]
        else:
            section = template["section"]
            field_name = template["field_name"]
            value = template["value"]
            extended_tags.append(
                {
                    "section": section,
                    "field_name": field_name,
                    "value": value,
                    "tag_name": tag_name,
                }
            )
            seen_tag_names.add(tag_name)

        link_rows.append(
            {
                "기준 실적선": baseline_name,
                "건조사양서 문구": template["spec_clause"],
                "TAG": tag_name,
                "POS 문구": template["pos_clause"],
                "모델 연결 객체": template["model_object"],
                "BOM 연결 항목": template["bom_item"],
            }
        )

    extended_tags.sort(key=lambda item: item["tag_name"])
    result["tags"] = extended_tags[:30]
    result["tag_link_rows"] = link_rows[:30]
    return result


def _build_tag_case_templates(current_spec: dict, baseline_name: str) -> list[dict]:
    attributes = current_spec.get("attributes", {})
    basic = attributes.get("basic_info", {})
    dim = attributes.get("principal_dimensions", {})
    machinery = attributes.get("machinery", {})
    cargo = attributes.get("cargo_system", {})

    ship_type = basic.get("ship_type_hint", "LNGC")
    loa = dim.get("loa_m", 299.0)
    breadth = dim.get("breadth_m", 46.4)
    draft = dim.get("draft_m", 11.5)
    main_engine = machinery.get("main_engine", "ME-GI")
    cargo_capacity = cargo.get("cargo_capacity_m3", 241000)
    tank_system = cargo.get("cargo_tank_system", "GTT Mark III Flex")

    return [
        _case("basic_info", "basic_info.ship_type_hint", ship_type, f"SB-BAS-SHIPTYPE-{ship_type}", f"{ship_type} 선형 기준", f"{ship_type} 기준 구매 사양 적용", "선형 기본 모델", "선형 기준 BOM"),
        _case("principal_dimensions", "principal_dimensions.loa_m", loa, f"SB-DIM-LOA-{_norm(loa)}", f"전장 {loa} m", f"LOA {loa} m 기준 치수 문구", "현측 외판 001", "BLOCK-109-중조-PLATE-SS-001"),
        _case("principal_dimensions", "principal_dimensions.breadth_m", breadth, f"SB-DIM-BREADTH-{_norm(breadth)}", f"선폭 {breadth} m", f"Breadth {breadth} m 기준 치수 문구", "현측 프레임 브라켓 001", "BLOCK-109-중조-FRAME-BRKT-001"),
        _case("principal_dimensions", "principal_dimensions.draft_m", draft, f"SB-DIM-DRAFT-{_norm(draft)}", f"만재흘수 {draft} m", f"Draft {draft} m 기준 치수 문구", "저판 외판 001", "BLOCK-105-중조-PLATE-BS-001"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-MENG-{main_engine}", f"메인 엔진 {main_engine}", f"{main_engine} 기준 기관 문구", "메인 엔진 기자재 받침대", "BLOCK-109-대조-MAIN-ENGINE-SEAT"),
        _case("cargo_system", "cargo_system.cargo_capacity_m3", cargo_capacity, f"SB-CGO-CAPA-{cargo_capacity}", f"화물창 용적 {cargo_capacity} m3", f"{cargo_capacity} m3 기준 화물시스템 문구", "화물창 구조 01", "BLOCK-108-소조-CARGO-TANK-01"),
        _case("cargo_system", "cargo_system.cargo_tank_system", tank_system, f"SB-CGO-TANKSYS-{_norm(tank_system)}", f"화물창 시스템 {tank_system}", f"{tank_system} 기준 화물창 문구", "멤브레인 구조 01", "BLOCK-108-소조-TANK-MEMBRANE-01"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-FGAS-{main_engine}", "연료가스 계통", f"{main_engine} 연계 연료가스 계통 문구", "연료가스 파이프 001", "BLOCK-108-중조-PIPE-FG-001"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-FOUND-{main_engine}", "기관실 기초", f"{main_engine} 연계 기초 구조 문구", "메인 엔진 베드 플레이트", "BLOCK-106-중조-BED-106-01"),
        _case("principal_dimensions", "principal_dimensions.loa_m", loa, f"SB-HUL-SIDESHELL-{_norm(loa)}", "현측 외판 영역", f"선체 현측 외판 기준 문구", "현측 외판", "BLOCK-104-중조-PNL-104-01"),
        _case("principal_dimensions", "principal_dimensions.draft_m", draft, f"SB-HUL-BOTSHELL-{_norm(draft)}", "저판 외판 영역", f"저판 외판 기준 문구", "저판 패널 조립 01", "BLOCK-105-중조-PNL-105-01"),
        _case("principal_dimensions", "principal_dimensions.loa_m", loa, f"SB-HUL-LONGI-{_norm(loa)}", "종보강재 기준", f"종보강재 기준 문구", "종보강재 001", "BLOCK-103-소조-STIFFENER-LG-001"),
        _case("cargo_system", "cargo_system.cargo_capacity_m3", cargo_capacity, f"SB-CGO-INSUL-{cargo_capacity}", "단열 구조 기준", f"화물창 단열 기준 문구", "화물창 단열 구조 01", "BLOCK-108-소조-INSULATION-01"),
        _case("cargo_system", "cargo_system.cargo_tank_system", tank_system, f"SB-CGO-BARR-{_norm(tank_system)}", "2차 방벽 기준", f"2차 방벽 기준 문구", "2차 방벽 구조 01", "BLOCK-108-소조-SECONDARY-BARRIER-01"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-TRAY-{main_engine}", "기관부 전장 기준", f"기관부 전장 기준 문구", "케이블 트레이 001", "BLOCK-110-PE-CABLE-TRAY-001"),
        _case("basic_info", "basic_info.ship_type_hint", ship_type, f"SB-BAS-YARD-{baseline_name}", f"기준 실적선 {baseline_name}", f"{baseline_name} 기준 재사용 문구", "프로젝트 기본 모델", "BLOCK-101-소조-BRKT-101-01"),
        _case("principal_dimensions", "principal_dimensions.breadth_m", breadth, f"SB-DIM-SIDESPACE-{_norm(breadth)}", "현측 공간 기준", f"현측 공간 기준 문구", "현측 웹 001", "BLOCK-101-소조-WEB-101-01"),
        _case("principal_dimensions", "principal_dimensions.loa_m", loa, f"SB-DIM-DECK-{_norm(loa)}", "상갑판 길이 기준", f"상갑판 기준 문구", "상갑판 프레임 01", "BLOCK-102-소조-FRM-102-01"),
        _case("principal_dimensions", "principal_dimensions.draft_m", draft, f"SB-DIM-BOTTOMWEB-{_norm(draft)}", "저판 웹 기준", f"저판 웹 기준 문구", "저판 웹 001", "BLOCK-103-소조-WEB-103-01"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-SUPPORT-{main_engine}", "기관실 서포트 기준", f"기관실 서포트 기준 문구", "기관실 서포트 조립 01", "BLOCK-106-중조-SUP-106-01"),
        _case("cargo_system", "cargo_system.cargo_capacity_m3", cargo_capacity, f"SB-CGO-TANK-{cargo_capacity}-A", "화물창 A 구역 기준", f"화물창 A 구역 기준 문구", "화물창 구조 A", "BLOCK-108-소조-CARGO-TANK-A"),
        _case("cargo_system", "cargo_system.cargo_capacity_m3", cargo_capacity, f"SB-CGO-TANK-{cargo_capacity}-B", "화물창 B 구역 기준", f"화물창 B 구역 기준 문구", "화물창 구조 B", "BLOCK-108-소조-CARGO-TANK-B"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-PIPE-{main_engine}-A", "연료가스 파이프 A", f"연료가스 파이프 A 기준 문구", "연료가스 파이프 002", "BLOCK-108-중조-PIPE-FG-002"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-PIPE-{main_engine}-B", "연료가스 파이프 B", f"연료가스 파이프 B 기준 문구", "연료가스 파이프 003", "BLOCK-108-중조-PIPE-FG-003"),
        _case("principal_dimensions", "principal_dimensions.breadth_m", breadth, f"SB-HUL-BRKT-{_norm(breadth)}-A", "현측 브라켓 A", f"현측 브라켓 A 기준 문구", "현측 브라켓 A", "BLOCK-101-소조-BRKT-101-02"),
        _case("principal_dimensions", "principal_dimensions.breadth_m", breadth, f"SB-HUL-BRKT-{_norm(breadth)}-B", "현측 브라켓 B", f"현측 브라켓 B 기준 문구", "현측 브라켓 B", "BLOCK-102-소조-BRKT-102-02"),
        _case("principal_dimensions", "principal_dimensions.loa_m", loa, f"SB-HUL-GIRD-{_norm(loa)}-A", "현측 거더 A", f"현측 거더 A 기준 문구", "현측 거더 A", "BLOCK-104-중조-GDR-104-01"),
        _case("principal_dimensions", "principal_dimensions.loa_m", loa, f"SB-HUL-GIRD-{_norm(loa)}-B", "저판 거더 B", f"저판 거더 B 기준 문구", "저판 거더 B", "BLOCK-105-중조-GDR-105-01"),
        _case("machinery", "machinery.main_engine", main_engine, f"SB-MAC-BED-{main_engine}-A", "메인 엔진 베드 A", f"메인 엔진 베드 A 기준 문구", "메인 엔진 베드 A", "BLOCK-106-중조-BED-106-02"),
        _case("cargo_system", "cargo_system.cargo_tank_system", tank_system, f"SB-CGO-MEM-{_norm(tank_system)}-A", "멤브레인 패널 A", f"멤브레인 패널 A 기준 문구", "멤브레인 패널 A", "BLOCK-108-소조-MEM-108-01"),
    ]


def _case(section: str, field_name: str, value, tag_name: str, spec_clause: str, pos_clause: str, model_object: str, bom_item: str) -> dict:
    return {
        "section": section,
        "field_name": field_name,
        "value": value,
        "tag_name": tag_name,
        "spec_clause": spec_clause,
        "pos_clause": pos_clause,
        "model_object": model_object,
        "bom_item": bom_item,
    }


def _norm(value) -> str:
    text = str(value).upper()
    normalized = []
    for char in text:
        if char.isalnum():
            normalized.append(char)
        elif char in {".", "-", "_", " "}:
            normalized.append("-")
    return "".join(normalized).strip("-")
