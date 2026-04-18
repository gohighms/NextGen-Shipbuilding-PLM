from __future__ import annotations

import pandas as pd
import streamlit as st

from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.digital_thread.ontology_service import build_supply_chain_tracking_context


def render_supply_chain_tracking_page() -> None:
    current_spec = get_current_spec()
    selected_project = get_selected_project()

    st.title("구매-설계-생산 추적")
    st.caption("특정 기자재나 자재가 설계, 구매, 생산 단계에서 어떻게 이어지는지 추적합니다.")

    if not current_spec and not selected_project:
        st.info("먼저 실적선 기반 설계 재활용 영역에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

    context = build_supply_chain_tracking_context(current_spec, selected_project)
    if not context["graph"] or not context["traceable_items"]:
        st.info("추적 가능한 기자재 또는 자재 그래프가 아직 없습니다.")
        return

    traceable_items = context["traceable_items"]
    selected_item_id = st.selectbox(
        "추적 대상 선택",
        options=[item["id"] for item in traceable_items],
        format_func=lambda item_id: next(
            f"{item['label']} ({item['node_type']})"
            for item in traceable_items
            if item["id"] == item_id
        ),
    )

    selected_item = next(item for item in traceable_items if item["id"] == selected_item_id)
    related_edges = [
        edge for edge in context["edges"]
        if edge["source"] == selected_item_id or edge["target"] == selected_item_id
    ]
    neighborhood_ids = {selected_item_id}
    for edge in related_edges:
        neighborhood_ids.add(edge["source"])
        neighborhood_ids.add(edge["target"])

    focus_nodes = [context["node_lookup"][node_id] for node_id in neighborhood_ids if node_id in context["node_lookup"]]
    focus_edges = [
        edge for edge in context["edges"]
        if edge["source"] in neighborhood_ids and edge["target"] in neighborhood_ids
    ]

    st.subheader("1. 추적 대상 주변 지식그래프")
    st.graphviz_chart(_build_focus_graph_dot(focus_nodes, focus_edges), use_container_width=True)

    st.divider()
    st.subheader("2. 생애주기 요약")
    stage_rows = _build_stage_rows(selected_item_id, context["node_lookup"], context["edges"])
    stage_col1, stage_col2, stage_col3 = st.columns(3)
    stage_col1.metric("설계 연결", _count_stage(stage_rows, "설계"))
    stage_col2.metric("구매 연결", _count_stage(stage_rows, "구매"))
    stage_col3.metric("생산 연결", _count_stage(stage_rows, "생산"))

    summary_col1, summary_col2 = st.columns([0.9, 1.1])
    with summary_col1:
        with st.container(border=True):
            st.markdown(f"**{selected_item['label']}**")
            st.caption(selected_item["node_type"])
            st.write(f"- 프로젝트: `{context['project_name']}`")
            st.write(f"- 노드 ID: `{selected_item['id']}`")
            st.write("- 이 항목을 중심으로 구매, BOM, 생산 패키지 연결 관계를 추적합니다.")
    with summary_col2:
        st.dataframe(pd.DataFrame(stage_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("3. 연결 세부 정보")
    detail_col1, detail_col2 = st.columns([1, 1])
    with detail_col1:
        st.markdown("#### 연관 노드")
        st.dataframe(pd.DataFrame(focus_nodes), use_container_width=True, hide_index=True)
    with detail_col2:
        st.markdown("#### 연관 관계")
        st.dataframe(pd.DataFrame(focus_edges), use_container_width=True, hide_index=True)


def _build_stage_rows(selected_item_id: str, node_lookup: dict, edges: list[dict]) -> list[dict]:
    rows = []
    stage_by_type = {
        "Equipment": "설계",
        "MaterialItem": "설계",
        "BomItem": "설계",
        "PurchaseItem": "구매",
        "WorkPackage": "생산",
    }

    for edge in edges:
        if edge["source"] != selected_item_id and edge["target"] != selected_item_id:
            continue
        related_id = edge["target"] if edge["source"] == selected_item_id else edge["source"]
        related = node_lookup.get(related_id)
        if not related:
            continue
        rows.append(
            {
                "단계": stage_by_type.get(related["node_type"], "연결"),
                "연결 대상": related["label"],
                "유형": related["node_type"],
                "관계": edge["relation"],
            }
        )

    rows.sort(key=lambda item: ["설계", "구매", "생산", "연결"].index(item["단계"]))
    return rows


def _count_stage(rows: list[dict], stage_name: str) -> int:
    return sum(1 for row in rows if row["단계"] == stage_name)


def _build_focus_graph_dot(nodes: list[dict], edges: list[dict]) -> str:
    node_lines = []
    edge_lines = []

    for node in nodes:
        node_lines.append(
            f'"{node["id"]}" [label="{_escape_dot(node["label"])}\\n{_escape_dot(node["node_type"])}", '
            f'shape=ellipse, style="filled", fillcolor="{node["color"]}", color="{node["color"]}", '
            f'fontcolor="white", penwidth=2.2, margin="0.22,0.16"];'
        )

    for edge in edges:
        edge_lines.append(
            f'"{edge["source"]}" -> "{edge["target"]}" '
            f'[label="{_escape_dot(edge["relation"])}", color="#64748b", fontcolor="#475569", penwidth=1.8, arrowsize=0.85];'
        )

    return f"""
digraph SupplyTrace {{
    graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.65, ranksep=0.9, splines=true, outputorder=edgesfirst];
    node [fontname="Arial"];
    edge [fontname="Arial"];
    {' '.join(node_lines)}
    {' '.join(edge_lines)}
}}
"""


def _escape_dot(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')
