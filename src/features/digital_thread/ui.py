from __future__ import annotations

import pandas as pd
import streamlit as st

from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.digital_thread.service import build_project_thread_context


def render_project_thread_map_page() -> None:
    current_spec = get_current_spec()
    selected_project = get_selected_project()

    st.title("프로젝트 Thread Map")
    st.caption("프로젝트 기준으로 사양서, TAG, POS, 모델, 계획, BOM, 작업지시서가 어떻게 이어지는지 안정적으로 확인합니다.")

    if not current_spec and not selected_project:
        st.info("먼저 실적선 기반 설계 재활용 영역에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

    context = build_project_thread_context(current_spec, selected_project)
    focus_mode, focus_value = _render_focus_controls(context)
    focus_state = _build_focus_state(context, focus_mode, focus_value)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("현재 프로젝트", context["project_name"] or "-")
    metric_col2.metric("연결된 노드", f"{context['active_nodes']}/{len(context['nodes'])}")
    metric_col3.metric("DP Key Event", context["dp_count"])
    metric_col4.metric("최근 흐름", context["latest_event"])

    st.divider()
    st.subheader("한눈에 보는 핵심 흐름")
    _render_overview_flow(context, focus_state)

    st.divider()
    st.subheader("상세 연결도")
    st.caption("상세 연결도는 보조 정보로만 두고, 본문은 표와 카드 중심으로 안정적으로 구성했습니다.")
    st.graphviz_chart(_build_thread_graphviz(context, focus_state), use_container_width=True)

    st.divider()
    st.subheader("포커스 상세")
    _render_focus_detail(context, focus_state, focus_mode, focus_value)

    st.divider()
    st.subheader("노드 상세 패널")
    _render_node_detail_panel(context, focus_state)

    st.divider()
    st.subheader("시간 흐름")
    _render_timeline_table(context["timeline"])

    st.divider()
    st.subheader("연결 요약")
    _render_summary_tables(context)


def _render_focus_controls(context: dict) -> tuple[str, str]:
    st.subheader("포커스 대상")
    st.caption("전체 흐름을 보거나, 특정 TAG 또는 특정 단계만 중심으로 볼 수 있습니다.")

    mode_col, value_col = st.columns([1, 1.4])
    with mode_col:
        focus_mode = st.radio(
            "보기 방식",
            options=["전체 흐름", "TAG 중심 추적", "단계 중심 추적"],
            horizontal=True,
        )

    with value_col:
        if focus_mode == "TAG 중심 추적":
            tag_options = _build_tag_options(context)
            if tag_options:
                focus_value = st.selectbox("기준 TAG", options=tag_options)
            else:
                st.info("저장된 TAG가 없어서 전체 흐름으로 전환합니다.")
                focus_mode = "전체 흐름"
                focus_value = "전체 흐름"
        elif focus_mode == "단계 중심 추적":
            stage_options = [node["title"] for node in context["nodes"] if node["node_id"] != "project"]
            focus_value = st.selectbox("기준 단계", options=stage_options)
        else:
            focus_value = "전체 흐름"

    return focus_mode, focus_value


def _render_overview_flow(context: dict, focus_state: dict) -> None:
    node_lookup = {node["node_id"]: node for node in context["nodes"]}
    groups = [
        ("1. 설계 기준", "프로젝트 출발점", ["spec", "tag"]),
        ("2. 설계 산출물", "문서와 모델 준비", ["pos", "model", "dp", "change"]),
        ("3. 생산 준비", "목적별 BOM 구성", ["block", "mbom", "wbom"]),
        ("4. 실행", "작업 실행 기준", ["work"]),
    ]

    if focus_state["active"]:
        st.caption(f"현재 포커스: `{focus_state['label']}`")

    for title, subtitle, node_ids in groups:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(subtitle)

            cols = st.columns(len(node_ids))
            for col, node_id in zip(cols, node_ids):
                node = node_lookup[node_id]
                with col:
                    is_focused = (not focus_state["active"]) or (node_id in focus_state["focused_nodes"])
                    _render_node_snapshot(node, is_focused)


def _render_node_snapshot(node: dict, is_focused: bool) -> None:
    if is_focused:
        st.markdown(f"**{node['title']}**")
        st.caption(node["subtitle"])
        st.write(node["detail"])
        st.write(f"`{_status_label(node['status'])}`")
    else:
        st.markdown(f"**{node['title']}**")
        st.caption("현재 포커스 바깥")
        st.write(f"`{_status_label(node['status'])}`")


def _build_thread_graphviz(context: dict, focus_state: dict) -> str:
    node_lines = []
    edge_lines = []

    for node in context["nodes"]:
        is_focused = (not focus_state["active"]) or (node["node_id"] in focus_state["focused_nodes"])
        fillcolor = node["accent"] if is_focused else "#e5e7eb"
        fontcolor = "white" if is_focused else "#6b7280"
        color = node["accent"] if is_focused else "#cbd5e1"
        penwidth = "2.2" if is_focused else "1.0"

        label = f"{_escape_dot(node['title'])}\\n{_escape_dot(node['subtitle'])}\\n[{_escape_dot(_status_label(node['status']))}]"
        node_lines.append(
            f'"{node["node_id"]}" [label="{label}", shape=box, style="rounded,filled", '
            f'fillcolor="{fillcolor}", color="{color}", fontcolor="{fontcolor}", penwidth={penwidth}, margin="0.18,0.14"];'
        )

    for edge in context["edges"]:
        is_focused = (not focus_state["active"]) or ((edge["from"], edge["to"]) in focus_state["focused_edges"])
        color = "#f59e0b" if focus_state["active"] and is_focused else ("#94a3b8" if is_focused else "#d1d5db")
        penwidth = "2.6" if focus_state["active"] and is_focused else ("1.8" if is_focused else "1.0")
        edge_lines.append(
            f'"{edge["from"]}" -> "{edge["to"]}" [color="{color}", penwidth={penwidth}, arrowsize=0.8];'
        )

    return f"""
digraph ThreadMap {{
    graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.45, ranksep=0.7, splines=true];
    node [fontname="Arial"];
    edge [fontname="Arial"];
    {' '.join(node_lines)}
    {' '.join(edge_lines)}
}}
"""


def _render_focus_detail(context: dict, focus_state: dict, focus_mode: str, focus_value: str) -> None:
    focused_nodes = [
        node for node in context["nodes"]
        if node["node_id"] != "project" and node["node_id"] in focus_state["focused_nodes"]
    ]

    if not focus_state["active"]:
        st.info("전체 흐름 기준입니다. 특정 TAG나 단계를 선택하면 관련 노드만 요약해서 볼 수 있습니다.")
    else:
        st.caption(f"`{focus_state['label']}` 기준으로 연결되는 노드와 근거를 정리했습니다.")

    rows = [
        {
            "구분": node["title"],
            "대표 정보": node["subtitle"],
            "상태": _status_label(node["status"]),
            "설명": node["detail"],
        }
        for node in focused_nodes
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if focus_mode == "TAG 중심 추적":
        _render_tag_trace_detail(context, focus_value)
    elif focus_mode == "단계 중심 추적":
        _render_stage_trace_detail(context, focus_value, focus_state)


def _render_tag_trace_detail(context: dict, focus_value: str) -> None:
    tag_name = focus_value.split(" | ", 1)[-1]
    tag_rows = [row for row in context.get("tag_thread_rows", []) if row["기준 TAG"] == tag_name]

    if not tag_rows:
        st.info("선택한 TAG에 연결된 후속 흐름 정보가 아직 없습니다.")
        return

    stage_order = {"POS": 1, "MODEL": 2, "BOM": 3, "PRODUCTION": 4}
    sorted_rows = sorted(tag_rows, key=lambda row: (stage_order.get(row["단계"], 99), row["연결 대상"]))
    st.markdown("#### TAG 기준 추적")
    st.dataframe(pd.DataFrame(sorted_rows), use_container_width=True, hide_index=True)


def _render_stage_trace_detail(context: dict, focus_value: str, focus_state: dict) -> None:
    focused_edges = [edge for edge in context["edges"] if (edge["from"], edge["to"]) in focus_state["focused_edges"]]
    node_lookup = {node["node_id"]: node["title"] for node in context["nodes"]}

    rows = [
        {
            "출발": node_lookup[edge["from"]],
            "도착": node_lookup[edge["to"]],
            "연결 의미": _describe_edge(edge["from"], edge["to"]),
        }
        for edge in focused_edges
    ]

    st.markdown(f"#### `{focus_value}` 단계 연결")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_node_detail_panel(context: dict, focus_state: dict) -> None:
    focused_nodes = [
        node for node in context["nodes"]
        if node["node_id"] != "project" and node["node_id"] in focus_state["focused_nodes"]
    ]

    if not focused_nodes:
        st.info("상세 패널에 표시할 노드가 없습니다.")
        return

    selected_node_id = st.selectbox(
        "상세 확인 노드",
        options=[node["node_id"] for node in focused_nodes],
        format_func=lambda node_id: next(
            f"{node['title']} ({node['subtitle']})"
            for node in focused_nodes
            if node["node_id"] == node_id
        ),
    )
    selected_node = next(node for node in focused_nodes if node["node_id"] == selected_node_id)

    left_col, right_col = st.columns([1.0, 1.0])
    with left_col:
        with st.container(border=True):
            st.markdown(f"**{selected_node['title']}**")
            st.caption(selected_node["subtitle"])
            st.write(selected_node["detail"])
            st.write(f"- 상태: `{_status_label(selected_node['status'])}`")
            st.write(f"- 노드 ID: `{selected_node['node_id']}`")

    with right_col:
        connection_rows = _build_node_connection_rows(context, selected_node_id)
        related_timeline = _build_related_timeline_rows(context, selected_node_id)
        st.markdown("#### 연결 관계")
        st.dataframe(pd.DataFrame(connection_rows), use_container_width=True, hide_index=True)
        st.markdown("#### 관련 흐름")
        st.dataframe(pd.DataFrame(related_timeline), use_container_width=True, hide_index=True)


def _render_timeline_table(timeline: list[dict]) -> None:
    if not timeline:
        st.info("아직 연결된 이력이 없습니다.")
        return

    rows = [{"흐름": item["label"], "시점": item["date"]} for item in timeline]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_summary_tables(context: dict) -> None:
    summary_col1, summary_col2 = st.columns([1.2, 1])
    with summary_col1:
        rows = [
            {
                "구분": node["title"],
                "현재 상태": _status_label(node["status"]),
                "대표 정보": node["subtitle"],
                "설명": node["detail"],
            }
            for node in context["nodes"]
            if node["node_id"] != "project"
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with summary_col2:
        with st.container(border=True):
            st.markdown("**상태 범례**")
            st.write("- `연결됨`: 현재 프로젝트 기준 결과가 존재함")
            st.write("- `준비됨`: 현재 정보로 바로 생성하거나 저장 가능함")
            st.write("- `대기중`: 앞 단계 결과가 더 필요함")


def _build_focus_state(context: dict, focus_mode: str, focus_value: str) -> dict:
    edges = [(edge["from"], edge["to"]) for edge in context["edges"]]

    if focus_mode == "전체 흐름":
        return {
            "active": False,
            "label": "전체 흐름",
            "focused_nodes": {node["node_id"] for node in context["nodes"]},
            "focused_edges": set(edges),
        }

    if focus_mode == "TAG 중심 추적":
        focused_nodes = _resolve_tag_focus_nodes(context, focus_value)
        return {
            "active": True,
            "label": focus_value,
            "focused_nodes": focused_nodes,
            "focused_edges": {edge for edge in edges if edge[0] in focused_nodes and edge[1] in focused_nodes},
        }

    focused_nodes = _resolve_stage_focus_nodes(context, focus_value)
    return {
        "active": True,
        "label": focus_value,
        "focused_nodes": focused_nodes,
        "focused_edges": {edge for edge in edges if edge[0] in focused_nodes and edge[1] in focused_nodes},
    }


def _resolve_tag_focus_nodes(context: dict, focus_value: str) -> set[str]:
    focused_nodes = {"project", "spec", "tag"}
    tag_name = focus_value.split(" | ", 1)[-1]

    for row in context.get("tag_thread_rows", []):
        if row["기준 TAG"] != tag_name:
            continue
        stage = row["단계"]
        if stage == "POS":
            focused_nodes.add("pos")
        elif stage == "MODEL":
            focused_nodes.update({"model", "dp"})
        elif stage == "BOM":
            focused_nodes.update({"block", "mbom", "wbom"})
        elif stage == "PRODUCTION":
            focused_nodes.update({"wbom", "work"})

    return focused_nodes


def _resolve_stage_focus_nodes(context: dict, focus_value: str) -> set[str]:
    node_lookup = {node["title"]: node["node_id"] for node in context["nodes"]}
    node_id = node_lookup.get(focus_value)
    if not node_id:
        return {node["node_id"] for node in context["nodes"]}

    focused_nodes = {"project", node_id}
    for edge in context["edges"]:
        if edge["from"] == node_id:
            focused_nodes.add(edge["to"])
        if edge["to"] == node_id:
            focused_nodes.add(edge["from"])
    return focused_nodes


def _build_node_connection_rows(context: dict, selected_node_id: str) -> list[dict]:
    node_lookup = {node["node_id"]: node for node in context["nodes"]}
    rows = []

    for edge in context["edges"]:
        if edge["from"] == selected_node_id:
            target = node_lookup[edge["to"]]
            rows.append(
                {
                    "방향": "후속",
                    "연결 노드": target["title"],
                    "대표 정보": target["subtitle"],
                    "의미": _describe_edge(edge["from"], edge["to"]),
                }
            )
        elif edge["to"] == selected_node_id:
            source = node_lookup[edge["from"]]
            rows.append(
                {
                    "방향": "선행",
                    "연결 노드": source["title"],
                    "대표 정보": source["subtitle"],
                    "의미": _describe_edge(edge["from"], edge["to"]),
                }
            )

    return rows


def _build_related_timeline_rows(context: dict, selected_node_id: str) -> list[dict]:
    label_map = {
        "spec": "건조사양서 기준 수립",
        "tag": "TAG 저장",
        "pos": "POS 초안 생성",
        "model": "모델 편집설계 시작",
        "dp": "DP 수립",
        "change": "설계변경 반영",
        "block": "Block Division 확정",
        "mbom": "MBOM 생성",
        "wbom": "WBOM 생성",
        "work": "작업지시서 생성",
    }
    related_label = label_map.get(selected_node_id)
    if not related_label:
        return [{"흐름": "관련 이력 없음", "시점": "-", "비고": "-"}]

    rows = [{"흐름": related_label, "시점": "-", "비고": "아직 저장된 이력 없음"}]
    for item in context["timeline"]:
        if item["label"] == related_label:
            rows = [{"흐름": item["label"], "시점": item["date"], "비고": "직접 관련"}]
            break
    return rows


def _build_tag_options(context: dict) -> list[str]:
    tag_item = context.get("tag_item")
    if not tag_item:
        return []
    return [f"{item['field_name']} | {item['tag_name']}" for item in tag_item.get("tags", [])]


def _describe_edge(source_id: str, target_id: str) -> str:
    edge_labels = {
        ("project", "spec"): "프로젝트 기준 사양 수립",
        ("project", "tag"): "프로젝트 기준 추적 키 부여",
        ("spec", "tag"): "사양 속성 기반 TAG 생성",
        ("tag", "pos"): "TAG 기준 POS 문서 연결",
        ("pos", "model"): "POS 기준 모델 편집설계",
        ("model", "dp"): "모델 설계 기준 DP 수립",
        ("model", "change"): "설계 진행 중 변경관리 연결",
        ("model", "block"): "모델 구조 기준 Block Division",
        ("block", "mbom"): "블록 기준 MBOM 생성",
        ("mbom", "wbom"): "작업 목적 WBOM 생성",
        ("wbom", "work"): "WBOM 기준 작업지시서 생성",
    }
    return edge_labels.get((source_id, target_id), "-")


def _status_label(status: str) -> str:
    labels = {
        "ready": "연결됨",
        "draft": "준비됨",
        "pending": "대기중",
    }
    return labels.get(status, status)


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
