from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.digital_thread.ontology_service import build_supply_chain_tracking_context
from src.features.digital_thread.service import build_project_thread_context


def render_project_thread_map_page() -> None:
    current_spec = get_current_spec()
    selected_project = get_selected_project()

    st.title("대시보드")
    st.caption("현재 프로젝트가 기준 정의부터 설계, BOM, 생산 준비까지 어떻게 이어지는지 한눈에 정리합니다.")

    if not current_spec and not selected_project:
        st.info("먼저 실적선 기반 설계 재활용 영역에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

    context = build_project_thread_context(current_spec, selected_project)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("현재 프로젝트", context["project_name"] or "-")
    metric_col2.metric("기준 실적선", context["base_project_name"] or "-")
    metric_col3.metric("연결 단계 수", f"{context['active_nodes'] - 1}/{len(context['nodes']) - 1}")
    metric_col4.metric("최근 흐름", context["latest_event"])

    st.divider()
    st.subheader("1. 한눈에 보는 프로젝트 흐름")
    _render_dashboard_flow(context)

    st.divider()
    st.subheader("2. 단계별 상태 요약")
    _render_stage_summary(context)

    st.divider()
    st.subheader("3. 상세 연결도")
    with st.expander("상세 연결도 보기", expanded=False):
        st.caption("대시보드에서는 핵심 흐름만 먼저 보여주고, 상세 연결은 필요할 때만 확인합니다.")
        st.graphviz_chart(_build_thread_graphviz(context), use_container_width=True)

    st.divider()
    st.subheader("4. 시간 흐름")
    _render_timeline_table(context["timeline"])

    st.divider()
    st.subheader("5. TAG 기반 자재 상태 추적")
    _render_tag_based_material_tracking()


def _render_dashboard_flow(context: dict) -> None:
    node_lookup = {node["node_id"]: node for node in context["nodes"]}
    groups = [
        ("기준 정의", ["spec", "tag"]),
        ("설계 전개", ["pos", "model", "dp", "change"]),
        ("생산 준비", ["block", "mbom", "wbom"]),
    ]

    for title, node_ids in groups:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            cols = st.columns(len(node_ids))
            for col, node_id in zip(cols, node_ids):
                node = node_lookup[node_id]
                with col:
                    st.markdown(f"**{node['title']}**")
                    st.caption(node["subtitle"])
                    st.write(node["detail"])
                    st.write(f"`{_status_label(node['status'])}`")


def _render_stage_summary(context: dict) -> None:
    rows = [
        {
            "단계": node["title"],
            "현재 상태": _status_label(node["status"]),
            "대표 정보": node["subtitle"],
            "설명": node["detail"],
        }
        for node in context["nodes"]
        if node["node_id"] != "project"
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _build_thread_graphviz(context: dict) -> str:
    node_lines = []
    edge_lines = []

    for node in context["nodes"]:
        fillcolor = node["accent"] if node["status"] != "pending" else "#e5e7eb"
        fontcolor = "white" if node["status"] != "pending" else "#6b7280"
        color = node["accent"] if node["status"] != "pending" else "#cbd5e1"
        label = f"{_escape_dot(node['title'])}\\n{_escape_dot(node['subtitle'])}\\n[{_escape_dot(_status_label(node['status']))}]"
        node_lines.append(
            f'"{node["node_id"]}" [label="{label}", shape=box, style="rounded,filled", '
            f'fillcolor="{fillcolor}", color="{color}", fontcolor="{fontcolor}", penwidth=1.8, margin="0.18,0.14"];'
        )

    for edge in context["edges"]:
        edge_lines.append(f'"{edge["from"]}" -> "{edge["to"]}" [color="#94a3b8", penwidth=1.5, arrowsize=0.8];')

    return f"""
digraph ThreadDashboard {{
    graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.45, ranksep=0.7, splines=true];
    node [fontname="Arial"];
    edge [fontname="Arial"];
    {' '.join(node_lines)}
    {' '.join(edge_lines)}
}}
"""


def _render_timeline_table(timeline: list[dict]) -> None:
    if not timeline:
        st.info("아직 연결된 흐름 이력이 없습니다.")
        return

    rows = [{"흐름": item["label"], "시점": item["date"]} for item in timeline]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_tag_based_material_tracking() -> None:
    current_spec = get_current_spec()
    selected_project = get_selected_project()
    context = build_supply_chain_tracking_context(current_spec, selected_project)

    if not context["graph"] or not context["traceable_items"]:
        st.info("추적 가능한 자재나 기자재가 아직 없습니다.")
        return

    selected_item_id = st.selectbox(
        "추적 대상 선택",
        options=[item["id"] for item in context["traceable_items"]],
        format_func=lambda item_id: next(
            f"{item['label']} ({item['node_type']})"
            for item in context["traceable_items"]
            if item["id"] == item_id
        ),
        key="dashboard_supply_item",
    )

    selected_item = next(item for item in context["traceable_items"] if item["id"] == selected_item_id)
    lifecycle_rows = _build_dashboard_lifecycle_rows(selected_item, context)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("추적 대상", selected_item["label"])
    metric_col2.metric("프로젝트", context["project_name"])
    metric_col3.metric("현재 상태", _latest_status_label(lifecycle_rows))

    st.altair_chart(_build_dashboard_lifecycle_chart(lifecycle_rows), use_container_width=True)


def _build_dashboard_lifecycle_rows(selected_item: dict, context: dict) -> list[dict]:
    node_lookup = context["node_lookup"]
    edges = context["edges"]
    item_id = selected_item["id"]

    related_edges = [edge for edge in edges if edge["source"] == item_id or edge["target"] == item_id]
    related_node_ids = set()
    for edge in related_edges:
        related_node_ids.add(edge["source"])
        related_node_ids.add(edge["target"])
    related_nodes = [node_lookup[node_id] for node_id in related_node_ids if node_id in node_lookup and node_id != item_id]

    bom_nodes = [node for node in related_nodes if node["node_type"] == "BomItem"]
    work_nodes = [node for node in related_nodes if node["node_type"] == "WorkPackage"]

    purchase_status = _infer_purchase_status(item_id)
    production_status = "완료" if work_nodes else "대기"
    bom_status = "완료" if bom_nodes else "대기"

    return [
        {"stage": "설계", "status": "완료", "detail": f"{selected_item['label']} 설계 객체 생성", "x": 0.0, "y": 1.0},
        {"stage": "BOM", "status": bom_status, "detail": _join_labels(work_nodes=bom_nodes, default="연결된 BOM 항목 없음"), "x": 1.2, "y": 1.0},
        {"stage": "구매", "status": purchase_status, "detail": _purchase_detail(selected_item['label'], purchase_status), "x": 0.2, "y": 0.0},
        {"stage": "생산", "status": production_status, "detail": _join_labels(work_nodes=work_nodes, default="연결된 생산 항목 없음"), "x": 1.4, "y": 0.0},
    ]


def _build_dashboard_lifecycle_chart(rows: list[dict]) -> alt.Chart:
    nodes_df = pd.DataFrame(rows)
    edges_df = pd.DataFrame(
        [
            {"x": 0.0, "y": 1.0, "x2": 1.2, "y2": 1.0},
            {"x": 1.2, "y": 1.0, "x2": 0.2, "y2": 0.0},
            {"x": 0.2, "y": 0.0, "x2": 1.4, "y2": 0.0},
        ]
    )

    edge_chart = alt.Chart(edges_df).mark_rule(color="#9ca3af", strokeWidth=3).encode(
        x=alt.X("x:Q", axis=None),
        y=alt.Y("y:Q", axis=None),
        x2="x2:Q",
        y2="y2:Q",
    )

    node_chart = alt.Chart(nodes_df).mark_circle(size=5000, opacity=0.98).encode(
        x=alt.X("x:Q", axis=None),
        y=alt.Y("y:Q", axis=None),
        color=alt.Color(
            "status:N",
            scale=alt.Scale(domain=["완료", "진행중", "대기"], range=["#22c55e", "#f59e0b", "#94a3b8"]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("stage:N", title="단계"),
            alt.Tooltip("status:N", title="상태"),
            alt.Tooltip("detail:N", title="주요 내용"),
        ],
    )

    title_chart = alt.Chart(nodes_df).mark_text(fontSize=18, fontWeight="bold", color="#111827", dy=-6).encode(
        x="x:Q",
        y="y:Q",
        text="stage:N",
    )

    status_chart = alt.Chart(nodes_df).mark_text(fontSize=13, color="#111827", dy=18).encode(
        x="x:Q",
        y="y:Q",
        text="status:N",
    )

    return (edge_chart + node_chart + title_chart + status_chart).properties(height=360).configure_view(strokeOpacity=0)


def _infer_purchase_status(item_id: str) -> str:
    seed = sum(ord(char) for char in str(item_id))
    return ["완료", "진행중", "대기"][seed % 3]


def _purchase_detail(label: str, status: str) -> str:
    if status == "완료":
        return f"{label} 관련 발주 완료"
    if status == "진행중":
        return f"{label} 관련 발주 또는 입고 진행중"
    return f"{label} 관련 발주 전 상태"


def _join_labels(work_nodes: list[dict], default: str) -> str:
    if not work_nodes:
        return default
    return ", ".join(node["label"] for node in work_nodes[:3])


def _latest_status_label(rows: list[dict]) -> str:
    production = next((row for row in rows if row["stage"] == "생산"), None)
    if production:
        return f"생산 {production['status']}"
    return "설계 완료"


def _status_label(status: str) -> str:
    return {
        "ready": "연결됨",
        "draft": "준비됨",
        "pending": "대기중",
    }.get(status, status)


def _escape_dot(value: str) -> str:
    return str(value).replace('"', '\\"')
