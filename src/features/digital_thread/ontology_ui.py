from __future__ import annotations

import pandas as pd
import streamlit as st

from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.digital_thread.ontology_service import build_ontology_context


def render_ontology_management_page() -> None:
    current_spec = get_current_spec()
    selected_project = get_selected_project()

    st.title("온톨로지 / 지식그래프 관리")
    st.caption("기존 기능에서 생성된 개체와 관계를 개념 체계와 지식그래프 형태로 관리하고 조회합니다.")

    if not current_spec and not selected_project:
        st.info("먼저 실적선 기반 설계 재활용 영역에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

    context = build_ontology_context(current_spec, selected_project)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("현재 프로젝트", context["project_name"] or "-")
    metric_col2.metric("개념 수", len(context["concepts"]))
    metric_col3.metric("관계 수", len(context["relations"]))
    metric_col4.metric("세부 그래프 수", len(context["detailed_graphs"]))

    st.divider()
    st.subheader("1. 개념 체계")
    st.caption("프로젝트 안에서 어떤 개념을 정의하고, 어떤 관계를 허용하는지 먼저 보여줍니다. 그래프는 일반적인 지식그래프처럼 둥근 노드 중심으로 표시합니다.")
    st.graphviz_chart(context["concept_graph_dot"], use_container_width=True)

    concept_col1, concept_col2 = st.columns([1.1, 1])
    with concept_col1:
        st.markdown("#### 개념 목록")
        st.dataframe(pd.DataFrame(context["concepts"]), use_container_width=True, hide_index=True)
    with concept_col2:
        st.markdown("#### 관계 정의")
        st.dataframe(pd.DataFrame(context["relations"]), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("1-1. 세부 엔티티 확장 방향")
    st.caption("LLM이 상위 문서 수준이 아니라 세부 객체 수준으로 검색·추론하려면 아래 레벨까지 엔티티를 확장해야 합니다.")
    st.dataframe(pd.DataFrame(context["detailed_entities"]), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("2. 현재 프로젝트 세부 지식그래프")
    st.caption("건조사양서, POS, 모델, BOM을 문서 하위 요소와 설계 객체 수준으로 내려서 보여줍니다.")

    graph_options = context["detailed_graphs"]
    if not graph_options:
        st.info("현재 프로젝트 기준으로 표시할 세부 엔티티 그래프가 없습니다.")
    else:
        selected_graph_id = st.selectbox(
            "세부 그래프 선택",
            options=[item["graph_id"] for item in graph_options],
            format_func=lambda graph_id: next(
                item["title"]
                for item in graph_options
                if item["graph_id"] == graph_id
            ),
        )
        selected_graph = next(item for item in graph_options if item["graph_id"] == selected_graph_id)
        st.graphviz_chart(selected_graph["dot"], use_container_width=True)
        st.caption("한 번에 모든 세부 엔티티를 그리지 않고, 엔티티 그룹별로 나눠서 안정적으로 표시합니다.")

    instance_col1, instance_col2 = st.columns([1.1, 1])
    with instance_col1:
        st.markdown("#### 세부 엔티티 노드")
        if graph_options:
            st.dataframe(pd.DataFrame(selected_graph["nodes"]), use_container_width=True, hide_index=True)
        else:
            st.info("표시할 세부 엔티티 노드가 없습니다.")
    with instance_col2:
        st.markdown("#### 세부 엔티티 관계")
        if graph_options:
            st.dataframe(pd.DataFrame(selected_graph["edges"]), use_container_width=True, hide_index=True)
        else:
            st.info("표시할 세부 엔티티 관계가 없습니다.")

    st.divider()
    st.subheader("3. 선택 세부 노드 상세")
    if graph_options:
        selected_node_id = st.selectbox(
            "상세 확인 세부 노드",
            options=[item["id"] for item in selected_graph["nodes"]],
            format_func=lambda node_id: next(
                f"{item['label']} ({item['node_type']})"
                for item in selected_graph["nodes"]
                if item["id"] == node_id
            ),
        )

        selected_node = next(item for item in selected_graph["nodes"] if item["id"] == selected_node_id)
        related_edges = [
            edge for edge in selected_graph["edges"]
            if edge["source"] == selected_node_id or edge["target"] == selected_node_id
        ]

        detail_col1, detail_col2 = st.columns([1, 1])
        with detail_col1:
            with st.container(border=True):
                st.markdown(f"**{selected_node['label']}**")
                st.caption(selected_node["node_type"])
                st.write(f"- 노드 ID: `{selected_node['id']}`")
                st.write(f"- 색상: `{selected_node['color']}`")

        with detail_col2:
            st.markdown("#### 연관 관계")
            if related_edges:
                st.dataframe(pd.DataFrame(related_edges), use_container_width=True, hide_index=True)
            else:
                st.info("연결된 관계가 없습니다.")
    else:
        st.info("상세 확인할 세부 노드가 없습니다.")
