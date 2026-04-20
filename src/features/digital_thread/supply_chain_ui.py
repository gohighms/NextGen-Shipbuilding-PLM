from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.digital_thread.ontology_service import build_supply_chain_tracking_context


STATUS_COLORS = {
    "완료": "#22c55e",
    "진행중": "#f59e0b",
    "대기": "#94a3b8",
}


def render_supply_chain_tracking_page() -> None:
    current_spec = get_current_spec()
    selected_project = get_selected_project()

    st.title("구매-설계-생산 추적")
    st.caption("특정 자재나 기자재 하나를 기준으로 설계, BOM, 구매, 생산까지 어디까지 진행됐는지 한 화면에서 확인합니다.")

    if not current_spec and not selected_project:
        st.info("먼저 `유사 프로젝트 검색`에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

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
    )

    selected_item = next(item for item in context["traceable_items"] if item["id"] == selected_item_id)
    lifecycle_rows = _build_lifecycle_rows(selected_item, context)

    st.subheader("1. 생애주기 흐름")
    st.caption("1행은 설계와 BOM, 2행은 구매와 생산입니다. 노드 색은 현재 상태를 뜻합니다.")

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("현재 프로젝트", context["project_name"])
    metric_col2.metric("추적 대상", selected_item["label"])
    metric_col3.metric("현재 상태", _latest_status_label(lifecycle_rows))

    chart = _build_lifecycle_chart(lifecycle_rows)
    st.altair_chart(chart, use_container_width=True)

    st.divider()
    st.subheader("2. 단계별 요약")
    summary_df = pd.DataFrame(
        [
            {
                "단계": row["stage"],
                "상태": row["status"],
                "주요 내용": row["detail"],
            }
            for row in lifecycle_rows
        ]
    )
    st.dataframe(summary_df, use_container_width=True, hide_index=True)


def _build_lifecycle_rows(selected_item: dict, context: dict) -> list[dict]:
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

    rows = [
        {
            "stage": "설계",
            "status": "완료",
            "detail": f"{selected_item['label']} 설계 객체가 생성되어 있습니다.",
            "x": 0.0,
            "y": 1.0,
        },
        {
            "stage": "BOM",
            "status": bom_status,
            "detail": _join_labels(bom_nodes, default="연결된 BOM 항목이 아직 없습니다."),
            "x": 1.2,
            "y": 1.0,
        },
        {
            "stage": "구매",
            "status": purchase_status,
            "detail": _purchase_detail(selected_item["label"], purchase_status),
            "x": 0.2,
            "y": 0.0,
        },
        {
            "stage": "생산",
            "status": production_status,
            "detail": _join_labels(work_nodes, default="연결된 생산/작업 항목이 아직 없습니다."),
            "x": 1.4,
            "y": 0.0,
        },
    ]
    return rows


def _build_lifecycle_chart(rows: list[dict]) -> alt.Chart:
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

    node_chart = alt.Chart(nodes_df).mark_circle(size=5200, opacity=0.98).encode(
        x=alt.X("x:Q", axis=None),
        y=alt.Y("y:Q", axis=None),
        color=alt.Color(
            "status:N",
            scale=alt.Scale(
                domain=list(STATUS_COLORS.keys()),
                range=list(STATUS_COLORS.values()),
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("stage:N", title="단계"),
            alt.Tooltip("status:N", title="상태"),
            alt.Tooltip("detail:N", title="주요 내용"),
        ],
    )

    title_chart = alt.Chart(nodes_df).mark_text(
        fontSize=18,
        fontWeight="bold",
        color="#111827",
        dy=-6,
    ).encode(
        x="x:Q",
        y="y:Q",
        text="stage:N",
    )

    status_chart = alt.Chart(nodes_df).mark_text(
        fontSize=13,
        color="#111827",
        dy=18,
    ).encode(
        x="x:Q",
        y="y:Q",
        text="status:N",
    )

    return (
        (edge_chart + node_chart + title_chart + status_chart)
        .properties(height=380)
        .configure_view(strokeOpacity=0)
    )


def _infer_purchase_status(item_id: str) -> str:
    seed = sum(ord(char) for char in str(item_id))
    states = ["완료", "진행중", "대기"]
    return states[seed % len(states)]


def _purchase_detail(label: str, status: str) -> str:
    if status == "완료":
        return f"{label} 관련 발주가 완료되어 구매 이력이 연결돼 있습니다."
    if status == "진행중":
        return f"{label} 관련 발주 또는 입고가 진행중이라고 가정합니다."
    return f"{label} 관련 발주는 아직 진행 전 상태라고 가정합니다."


def _join_labels(nodes: list[dict], default: str) -> str:
    if not nodes:
        return default
    labels = [node["label"] for node in nodes[:3]]
    return ", ".join(labels)


def _latest_status_label(rows: list[dict]) -> str:
    production = next((row for row in rows if row["stage"] == "생산"), None)
    if production:
        return f"생산 {production['status']}"
    return "설계 완료"
