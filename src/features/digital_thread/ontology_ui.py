from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.digital_thread.ontology_service import (
    build_ontology_graph_html,
    build_ontology_pyvis_context,
    collect_focus_tags,
    filter_ontology_graph,
    focus_ontology_graph,
)


def render_ontology_management_page() -> None:
    current_spec = get_current_spec()
    selected_project = get_selected_project()

    st.title("온톨로지 / 지식그래프")
    st.caption("온톨로지는 항목과 항목 사이의 의미 관계를 설명합니다. 여기서는 건조사양서, POS, 모델, BOM이 어떤 의미 관계로 연결되는지 그래프로 확인합니다.")

    if not current_spec or not selected_project:
        st.info("먼저 `유사 프로젝트 탐색`에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

    context = build_ontology_pyvis_context(current_spec, selected_project)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("현재 프로젝트", context["project_name"])
    metric_col2.metric("기준 실적선", context["baseline_project_name"])
    metric_col3.metric("TAG 수", context["tag_count"])
    metric_col4.metric("그래프 연결 수", context["edge_count"])

    st.divider()
    st.subheader("1. 의미 관계 그래프")
    st.caption("노드 색은 건조사양서, POS, 모델, BOM을 구분합니다. 엣지 라벨은 TAG이고, 마우스를 올리면 의미 관계를 볼 수 있습니다.")

    legend_col1, legend_col2, legend_col3, legend_col4 = st.columns(4)
    _render_legend_card(legend_col1, "#3b82f6", "건조사양서", "사양 문구")
    _render_legend_card(legend_col2, "#14b8a6", "POS", "POS 문구")
    _render_legend_card(legend_col3, "#22c55e", "모델", "모델 객체")
    _render_legend_card(legend_col4, "#a16207", "BOM", "BOM 항목")

    st.divider()
    st.subheader("2. 그래프 필터")
    filter_col1, filter_col2, filter_col3 = st.columns([1.2, 1.2, 0.8])

    with filter_col1:
        selected_tag_groups = st.multiselect(
            "TAG군",
            options=context["tag_groups"],
            default=[],
            help="예: DIM, MAC, CGO 같은 TAG군만 골라서 볼 수 있습니다.",
        )

    with filter_col2:
        selected_node_types = st.multiselect(
            "노드 유형",
            options=["spec", "pos", "model", "bom"],
            default=[],
            format_func=lambda value: {
                "spec": "건조사양서",
                "pos": "POS",
                "model": "모델",
                "bom": "BOM",
            }[value],
            help="보고 싶은 노드 유형만 남길 수 있습니다.",
        )

    with filter_col3:
        density_mode = st.radio(
            "표시 밀도",
            options=["전체", "핵심 관계만"],
            help="핵심 관계만 선택하면 건조사양서 → POS → 모델 → BOM 흐름만 남깁니다.",
        )

    filtered_nodes, filtered_edges = filter_ontology_graph(
        context["nodes"],
        context["edges"],
        selected_tag_groups=selected_tag_groups,
        selected_node_types=selected_node_types,
        density_mode=density_mode,
    )

    st.divider()
    st.subheader("3. TAG focus")
    focus_col1, focus_col2 = st.columns([1.2, 0.8])
    focus_tags = collect_focus_tags(filtered_edges)

    with focus_col1:
        focus_tag = st.selectbox(
            "중심 TAG",
            options=["전체"] + focus_tags,
            help="선택한 TAG를 중심으로 관련 경로만 간단히 볼 수 있습니다.",
        )
    with focus_col2:
        hop_mode = st.radio(
            "표시 범위",
            options=["전체", "TAG 경로만", "1-hop", "2-hop"],
            horizontal=True,
        )

    filtered_nodes, filtered_edges = focus_ontology_graph(
        filtered_nodes,
        filtered_edges,
        focus_tag=focus_tag,
        hop_mode=hop_mode,
    )

    summary_col1, summary_col2 = st.columns(2)
    summary_col1.metric("필터 후 노드 수", len(filtered_nodes))
    summary_col2.metric("필터 후 연결 수", len(filtered_edges))

    if not filtered_nodes or not filtered_edges:
        st.info("현재 필터 조건에 맞는 연결이 없습니다. TAG군이나 노드 유형을 조금 더 넓혀보세요.")
        return

    components.html(
        build_ontology_graph_html(filtered_nodes, filtered_edges, context["project_name"]),
        height=920,
        scrolling=True,
    )


def _render_legend_card(column, color: str, title: str, subtitle: str) -> None:
    with column:
        st.markdown(
            f"""
            <div style="
                border:1px solid #d1d5db;
                border-radius:12px;
                padding:12px 14px;
                background:#ffffff;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="
                        width:14px;
                        height:14px;
                        border-radius:999px;
                        background:{color};">
                    </div>
                    <div>
                        <div style="font-weight:700;color:#111827;">{title}</div>
                        <div style="font-size:0.92rem;color:#6b7280;">{subtitle}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
