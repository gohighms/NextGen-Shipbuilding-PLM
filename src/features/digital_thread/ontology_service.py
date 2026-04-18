from __future__ import annotations

import json
import re

from src.common.paths import MODEL_DATA_DIR, POS_DATA_DIR
from src.features.digital_thread.service import build_project_thread_context


CONCEPT_DEFINITIONS = [
    {
        "concept_id": "Project",
        "label": "프로젝트",
        "category": "관리 객체",
        "description": "전체 디지털 쓰레드의 기준이 되는 최상위 개체",
    },
    {
        "concept_id": "Specification",
        "label": "건조사양서",
        "category": "설계 기준",
        "description": "프로젝트의 출발점이 되는 요구/기준 사양",
    },
    {
        "concept_id": "Tag",
        "label": "TAG",
        "category": "식별/추적",
        "description": "속성과 객체를 프로젝트 전 과정에서 추적하기 위한 공통 식별자",
    },
    {
        "concept_id": "POS",
        "label": "POS",
        "category": "설계 산출물",
        "description": "구매 및 설계 기준이 되는 Purchase Order Specification",
    },
    {
        "concept_id": "Model",
        "label": "모델",
        "category": "설계 산출물",
        "description": "편집설계를 통해 구체화되는 프로젝트 모델 구조",
    },
    {
        "concept_id": "DesignPlan",
        "label": "설계계획",
        "category": "프로젝트 관리",
        "description": "모델 설계를 기준으로 수립되는 DP 일정",
    },
    {
        "concept_id": "DesignChange",
        "label": "설계변경",
        "category": "프로젝트 관리",
        "description": "설계 진행 중 발생하는 변경 요청 및 Rev 관리",
    },
    {
        "concept_id": "BlockDivision",
        "label": "Block Division",
        "category": "생산 준비",
        "description": "모델 구조를 생산 블록 기준으로 재구성하는 단계",
    },
    {
        "concept_id": "MBOM",
        "label": "MBOM",
        "category": "생산 준비",
        "description": "생산 목적의 Manufacturing BOM",
    },
    {
        "concept_id": "WBOM",
        "label": "WBOM",
        "category": "생산 준비",
        "description": "작업 목적의 Work BOM",
    },
    {
        "concept_id": "WorkInstruction",
        "label": "작업지시서",
        "category": "실행",
        "description": "WBOM을 기준으로 생성되는 실행 단위 지시 정보",
    },
]


RELATION_DEFINITIONS = [
    {
        "relation_id": "has_specification",
        "label": "has_specification",
        "source_type": "Project",
        "target_type": "Specification",
        "description": "프로젝트는 기준 건조사양서를 가진다",
    },
    {
        "relation_id": "defines_tag",
        "label": "defines_tag",
        "source_type": "Specification",
        "target_type": "Tag",
        "description": "사양 속성은 TAG를 정의한다",
    },
    {
        "relation_id": "references_pos",
        "label": "references_pos",
        "source_type": "Tag",
        "target_type": "POS",
        "description": "TAG는 연관 POS 기준과 연결된다",
    },
    {
        "relation_id": "drives_model",
        "label": "drives_model",
        "source_type": "POS",
        "target_type": "Model",
        "description": "POS는 모델 편집설계를 이끈다",
    },
    {
        "relation_id": "plans_design",
        "label": "plans_design",
        "source_type": "Model",
        "target_type": "DesignPlan",
        "description": "모델 구조는 설계계획 수립 기준이 된다",
    },
    {
        "relation_id": "impacts_change",
        "label": "impacts_change",
        "source_type": "Model",
        "target_type": "DesignChange",
        "description": "모델은 설계변경 영향 대상이 된다",
    },
    {
        "relation_id": "divides_to_block",
        "label": "divides_to_block",
        "source_type": "Model",
        "target_type": "BlockDivision",
        "description": "모델은 Block Division으로 전환된다",
    },
    {
        "relation_id": "transforms_to_mbom",
        "label": "transforms_to_mbom",
        "source_type": "BlockDivision",
        "target_type": "MBOM",
        "description": "Block Division 결과는 MBOM으로 이어진다",
    },
    {
        "relation_id": "transforms_to_wbom",
        "label": "transforms_to_wbom",
        "source_type": "MBOM",
        "target_type": "WBOM",
        "description": "MBOM은 작업 목적 WBOM으로 확장된다",
    },
    {
        "relation_id": "executes_with_instruction",
        "label": "executes_with_instruction",
        "source_type": "WBOM",
        "target_type": "WorkInstruction",
        "description": "WBOM은 작업지시서로 실행된다",
    },
]


DETAILED_ENTITY_BLUEPRINT = [
    {
        "entity_type": "SpecSection",
        "level": "문서 하위",
        "example": "principal_dimensions, cargo_system",
        "purpose": "건조사양서 내부 섹션 단위로 질의할 수 있게 함",
    },
    {
        "entity_type": "SpecAttribute",
        "level": "속성",
        "example": "loa_m, cargo_capacity_m3, main_engine",
        "purpose": "LLM이 속성 조건 기반으로 검색/비교할 수 있게 함",
    },
    {
        "entity_type": "PosClause",
        "level": "문서 하위",
        "example": "기관부 조항, 화물 시스템 조항",
        "purpose": "POS의 특정 문단과 설계/구매 영향 연결",
    },
    {
        "entity_type": "ModelNode",
        "level": "설계 객체",
        "example": "PIPE-FG-002, PLATE-SS-002",
        "purpose": "모델 구조 노드 단위 영향 추적",
    },
    {
        "entity_type": "Equipment",
        "level": "기자재",
        "example": "Main Engine, Valve, Pump",
        "purpose": "기자재 기준 구매-설계-생산 추적",
    },
    {
        "entity_type": "MaterialItem",
        "level": "자재",
        "example": "Pipe, Flange, Plate, Stiffener",
        "purpose": "자재 단위 BOM과 구매 이력 연결",
    },
    {
        "entity_type": "BomItem",
        "level": "BOM 항목",
        "example": "MBOM line item, WBOM item",
        "purpose": "목적별 BOM 차이를 세부 항목 기준으로 조회",
    },
    {
        "entity_type": "PurchaseItem",
        "level": "구매",
        "example": "PO line, 입고 예정 품목",
        "purpose": "설계 변경 전 구매 현황을 함께 판단",
    },
    {
        "entity_type": "WorkPackage",
        "level": "실행",
        "example": "Block 109 작업 패키지",
        "purpose": "작업지시와 실제 생산 실행을 연결",
    },
    {
        "entity_type": "ChangeTarget",
        "level": "변경 영향",
        "example": "배관용 hole, foundation opening",
        "purpose": "설계변경 영향 대상을 세밀하게 지정",
    },
]


CONCEPT_STYLE = {
    "Project": "#0b7285",
    "Specification": "#11497b",
    "Tag": "#c05621",
    "POS": "#157f8a",
    "Model": "#2f855a",
    "DesignPlan": "#5a67d8",
    "DesignChange": "#dd6b20",
    "BlockDivision": "#805ad5",
    "MBOM": "#718096",
    "WBOM": "#8b6f47",
    "WorkInstruction": "#2d3748",
}


NODE_TO_CONCEPT = {
    "project": "Project",
    "spec": "Specification",
    "tag": "Tag",
    "pos": "POS",
    "model": "Model",
    "dp": "DesignPlan",
    "change": "DesignChange",
    "block": "BlockDivision",
    "mbom": "MBOM",
    "wbom": "WBOM",
    "work": "WorkInstruction",
}


RELATION_BY_EDGE = {
    ("project", "spec"): "has_specification",
    ("spec", "tag"): "defines_tag",
    ("tag", "pos"): "references_pos",
    ("pos", "model"): "drives_model",
    ("model", "dp"): "plans_design",
    ("model", "change"): "impacts_change",
    ("model", "block"): "divides_to_block",
    ("block", "mbom"): "transforms_to_mbom",
    ("mbom", "wbom"): "transforms_to_wbom",
    ("wbom", "work"): "executes_with_instruction",
}


def build_ontology_context(current_spec: dict | None, selected_project: dict | None) -> dict:
    thread_context = build_project_thread_context(current_spec, selected_project)
    instance_nodes = _build_instance_nodes(thread_context)
    instance_edges = _build_instance_edges(thread_context)
    detailed_graphs = _build_detailed_graphs(thread_context, current_spec)

    return {
        "project_name": thread_context["project_name"],
        "thread_context": thread_context,
        "concepts": CONCEPT_DEFINITIONS,
        "relations": RELATION_DEFINITIONS,
        "detailed_entities": DETAILED_ENTITY_BLUEPRINT,
        "instance_nodes": instance_nodes,
        "instance_edges": instance_edges,
        "detailed_graphs": detailed_graphs,
        "concept_graph_dot": _build_concept_graph_dot(CONCEPT_DEFINITIONS, RELATION_DEFINITIONS),
        "instance_graph_dot": _build_instance_graph_dot(instance_nodes, instance_edges),
    }


def build_supply_chain_tracking_context(current_spec: dict | None, selected_project: dict | None) -> dict:
    context = build_ontology_context(current_spec, selected_project)
    supply_graph = next(
        (item for item in context["detailed_graphs"] if item["graph_id"] == "supply_chain_detail"),
        None,
    )
    if not supply_graph:
        return {
            "project_name": context["project_name"],
            "graph": None,
            "traceable_items": [],
        }

    nodes = supply_graph["nodes"]
    edges = supply_graph["edges"]
    node_lookup = {node["id"]: node for node in nodes}
    traceable_items = [
        node for node in nodes
        if node["node_type"] in {"Equipment", "MaterialItem"}
    ]

    return {
        "project_name": context["project_name"],
        "graph": supply_graph,
        "nodes": nodes,
        "edges": edges,
        "node_lookup": node_lookup,
        "traceable_items": traceable_items,
    }


def _build_instance_nodes(thread_context: dict) -> list[dict]:
    concept_lookup = {item["concept_id"]: item for item in CONCEPT_DEFINITIONS}
    nodes = []

    for node in thread_context["nodes"]:
        concept_id = NODE_TO_CONCEPT[node["node_id"]]
        concept = concept_lookup[concept_id]
        nodes.append(
            {
                "instance_id": node["node_id"],
                "label": node["title"],
                "subtitle": node["subtitle"],
                "concept_id": concept_id,
                "concept_label": concept["label"],
                "category": concept["category"],
                "status": _status_label(node["status"]),
                "description": node["detail"],
                "accent": node["accent"],
            }
        )
    return nodes


def _build_instance_edges(thread_context: dict) -> list[dict]:
    rows = []
    node_lookup = {node["node_id"]: node for node in thread_context["nodes"]}
    relation_lookup = {item["relation_id"]: item for item in RELATION_DEFINITIONS}

    for edge in thread_context["edges"]:
        relation_id = RELATION_BY_EDGE.get((edge["from"], edge["to"]))
        if not relation_id:
            continue
        relation = relation_lookup[relation_id]
        rows.append(
            {
                "source_id": edge["from"],
                "source_label": node_lookup[edge["from"]]["title"],
                "relation_id": relation_id,
                "relation_label": relation["label"],
                "target_id": edge["to"],
                "target_label": node_lookup[edge["to"]]["title"],
                "description": relation["description"],
            }
        )
    return rows


def _build_concept_graph_dot(concepts: list[dict], relations: list[dict]) -> str:
    node_lines = []
    edge_lines = []

    for concept in concepts:
        color = CONCEPT_STYLE.get(concept["concept_id"], "#475569")
        label = f"{_escape_dot(concept['label'])}\\n{_escape_dot(concept['category'])}"
        node_lines.append(
            f'"{concept["concept_id"]}" [label="{label}", shape=ellipse, style="filled", '
            f'fillcolor="{color}", color="{color}", fontcolor="white", penwidth=2.2, margin="0.22,0.16"];'
        )

    for relation in relations:
        edge_lines.append(
            f'"{relation["source_type"]}" -> "{relation["target_type"]}" '
            f'[label="{relation["label"]}", color="#64748b", fontcolor="#475569", penwidth=2.0, arrowsize=0.9];'
        )

    return f"""
digraph OntologyConcepts {{
    graph [rankdir=LR, bgcolor="transparent", pad=0.25, nodesep=0.7, ranksep=1.0, splines=true, outputorder=edgesfirst];
    node [fontname="Arial"];
    edge [fontname="Arial"];
    {' '.join(node_lines)}
    {' '.join(edge_lines)}
}}
"""


def _build_instance_graph_dot(nodes: list[dict], edges: list[dict]) -> str:
    node_lines = []
    edge_lines = []

    for node in nodes:
        node_lines.append(
            f'"{node["instance_id"]}" [label="{_escape_dot(node["label"])}\\n{_escape_dot(node["status"])}", '
            f'shape=ellipse, style="filled", fillcolor="{node["accent"]}", color="{node["accent"]}", '
            f'fontcolor="white", penwidth=2.2, margin="0.22,0.16"];'
        )

    for edge in edges:
        edge_lines.append(
            f'"{edge["source_id"]}" -> "{edge["target_id"]}" '
            f'[label="{edge["relation_label"]}", color="#64748b", fontcolor="#475569", penwidth=2.0, arrowsize=0.9];'
        )

    return f"""
digraph OntologyInstances {{
    graph [rankdir=LR, bgcolor="transparent", pad=0.25, nodesep=0.65, ranksep=0.9, splines=true, outputorder=edgesfirst];
    node [fontname="Arial"];
    edge [fontname="Arial"];
    {' '.join(node_lines)}
    {' '.join(edge_lines)}
}}
"""


def _build_detailed_graphs(thread_context: dict, current_spec: dict | None) -> list[dict]:
    graphs = []
    project_name = thread_context["project_name"] or "PROJECT"

    spec_graph = _build_spec_detail_graph(thread_context, current_spec, project_name)
    if spec_graph["nodes"]:
        graphs.append(spec_graph)

    pos_graph = _build_pos_detail_graph(thread_context, project_name)
    if pos_graph["nodes"]:
        graphs.append(pos_graph)

    model_graph = _build_model_detail_graph(thread_context, project_name)
    if model_graph["nodes"]:
        graphs.append(model_graph)

    bom_graph = _build_bom_detail_graph(thread_context, project_name)
    if bom_graph["nodes"]:
        graphs.append(bom_graph)

    supply_graph = _build_supply_chain_detail_graph(thread_context, current_spec, project_name)
    if supply_graph["nodes"]:
        graphs.append(supply_graph)

    return graphs


def _build_spec_detail_graph(thread_context: dict, current_spec: dict | None, project_name: str) -> dict:
    tag_item = thread_context.get("tag_item") or {}
    attributes = {}
    if current_spec:
        attributes = current_spec.get("attributes", {})
    if not attributes:
        attributes = tag_item.get("attributes", {})
    if not attributes:
        return {"graph_id": "spec_detail", "title": "건조사양서 세부 그래프", "nodes": [], "edges": [], "dot": ""}

    nodes = []
    edges = []
    root_id = "spec_root"
    nodes.append(_detail_node(root_id, f"{project_name} 건조사양서", "Specification", "#11497b"))

    for section_name, section_values in attributes.items():
        section_id = f"spec_section_{_slug(section_name)}"
        nodes.append(_detail_node(section_id, section_name, "SpecSection", "#315d8a"))
        edges.append(_detail_edge(root_id, section_id, "has_section"))

        if isinstance(section_values, dict):
            for field_name, field_value in section_values.items():
                field_id = f"{section_id}_{_slug(field_name)}"
                label = f"{field_name}: {field_value}"
                nodes.append(_detail_node(field_id, label, "SpecAttribute", "#4b7fb0"))
                edges.append(_detail_edge(section_id, field_id, "has_attribute"))

    return {
        "graph_id": "spec_detail",
        "title": "건조사양서 세부 그래프",
        "nodes": nodes,
        "edges": edges,
        "dot": _build_detailed_graph_dot("SpecDetail", nodes, edges),
    }


def _build_pos_detail_graph(thread_context: dict, project_name: str) -> dict:
    pos_title = next((node["subtitle"] for node in thread_context["nodes"] if node["node_id"] == "pos"), "POS")
    pos_sections = []
    pos_item = thread_context.get("pos_item")
    if not pos_item:
        pos_item = _load_source_item(POS_DATA_DIR, "source_project_name", thread_context.get("base_project_name"))
    if pos_item:
        pos_sections = pos_item.get("sections", [])

    if not pos_sections:
        return {"graph_id": "pos_detail", "title": "POS 세부 그래프", "nodes": [], "edges": [], "dot": ""}

    nodes = []
    edges = []
    root_id = "pos_root"
    nodes.append(_detail_node(root_id, pos_title, "POS", "#157f8a"))

    for index, section in enumerate(pos_sections, start=1):
        section_name = section.get("section", f"section_{index}")
        section_id = f"pos_clause_{index}"
        nodes.append(_detail_node(section_id, section_name, "PosClause", "#2b97a2"))
        edges.append(_detail_edge(root_id, section_id, "has_clause"))

        content = section.get("content", "")
        for sentence_index, chunk in enumerate(_split_text(content, 2), start=1):
            chunk_id = f"{section_id}_{sentence_index}"
            nodes.append(_detail_node(chunk_id, chunk, "ClauseChunk", "#63b3bf"))
            edges.append(_detail_edge(section_id, chunk_id, "contains_text"))

    return {
        "graph_id": "pos_detail",
        "title": "POS 세부 그래프",
        "nodes": nodes,
        "edges": edges,
        "dot": _build_detailed_graph_dot("PosDetail", nodes, edges),
    }


def _build_model_detail_graph(thread_context: dict, project_name: str) -> dict:
    model_item = thread_context.get("model_item")
    if not model_item:
        model_item = _load_source_item(MODEL_DATA_DIR, "source_project_name", thread_context.get("base_project_name"))
    hierarchy = model_item.get("model_hierarchy", []) if model_item else []
    if not hierarchy:
        return {"graph_id": "model_detail", "title": "모델 세부 그래프", "nodes": [], "edges": [], "dot": ""}

    nodes = []
    edges = []
    root_id = "model_root"
    nodes.append(_detail_node(root_id, f"{project_name} 모델", "Model", "#2f855a"))

    for item in hierarchy[:30]:
        path = item.get("path", "")
        parent_path = "/".join(path.split("/")[:-1])
        node_id = f"model_{_slug(path)}"
        node_name = item.get("name", path.split("/")[-1])
        model_type = item.get("model_type", item.get("type", "ModelNode"))
        nodes.append(_detail_node(node_id, node_name, model_type, "#48a36f"))

        if "PROJECT/" in parent_path:
            parent_id = f"model_{_slug(parent_path)}"
            if not any(node["id"] == parent_id for node in nodes):
                parent_name = parent_path.split("/")[-1]
                nodes.append(_detail_node(parent_id, parent_name, "ModelGroup", "#3a9463"))
                edges.append(_detail_edge(root_id, parent_id, "contains"))
            edges.append(_detail_edge(parent_id, node_id, "contains"))
        else:
            edges.append(_detail_edge(root_id, node_id, "contains"))

    return {
        "graph_id": "model_detail",
        "title": "모델 세부 그래프",
        "nodes": _dedupe_nodes(nodes),
        "edges": edges,
        "dot": _build_detailed_graph_dot("ModelDetail", _dedupe_nodes(nodes), edges),
    }


def _build_bom_detail_graph(thread_context: dict, project_name: str) -> dict:
    nodes = []
    edges = []
    root_id = "bom_root"

    mbom_item = thread_context.get("mbom_item")
    wbom_item = thread_context.get("wbom_item")

    if not mbom_item and not wbom_item:
        return {"graph_id": "bom_detail", "title": "BOM 세부 그래프", "nodes": [], "edges": [], "dot": ""}

    nodes.append(_detail_node(root_id, f"{project_name} BOM", "BomRoot", "#718096"))

    if mbom_item:
        mbom_root = "mbom_root"
        nodes.append(_detail_node(mbom_root, mbom_item.get("title", "MBOM"), "MBOM", "#718096"))
        edges.append(_detail_edge(root_id, mbom_root, "has_mbom"))
        for index, row in enumerate(mbom_item.get("mbom_rows", [])[:10], start=1):
            item_id = f"mbom_item_{index}"
            label = row.get("품목", row.get("item_name", f"MBOM Item {index}"))
            nodes.append(_detail_node(item_id, label, "BomItem", "#8a9aad"))
            edges.append(_detail_edge(mbom_root, item_id, "contains_item"))

    if wbom_item:
        wbom_root = "wbom_root"
        nodes.append(_detail_node(wbom_root, wbom_item.get("title", "WBOM"), "WBOM", "#8b6f47"))
        edges.append(_detail_edge(root_id, wbom_root, "has_wbom"))
        for index, row in enumerate(wbom_item.get("wbom_rows", [])[:10], start=1):
            item_id = f"wbom_item_{index}"
            label = row.get("작업 항목", row.get("item_name", f"WBOM Item {index}"))
            nodes.append(_detail_node(item_id, label, "WorkItem", "#a38863"))
            edges.append(_detail_edge(wbom_root, item_id, "contains_item"))

    deduped_nodes = _dedupe_nodes(nodes)
    return {
        "graph_id": "bom_detail",
        "title": "BOM 세부 그래프",
        "nodes": deduped_nodes,
        "edges": edges,
        "dot": _build_detailed_graph_dot("BomDetail", deduped_nodes, edges),
    }


def _build_supply_chain_detail_graph(
    thread_context: dict,
    current_spec: dict | None,
    project_name: str,
) -> dict:
    model_item = thread_context.get("model_item")
    if not model_item:
        model_item = _load_source_item(MODEL_DATA_DIR, "source_project_name", thread_context.get("base_project_name"))

    hierarchy = model_item.get("model_hierarchy", []) if model_item else []
    attributes = current_spec.get("attributes", {}) if current_spec else {}
    if not hierarchy and not attributes:
        return {"graph_id": "supply_chain_detail", "title": "구매-설계-생산 추적 그래프", "nodes": [], "edges": [], "dot": ""}

    nodes = []
    edges = []

    root_id = "supply_root"
    nodes.append(_detail_node(root_id, f"{project_name} 구매-설계-생산", "LifecycleThread", "#0f766e"))

    equipment_root = "equipment_root"
    material_root = "material_root"
    purchase_root = "purchase_root"
    work_root = "work_root"
    nodes.extend(
        [
            _detail_node(equipment_root, "기자재", "EquipmentGroup", "#0e7490"),
            _detail_node(material_root, "자재", "MaterialGroup", "#4f46e5"),
            _detail_node(purchase_root, "구매 항목", "PurchaseGroup", "#b45309"),
            _detail_node(work_root, "생산/작업", "WorkPackageGroup", "#475569"),
        ]
    )
    edges.extend(
        [
            _detail_edge(root_id, equipment_root, "tracks"),
            _detail_edge(root_id, material_root, "tracks"),
            _detail_edge(root_id, purchase_root, "tracks"),
            _detail_edge(root_id, work_root, "tracks"),
        ]
    )

    equipment_names = []
    machinery = attributes.get("machinery", {})
    cargo_system = attributes.get("cargo_system", {})
    if machinery.get("main_engine"):
        equipment_names.append(("EQ_MAIN_ENGINE", f"Main Engine {machinery['main_engine']}"))
    if cargo_system.get("cargo_tank_system"):
        equipment_names.append(("EQ_CARGO_SYSTEM", cargo_system["cargo_tank_system"]))
    equipment_names.append(("EQ_FGSS", "FGSS Package"))

    for code, label in equipment_names[:3]:
        equipment_id = _slug(code)
        purchase_id = f"po_{equipment_id}"
        work_id = f"wk_{equipment_id}"
        nodes.extend(
            [
                _detail_node(equipment_id, label, "Equipment", "#0891b2"),
                _detail_node(purchase_id, f"PO {label}", "PurchaseItem", "#d97706"),
                _detail_node(work_id, f"{label} 설치", "WorkPackage", "#64748b"),
            ]
        )
        edges.extend(
            [
                _detail_edge(equipment_root, equipment_id, "contains"),
                _detail_edge(equipment_id, purchase_id, "purchased_as"),
                _detail_edge(equipment_id, work_id, "installed_in"),
                _detail_edge(purchase_id, work_id, "released_to"),
                _detail_edge(purchase_root, purchase_id, "manages"),
                _detail_edge(work_root, work_id, "executes"),
            ]
        )

    material_map = []
    part_lookup = {}
    for row in hierarchy:
        if row.get("type") != "Part":
            continue
        model_type = row.get("model_type", "")
        if model_type not in part_lookup:
            part_lookup[model_type] = row

    for model_type, row in part_lookup.items():
        if model_type in {"플레이트", "스티프너", "파이프", "플렌지"}:
            material_map.append((model_type, row.get("name", model_type), row.get("node_code", model_type)))

    for model_type, name, code in material_map[:4]:
        material_id = f"mat_{_slug(code)}"
        bom_id = f"bom_{_slug(code)}"
        purchase_id = f"po_mat_{_slug(code)}"
        work_id = f"wk_mat_{_slug(code)}"
        nodes.extend(
            [
                _detail_node(material_id, f"{name}", "MaterialItem", "#6366f1"),
                _detail_node(bom_id, f"{model_type} BOM", "BomItem", "#818cf8"),
                _detail_node(purchase_id, f"{name} 구매", "PurchaseItem", "#f59e0b"),
                _detail_node(work_id, f"{name} 제작/설치", "WorkPackage", "#94a3b8"),
            ]
        )
        edges.extend(
            [
                _detail_edge(material_root, material_id, "contains"),
                _detail_edge(material_id, bom_id, "listed_as"),
                _detail_edge(material_id, purchase_id, "purchased_as"),
                _detail_edge(bom_id, work_id, "issued_to"),
                _detail_edge(purchase_id, work_id, "available_for"),
                _detail_edge(purchase_root, purchase_id, "manages"),
                _detail_edge(work_root, work_id, "executes"),
            ]
        )

    deduped_nodes = _dedupe_nodes(nodes)
    return {
        "graph_id": "supply_chain_detail",
        "title": "구매-설계-생산 추적 그래프",
        "nodes": deduped_nodes,
        "edges": edges,
        "dot": _build_detailed_graph_dot("SupplyChainDetail", deduped_nodes, edges),
    }


def _build_detailed_graph_dot(graph_name: str, nodes: list[dict], edges: list[dict]) -> str:
    node_lines = []
    edge_lines = []

    for node in nodes:
        node_lines.append(
            f'"{node["id"]}" [label="{_escape_dot(node["label"])}\\n{_escape_dot(node["node_type"])}", '
            f'shape=ellipse, style="filled", fillcolor="{node["color"]}", color="{node["color"]}", '
            f'fontcolor="white", penwidth=2.0, margin="0.22,0.16"];'
        )

    for edge in edges:
        edge_lines.append(
            f'"{edge["source"]}" -> "{edge["target"]}" '
            f'[label="{_escape_dot(edge["relation"])}", color="#64748b", fontcolor="#475569", penwidth=1.8, arrowsize=0.85];'
        )

    return f"""
digraph {graph_name} {{
    graph [rankdir=LR, bgcolor="transparent", pad=0.25, nodesep=0.7, ranksep=1.0, splines=true, outputorder=edgesfirst];
    node [fontname="Arial"];
    edge [fontname="Arial"];
    {' '.join(node_lines)}
    {' '.join(edge_lines)}
}}
"""


def _detail_node(node_id: str, label: str, node_type: str, color: str) -> dict:
    return {
        "id": node_id,
        "label": str(label),
        "node_type": node_type,
        "color": color,
    }


def _detail_edge(source: str, target: str, relation: str) -> dict:
    return {"source": source, "target": target, "relation": relation}


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def _split_text(text: str, limit: int) -> list[str]:
    parts = [chunk.strip() for chunk in str(text).split(".") if chunk.strip()]
    return parts[:limit]


def _dedupe_nodes(nodes: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for node in nodes:
        if node["id"] in seen:
            continue
        seen.add(node["id"])
        deduped.append(node)
    return deduped


def _load_source_item(directory, key: str, value: str | None) -> dict | None:
    if not value or value == "-":
        return None

    for path in sorted(directory.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if item.get(key) == value:
            return item
    return None


def _status_label(status: str) -> str:
    labels = {
        "ready": "연결됨",
        "draft": "준비됨",
        "pending": "대기중",
    }
    return labels.get(status, status)


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
