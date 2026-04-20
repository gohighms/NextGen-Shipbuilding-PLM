from __future__ import annotations

import json
from pathlib import Path

from pyvis.network import Network

from src.common.paths import MBOM_DIR, MODEL_DATA_DIR, MODEL_DRAFT_DIR, WBOM_DIR
from src.features.tag_management.tag_generator import generate_tags_from_attributes
from src.features.tag_management.ui import _build_extended_tag_result


NODE_COLORS = {
    "spec": "#3b82f6",
    "pos": "#14b8a6",
    "model": "#22c55e",
    "bom": "#a16207",
}

EDGE_COLORS = {
    "specifies": "#60a5fa",
    "defines": "#2dd4bf",
    "listed_as": "#f59e0b",
    "same_spec_group": "#94a3b8",
    "same_pos_context": "#94a3b8",
    "related_model": "#94a3b8",
    "related_bom": "#94a3b8",
    "project_context": "#64748b",
}

GROUP_ORDER = ["BAS", "DIM", "MAC", "CGO", "HUL", "OUT", "GEN"]


def build_ontology_pyvis_context(current_spec: dict | None, selected_project: dict | None) -> dict:
    if not current_spec or not selected_project:
        return {
            "project_name": "",
            "baseline_project_name": "",
            "tag_count": 0,
            "node_count": 0,
            "edge_count": 0,
            "graph_html": "",
        }

    tag_result = _build_extended_tag_result(
        generate_tags_from_attributes(current_spec.get("attributes", {})),
        current_spec,
        selected_project,
    )
    link_rows = tag_result.get("tag_link_rows", [])
    nodes, edges = _build_ontology_graph_data(link_rows)

    return {
        "project_name": current_spec["project_name"],
        "baseline_project_name": selected_project["project_name"],
        "tag_count": len(tag_result.get("tags", [])),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "graph_html": build_ontology_graph_html(nodes, edges, current_spec["project_name"]),
        "tag_groups": _collect_tag_groups(edges),
    }


def build_supply_chain_tracking_context(current_spec: dict | None, selected_project: dict | None) -> dict:
    project_name = current_spec["project_name"] if current_spec else ""
    base_project_name = selected_project["project_name"] if selected_project else ""

    model_item = _find_latest_by_project(_load_json_dir(MODEL_DRAFT_DIR), project_name, "current_project_name")
    if not model_item:
        model_item = _find_latest_by_project(_load_json_dir(MODEL_DATA_DIR), base_project_name, "source_project_name")

    mbom_item = _find_latest_by_project(_load_json_dir(MBOM_DIR), project_name, "project_name")
    wbom_item = _find_latest_by_project(_load_json_dir(WBOM_DIR), project_name, "project_name")

    nodes: list[dict] = []
    edges: list[dict] = []

    if model_item:
        for row in model_item.get("model_hierarchy", []):
            if row.get("type") != "Part":
                continue

            model_type = str(row.get("model_type", ""))
            allowed_types = {
                "Pipe",
                "Flange",
                "Plate",
                "Stiffener",
                "Valve",
                "Equipment",
                "파이프",
                "플렌지",
                "플레이트",
                "스티프너",
                "밸브",
                "장비",
            }
            if model_type not in allowed_types:
                continue

            nodes.append(
                {
                    "id": f"model::{row.get('node_code', row.get('name', 'MODEL'))}",
                    "label": row.get("name", row.get("node_code", "모델 항목")),
                    "node_type": "Equipment" if model_type in {"Equipment", "장비"} else "MaterialItem",
                    "color": "#22c55e",
                }
            )

    if mbom_item:
        for row in mbom_item.get("mbom_rows", [])[:20]:
            item_code = _pick(row, "항목코드", "item_code") or "MBOM"
            item_name = _pick(row, "항목명", "item_name") or "MBOM 항목"
            nodes.append(
                {
                    "id": f"mbom::{item_code}",
                    "label": item_name,
                    "node_type": "BomItem",
                    "color": "#a16207",
                }
            )

    if wbom_item:
        for row in wbom_item.get("wbom_rows", [])[:20]:
            item_code = _pick(row, "항목코드", "item_code") or "WBOM"
            item_name = _pick(row, "항목명", "item_name") or "WBOM 항목"
            nodes.append(
                {
                    "id": f"wbom::{item_code}",
                    "label": item_name,
                    "node_type": "WorkPackage",
                    "color": "#475569",
                }
            )

    nodes = _dedupe_by_key(nodes, "id")
    node_lookup = {node["id"]: node for node in nodes}

    if mbom_item:
        for row in mbom_item.get("mbom_rows", [])[:20]:
            model_code = _pick(row, "원천 모델", "source_model") or ""
            item_code = _pick(row, "항목코드", "item_code") or "MBOM"
            model_node_id = _find_node_id_by_suffix(node_lookup, model_code)
            bom_node_id = f"mbom::{item_code}"
            if model_node_id and bom_node_id in node_lookup:
                edges.append({"source": model_node_id, "target": bom_node_id, "relation": "listed_as"})

    if wbom_item:
        for row in wbom_item.get("wbom_rows", [])[:20]:
            model_code = _pick(row, "모델ID", "model_id") or ""
            item_code = _pick(row, "항목코드", "item_code") or "WBOM"
            model_node_id = _find_node_id_by_suffix(node_lookup, model_code)
            work_node_id = f"wbom::{item_code}"
            if model_node_id and work_node_id in node_lookup:
                edges.append({"source": model_node_id, "target": work_node_id, "relation": "used_in"})

    traceable_items = [node for node in nodes if node["node_type"] in {"MaterialItem", "Equipment"}]

    return {
        "project_name": project_name or base_project_name,
        "graph": {"nodes": nodes, "edges": edges} if nodes else None,
        "nodes": nodes,
        "edges": edges,
        "node_lookup": node_lookup,
        "traceable_items": traceable_items,
    }


def _build_ontology_graph_data(link_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    nodes_by_id: dict[str, dict] = {}
    edges_by_key: dict[tuple[str, str, str], dict] = {}
    row_contexts: list[dict] = []

    for row in link_rows:
        spec_text = str(_pick(row, "건조사양서 문구") or "").strip()
        pos_text = str(_pick(row, "POS 문구") or "").strip()
        model_name = str(_pick(row, "모델 연결 객체") or "").strip()
        bom_name = str(_pick(row, "BOM 연결 항목") or "").strip()
        tag_name = str(_pick(row, "TAG") or "").strip()
        group = _semantic_group(tag_name)

        spec_id = f"spec::{_slug(spec_text)}"
        pos_id = f"pos::{_slug(pos_text)}"
        model_id = f"model::{_slug(model_name)}"
        bom_id = f"bom::{_slug(bom_name)}"

        nodes_by_id[spec_id] = _make_node(spec_id, _short_label(spec_text, 28), "spec", spec_text)
        nodes_by_id[pos_id] = _make_node(pos_id, _short_label(pos_text, 28), "pos", pos_text)
        nodes_by_id[model_id] = _make_node(model_id, _short_label(model_name, 26), "model", model_name)
        nodes_by_id[bom_id] = _make_node(bom_id, _short_label(bom_name, 26), "bom", bom_name)

        _merge_primary_edge(edges_by_key, spec_id, pos_id, "specifies", tag_name)
        _merge_primary_edge(edges_by_key, pos_id, model_id, "defines", tag_name)
        _merge_primary_edge(edges_by_key, model_id, bom_id, "listed_as", tag_name)

        row_contexts.append(
            {
                "group": group,
                "spec_id": spec_id,
                "pos_id": pos_id,
                "model_id": model_id,
                "bom_id": bom_id,
                "model_cluster": _model_cluster(model_name),
                "bom_cluster": _bom_cluster(bom_name),
            }
        )

    _add_semantic_edges(edges_by_key, row_contexts)
    return list(nodes_by_id.values()), list(edges_by_key.values())


def build_ontology_graph_html(nodes: list[dict], edges: list[dict], project_name: str) -> str:
    network = Network(
        height="860px",
        width="100%",
        bgcolor="#0f1117",
        font_color="#e5e7eb",
        directed=True,
        cdn_resources="in_line",
    )

    for node in nodes:
        network.add_node(
            node["id"],
            label=node["label"],
            title=node["title"],
            color=node["color"],
            shape="dot",
            size=22,
        )

    for edge in edges:
        network.add_edge(
            edge["source"],
            edge["target"],
            label=edge["label"],
            title=edge["title"],
            color=edge["color"],
            arrows="to",
            font={"size": 10, "align": "middle"},
            smooth={"enabled": True, "type": "dynamic"},
        )

    network.set_options(
        """
        {
          "autoResize": true,
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true,
            "tooltipDelay": 100
          },
          "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
              "gravitationalConstant": -70,
              "centralGravity": 0.01,
              "springLength": 180,
              "springConstant": 0.08,
              "damping": 0.6,
              "avoidOverlap": 0.9
            },
            "stabilization": {
              "enabled": true,
              "iterations": 800
            }
          },
          "layout": {
            "improvedLayout": true
          },
          "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 3,
            "font": {
              "color": "#0f172a",
              "face": "Arial",
              "size": 14
            }
          },
          "edges": {
            "width": 2,
            "selectionWidth": 3,
            "color": {
              "inherit": false
            },
            "font": {
              "color": "#e5e7eb",
              "strokeWidth": 0,
              "face": "Arial",
              "size": 11
            }
          }
        }
        """
    )

    html = network.generate_html(notebook=False)
    footer = (
        f"<div style='color:#94a3b8;font-family:Arial;font-size:12px;padding:8px 14px;'>"
        f"프로젝트: {project_name} | 엣지 라벨은 TAG 또는 TAG군이고, 마우스를 올리면 의미 관계를 확인할 수 있습니다."
        f"</div>"
    )
    return html.replace("</body>", footer + "</body>")


def filter_ontology_graph(
    nodes: list[dict],
    edges: list[dict],
    selected_tag_groups: list[str] | None = None,
    selected_node_types: list[str] | None = None,
    density_mode: str = "전체",
) -> tuple[list[dict], list[dict]]:
    selected_tag_groups = selected_tag_groups or []
    selected_node_types = selected_node_types or []

    filtered_edges = list(edges)

    if selected_tag_groups:
        filtered_edges = [
            edge
            for edge in filtered_edges
            if any(group in str(edge.get("label", "")) for group in selected_tag_groups)
            or any(group in str(edge.get("title", "")) for group in selected_tag_groups)
        ]

    if density_mode == "핵심 관계만":
        filtered_edges = [
            edge for edge in filtered_edges if edge.get("relation") in {"specifies", "defines", "listed_as"}
        ]

    visible_node_ids = set()
    for edge in filtered_edges:
        visible_node_ids.add(edge["source"])
        visible_node_ids.add(edge["target"])

    filtered_nodes = [node for node in nodes if node["id"] in visible_node_ids] if visible_node_ids else list(nodes)

    if selected_node_types:
        filtered_nodes = [node for node in filtered_nodes if node.get("node_type_code") in selected_node_types]
        allowed_ids = {node["id"] for node in filtered_nodes}
        filtered_edges = [
            edge for edge in filtered_edges if edge["source"] in allowed_ids and edge["target"] in allowed_ids
        ]

    return filtered_nodes, filtered_edges


def focus_ontology_graph(
    nodes: list[dict],
    edges: list[dict],
    focus_tag: str | None = None,
    hop_mode: str = "전체",
) -> tuple[list[dict], list[dict]]:
    if not focus_tag or focus_tag == "전체":
        return nodes, edges

    seed_edges = [edge for edge in edges if focus_tag in str(edge.get("title", "")) or focus_tag == str(edge.get("label", ""))]
    if not seed_edges:
        return nodes, edges

    if hop_mode == "TAG 경로만":
        visible_ids = set()
        for edge in seed_edges:
            visible_ids.add(edge["source"])
            visible_ids.add(edge["target"])
        focused_nodes = [node for node in nodes if node["id"] in visible_ids]
        return focused_nodes, seed_edges

    visible_ids = set()
    frontier_ids = set()
    for edge in seed_edges:
        visible_ids.add(edge["source"])
        visible_ids.add(edge["target"])
        frontier_ids.add(edge["source"])
        frontier_ids.add(edge["target"])

    expand_rounds = 1 if hop_mode == "1-hop" else 2
    for _ in range(expand_rounds):
        next_frontier = set(frontier_ids)
        for edge in edges:
            if edge["source"] in frontier_ids or edge["target"] in frontier_ids:
                next_frontier.add(edge["source"])
                next_frontier.add(edge["target"])
        visible_ids.update(next_frontier)
        frontier_ids = next_frontier

    focused_nodes = [node for node in nodes if node["id"] in visible_ids]
    focused_edges = [edge for edge in edges if edge["source"] in visible_ids and edge["target"] in visible_ids]
    return focused_nodes, focused_edges


def _make_node(node_id: str, label: str, node_type: str, full_text: str) -> dict:
    titles = {
        "spec": "건조사양서 항목",
        "pos": "POS 항목",
        "model": "모델 객체",
        "bom": "BOM 항목",
    }
    return {
        "id": node_id,
        "label": label,
        "color": NODE_COLORS[node_type],
        "node_type_code": node_type,
        "title": f"{titles[node_type]}<br>{full_text}",
    }


def _merge_primary_edge(edges_by_key: dict[tuple[str, str, str], dict], source: str, target: str, relation: str, tag_name: str) -> None:
    key = (source, target, relation)
    if key not in edges_by_key:
        edges_by_key[key] = {
            "source": source,
            "target": target,
            "relation": relation,
            "tags": [],
            "color": EDGE_COLORS[relation],
        }

    if tag_name and tag_name not in edges_by_key[key]["tags"]:
        edges_by_key[key]["tags"].append(tag_name)

    tags = edges_by_key[key]["tags"]
    label = tags[0] if len(tags) == 1 else f"{tags[0]} 외 {len(tags) - 1}건"

    relation_label = {
        "specifies": "건조사양서가 POS 의미를 규정",
        "defines": "POS가 모델 객체를 규정",
        "listed_as": "모델 객체가 BOM 항목으로 전개",
    }[relation]

    edges_by_key[key]["label"] = label
    edges_by_key[key]["title"] = f"의미 관계: {relation_label}<br>연결 TAG:<br>{'<br>'.join(tags)}"


def _add_semantic_edges(edges_by_key: dict[tuple[str, str, str], dict], row_contexts: list[dict]) -> None:
    spec_by_group: dict[str, list[str]] = {}
    pos_by_group: dict[str, list[str]] = {}
    model_by_cluster: dict[str, list[str]] = {}
    bom_by_cluster: dict[str, list[str]] = {}

    for row in row_contexts:
        spec_by_group.setdefault(row["group"], []).append(row["spec_id"])
        pos_by_group.setdefault(row["group"], []).append(row["pos_id"])
        model_by_cluster.setdefault(row["model_cluster"], []).append(row["model_id"])
        bom_by_cluster.setdefault(row["bom_cluster"], []).append(row["bom_id"])

    for group, node_ids in spec_by_group.items():
        _link_consecutive(edges_by_key, node_ids, "same_spec_group", group, "같은 사양군 문구")

    for group, node_ids in pos_by_group.items():
        _link_consecutive(edges_by_key, node_ids, "same_pos_context", group, "같은 POS 문맥")

    for cluster, node_ids in model_by_cluster.items():
        _link_consecutive(edges_by_key, node_ids, "related_model", cluster, "같은 모델군 객체")

    for cluster, node_ids in bom_by_cluster.items():
        _link_consecutive(edges_by_key, node_ids, "related_bom", cluster, "같은 BOM군 항목")

    representative_groups: list[tuple[str, str]] = []
    for group in GROUP_ORDER:
        if group in spec_by_group:
            representative_groups.append((group, _dedupe_list(spec_by_group[group])[0]))

    for group in sorted(spec_by_group.keys()):
        if group not in [item[0] for item in representative_groups]:
            representative_groups.append((group, _dedupe_list(spec_by_group[group])[0]))

    for index in range(len(representative_groups) - 1):
        current_group, current_node = representative_groups[index]
        next_group, next_node = representative_groups[index + 1]
        _add_semantic_edge(
            edges_by_key,
            current_node,
            next_node,
            "project_context",
            f"{current_group}->{next_group}",
            "같은 프로젝트 내 인접 사양군",
        )


def _link_consecutive(
    edges_by_key: dict[tuple[str, str, str], dict],
    node_ids: list[str],
    relation: str,
    label_text: str,
    relation_text: str,
) -> None:
    deduped_ids = _dedupe_list(node_ids)
    for index in range(len(deduped_ids) - 1):
        _add_semantic_edge(
            edges_by_key,
            deduped_ids[index],
            deduped_ids[index + 1],
            relation,
            label_text,
            relation_text,
        )


def _add_semantic_edge(
    edges_by_key: dict[tuple[str, str, str], dict],
    source: str,
    target: str,
    relation: str,
    label_text: str,
    relation_text: str,
) -> None:
    key = (source, target, relation)
    if key in edges_by_key:
        return

    edges_by_key[key] = {
        "source": source,
        "target": target,
        "relation": relation,
        "tags": [label_text],
        "color": EDGE_COLORS[relation],
        "label": label_text,
        "title": f"의미 관계: {relation_text}<br>연결 TAG군: {label_text}",
    }


def _semantic_group(tag_name: str) -> str:
    parts = str(tag_name).split("-")
    if len(parts) >= 3:
        return parts[2]
    if len(parts) >= 2:
        return parts[1]
    return "GEN"


def _model_cluster(model_name: str) -> str:
    upper = str(model_name).upper()
    for token in ["PIPE", "TANK", "ENGINE", "BED", "PLATE", "BRKT", "GDR", "WEB", "MEM", "INSULATION", "FRAME"]:
        if token in upper:
            return token
    return upper.split()[0] if upper.split() else "MODEL"


def _bom_cluster(bom_name: str) -> str:
    upper = str(bom_name).upper()
    if "BLOCK-" in upper:
        parts = upper.split("-")
        if len(parts) >= 2:
            return parts[1]
    return upper.split()[0] if upper.split() else "BOM"


def _find_latest_by_project(items: list[dict], project_name: str, project_key: str) -> dict | None:
    if not project_name:
        return None
    for item in items:
        if item.get(project_key) == project_name:
            return item
    return None


def _load_json_dir(directory: Path) -> list[dict]:
    items = []
    if not directory.exists():
        return items
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return items


def _find_node_id_by_suffix(node_lookup: dict[str, dict], suffix: str) -> str | None:
    if not suffix:
        return None
    for node_id in node_lookup:
        if node_id.endswith(str(suffix)):
            return node_id
    return None


def _dedupe_by_key(rows: list[dict], key_name: str) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        value = row[key_name]
        if value in seen:
            continue
        seen.add(value)
        deduped.append(row)
    return deduped


def _dedupe_list(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _short_label(text: str, limit: int) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit - 1]}…"


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in str(value)).strip("-")


def _pick(row: dict, *keys: str):
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _collect_tag_groups(edges: list[dict]) -> list[str]:
    groups = set()
    for edge in edges:
        label = str(edge.get("label", ""))
        title = str(edge.get("title", ""))
        for group in GROUP_ORDER:
            if group in label or group in title:
                groups.add(group)
    return [group for group in GROUP_ORDER if group in groups]


def collect_focus_tags(edges: list[dict]) -> list[str]:
    tags = set()
    for edge in edges:
        relation = edge.get("relation")
        if relation not in {"specifies", "defines", "listed_as"}:
            continue
        title = str(edge.get("title", ""))
        if "연결 TAG:<br>" in title:
            tag_block = title.split("연결 TAG:<br>", 1)[1]
            for tag in tag_block.split("<br>"):
                clean = tag.strip()
                if clean:
                    tags.add(clean)
    return sorted(tags)
