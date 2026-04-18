from __future__ import annotations

from datetime import datetime

from src.common.paths import (
    BLOCK_DIVISION_DIR,
    DESIGN_CHANGE_DIR,
    MBOM_DIR,
    MODEL_DRAFT_DIR,
    POS_DRAFT_DIR,
    TAG_REGISTRY_DIR,
    WBOM_DIR,
    WORK_INSTRUCTION_DIR,
)
from src.features.bom_management.mbom_repository import MbomRepository
from src.features.bom_management.repository import BlockDivisionRepository
from src.features.bom_management.wbom_repository import WbomRepository
from src.features.bom_management.work_instruction_repository import WorkInstructionRepository
from src.features.design_change_management.repository import DesignChangeRepository
from src.features.design_plan_management.service import build_dp_schedule
from src.features.model_generation.draft_repository import ModelDraftRepository
from src.features.pos_generation.draft_repository import PosDraftRepository
from src.features.tag_management.registry_repository import TagRegistryRepository
from src.features.tag_management.thread_mapper import build_thread_rows


NODE_LAYOUT = {
    "project": {"x": 650, "y": 24, "w": 220, "h": 92},
    "spec": {"x": 52, "y": 182, "w": 220, "h": 110},
    "tag": {"x": 312, "y": 182, "w": 220, "h": 110},
    "pos": {"x": 572, "y": 182, "w": 220, "h": 110},
    "model": {"x": 832, "y": 182, "w": 220, "h": 110},
    "dp": {"x": 1092, "y": 108, "w": 220, "h": 110},
    "change": {"x": 1092, "y": 256, "w": 220, "h": 110},
    "block": {"x": 832, "y": 404, "w": 220, "h": 110},
    "mbom": {"x": 1092, "y": 404, "w": 220, "h": 110},
    "wbom": {"x": 1092, "y": 552, "w": 220, "h": 110},
    "work": {"x": 1352, "y": 552, "w": 220, "h": 110},
}


def build_project_thread_context(current_spec: dict | None, selected_project: dict | None) -> dict:
    project_name = _resolve_project_name(current_spec, selected_project)
    base_project_name = selected_project["project_name"] if selected_project else "-"

    tag_repository = TagRegistryRepository(TAG_REGISTRY_DIR)
    pos_repository = PosDraftRepository(POS_DRAFT_DIR)
    model_repository = ModelDraftRepository(MODEL_DRAFT_DIR)
    design_change_repository = DesignChangeRepository(DESIGN_CHANGE_DIR)
    block_repository = BlockDivisionRepository(BLOCK_DIVISION_DIR)
    mbom_repository = MbomRepository(MBOM_DIR)
    wbom_repository = WbomRepository(WBOM_DIR)
    work_instruction_repository = WorkInstructionRepository(WORK_INSTRUCTION_DIR)

    tag_item = _find_latest_tag_registry(tag_repository.list_all(), current_spec, project_name)
    pos_item = _find_latest_by_project(pos_repository.list_all(), project_name, "current_project_name")
    model_item = _find_latest_by_project(model_repository.list_all(), project_name, "current_project_name")
    design_change_item = _find_latest_by_project(design_change_repository.list_all(), project_name, "project_name")
    block_item = _find_latest_by_project(block_repository.list_all(), project_name, "project_name")
    mbom_item = _find_latest_by_project(mbom_repository.list_all(), project_name, "project_name")
    wbom_item = _find_latest_by_project(wbom_repository.list_all(), project_name, "project_name")
    work_item = _find_latest_by_project(work_instruction_repository.list_all(), project_name, "project_name")

    dp_rows = build_dp_schedule(project_name) if project_name else []

    nodes = [
        _project_node(project_name, base_project_name),
        _node(
            node_id="spec",
            title="건조사양서",
            subtitle=current_spec["project_name"] if current_spec else "현재 프로젝트 미선정",
            detail=_spec_detail(current_spec, selected_project),
            accent="#11497b",
            status="ready" if current_spec or selected_project else "pending",
            badge="SPEC",
        ),
        _node(
            node_id="tag",
            title="TAG",
            subtitle=tag_item["registry_id"] if tag_item else "저장된 TAG 없음",
            detail=_tag_detail(tag_item, current_spec),
            accent="#c05621",
            status="ready" if tag_item else ("draft" if current_spec else "pending"),
            badge="TAG",
        ),
        _node(
            node_id="pos",
            title="POS",
            subtitle=_pick_value(pos_item, "new_pos_id", "draft_id", default="POS 초안 없음"),
            detail=_pos_detail(pos_item),
            accent="#157f8a",
            status="ready" if pos_item else "pending",
            badge="POS",
        ),
        _node(
            node_id="model",
            title="모델",
            subtitle=_pick_value(model_item, "new_model_id", "draft_id", default="모델 초안 없음"),
            detail=_model_detail(model_item),
            accent="#2f855a",
            status="ready" if model_item else "pending",
            badge="MODEL",
        ),
        _node(
            node_id="dp",
            title="설계계획(DP)",
            subtitle=f"Key Event {len(dp_rows)}건" if dp_rows else "DP 미구성",
            detail=_dp_detail(dp_rows),
            accent="#5a67d8",
            status="ready" if dp_rows else "pending",
            badge="DP",
        ),
        _node(
            node_id="change",
            title="설계변경",
            subtitle=_pick_value(design_change_item, "request_id", default="변경 이력 없음"),
            detail=_change_detail(design_change_item),
            accent="#dd6b20",
            status="ready" if design_change_item else "pending",
            badge="ECR",
        ),
        _node(
            node_id="block",
            title="Block Division",
            subtitle=_pick_value(block_item, "division_id", default="Block Division 없음"),
            detail=_block_detail(block_item),
            accent="#805ad5",
            status="ready" if block_item else "pending",
            badge="BLOCK",
        ),
        _node(
            node_id="mbom",
            title="MBOM",
            subtitle=_pick_value(mbom_item, "mbom_id", default="MBOM 없음"),
            detail=_mbom_detail(mbom_item),
            accent="#718096",
            status="ready" if mbom_item else "pending",
            badge="MBOM",
        ),
        _node(
            node_id="wbom",
            title="WBOM",
            subtitle=_pick_value(wbom_item, "wbom_id", default="WBOM 없음"),
            detail=_wbom_detail(wbom_item),
            accent="#8b6f47",
            status="ready" if wbom_item else "pending",
            badge="WBOM",
        ),
        _node(
            node_id="work",
            title="작업지시서",
            subtitle=_pick_value(work_item, "instruction_id", default="지시서 없음"),
            detail=_work_detail(work_item),
            accent="#2d3748",
            status="ready" if work_item else "pending",
            badge="WORK",
        ),
    ]

    timeline = _build_timeline(
        current_spec=current_spec,
        tag_item=tag_item,
        pos_item=pos_item,
        model_item=model_item,
        design_change_item=design_change_item,
        block_item=block_item,
        mbom_item=mbom_item,
        wbom_item=wbom_item,
        work_item=work_item,
        has_dp=bool(dp_rows),
    )

    active_nodes = sum(1 for node in nodes if node["status"] != "pending")
    latest_event = timeline[-1]["label"] if timeline else "-"

    return {
        "project_name": project_name,
        "base_project_name": base_project_name,
        "nodes": nodes,
        "edges": _build_edges(),
        "timeline": timeline,
        "active_nodes": active_nodes,
        "latest_event": latest_event,
        "dp_count": len(dp_rows),
        "tag_item": tag_item,
        "pos_item": pos_item,
        "model_item": model_item,
        "design_change_item": design_change_item,
        "block_item": block_item,
        "mbom_item": mbom_item,
        "wbom_item": wbom_item,
        "work_item": work_item,
        "tag_thread_rows": build_thread_rows(tag_item["tags"]) if tag_item else [],
    }


def _project_node(project_name: str, base_project_name: str) -> dict:
    return {
        "node_id": "project",
        "title": project_name or "프로젝트 미선정",
        "subtitle": "Project Thread Anchor",
        "detail": f"기준 실적선: {base_project_name}",
        "accent": "#0b7285",
        "status": "ready" if project_name else "pending",
        "badge": "PROJECT",
        **NODE_LAYOUT["project"],
    }


def _node(
    node_id: str,
    title: str,
    subtitle: str,
    detail: str,
    accent: str,
    status: str,
    badge: str,
) -> dict:
    return {
        "node_id": node_id,
        "title": title,
        "subtitle": subtitle,
        "detail": detail,
        "accent": accent,
        "status": status,
        "badge": badge,
        **NODE_LAYOUT[node_id],
    }


def _resolve_project_name(current_spec: dict | None, selected_project: dict | None) -> str:
    if current_spec:
        return current_spec["project_name"]
    if selected_project:
        return selected_project["project_name"]
    return ""


def _find_latest_by_project(items: list[dict], project_name: str, project_key: str) -> dict | None:
    if not project_name:
        return None
    for item in items:
        if item.get(project_key) == project_name:
            return item
    return None


def _find_latest_tag_registry(items: list[dict], current_spec: dict | None, project_name: str) -> dict | None:
    if current_spec:
        for item in items:
            if item.get("attributes", {}) == current_spec.get("attributes", {}):
                return item

    for item in items:
        if item.get("source_name") == project_name:
            return item

    return items[0] if items else None


def _spec_detail(current_spec: dict | None, selected_project: dict | None) -> str:
    if current_spec:
        return f"현재 프로젝트 사양 확정 / 기준 실적선 {selected_project['project_name'] if selected_project else '-'}"
    if selected_project:
        return f"유사 프로젝트 {selected_project['spec_id']} 선택됨"
    return "건조사양서 비교 결과가 아직 없습니다."


def _tag_detail(tag_item: dict | None, current_spec: dict | None) -> str:
    if tag_item:
        return f"TAG {tag_item['tag_count']}건 / 저장 기준 {tag_item['source_name']}"
    if current_spec:
        return "현재 프로젝트 속성으로 TAG 생성 가능"
    return "TAG 연결 정보를 만들려면 먼저 프로젝트 기준이 필요합니다."


def _pos_detail(pos_item: dict | None) -> str:
    if not pos_item:
        return "유사 프로젝트 POS를 편집설계하면 이 노드가 연결됩니다."
    return f"기준 POS {pos_item.get('based_on_pos_id', '-')} / Change Note 반영"


def _model_detail(model_item: dict | None) -> str:
    if not model_item:
        return "POS 이후 모델 편집설계를 진행하면 연결됩니다."
    hierarchy_count = len(model_item.get("model_hierarchy", []))
    return f"재활용 모델 {model_item.get('based_on_model_id', '-')} / 구조 {hierarchy_count}개"


def _dp_detail(dp_rows: list[dict]) -> str:
    if not dp_rows:
        return "프로젝트 기준 계획 정보가 없습니다."
    return f"{dp_rows[0]['key_event']} ~ {dp_rows[-1]['key_event']}"


def _change_detail(change_item: dict | None) -> str:
    if not change_item:
        return "설계 진행 중 변경 요청이 발생하면 이력이 쌓입니다."
    title = change_item.get("change_title") or change_item.get("title") or "변경 요청"
    rev = change_item.get("target_revision", change_item.get("next_revision", "Rev.01"))
    return f"{title} / {rev}"


def _block_detail(block_item: dict | None) -> str:
    if not block_item:
        return "모델 구조를 기준으로 Block Division이 확정되면 연결됩니다."
    block_count = len(block_item.get("block_rows", []))
    return f"Logical Block {block_count}건 / {block_item.get('source_model_id', '-')}"


def _mbom_detail(mbom_item: dict | None) -> str:
    if not mbom_item:
        return "Block Division 이후 MBOM View가 생성됩니다."
    row_count = len(mbom_item.get("mbom_rows", []))
    return f"MBOM 항목 {row_count}건 / 기준 {mbom_item.get('source_division_id', '-')}"


def _wbom_detail(wbom_item: dict | None) -> str:
    if not wbom_item:
        return "작업 목적 View가 생성되면 연결됩니다."
    row_count = len(wbom_item.get("wbom_rows", []))
    return f"WBOM 항목 {row_count}건 / 기준 {wbom_item.get('source_mbom_id', '-')}"


def _work_detail(work_item: dict | None) -> str:
    if not work_item:
        return "작업 패키지와 지시서가 준비되면 연결됩니다."
    row_count = len(work_item.get("instruction_rows", []))
    return f"작업 패키지 {row_count}건 / 기준 {work_item.get('source_wbom_id', '-')}"


def _pick_value(item: dict | None, *keys: str, default: str) -> str:
    if not item:
        return default
    for key in keys:
        value = item.get(key)
        if value:
            return str(value)
    return default


def _build_timeline(**items: dict) -> list[dict]:
    timeline = []

    if items.get("current_spec"):
        timeline.append({"label": "건조사양서 기준 수립", "date": "현재 세션", "accent": "#11497b"})

    tag_item = items.get("tag_item")
    if tag_item:
        timeline.append({"label": "TAG 저장", "date": tag_item["saved_at"], "accent": "#c05621"})

    pos_item = items.get("pos_item")
    if pos_item:
        timeline.append({"label": "POS 초안 생성", "date": pos_item["saved_at"], "accent": "#157f8a"})

    model_item = items.get("model_item")
    if model_item:
        timeline.append({"label": "모델 편집설계 시작", "date": model_item["saved_at"], "accent": "#2f855a"})

    if items.get("has_dp"):
        timeline.append({"label": "DP 수립", "date": "계획 기준", "accent": "#5a67d8"})

    design_change_item = items.get("design_change_item")
    if design_change_item:
        timeline.append({"label": "설계변경 반영", "date": design_change_item["saved_at"], "accent": "#dd6b20"})

    block_item = items.get("block_item")
    if block_item:
        timeline.append({"label": "Block Division 확정", "date": block_item["saved_at"], "accent": "#805ad5"})

    mbom_item = items.get("mbom_item")
    if mbom_item:
        timeline.append({"label": "MBOM 생성", "date": mbom_item["saved_at"], "accent": "#718096"})

    wbom_item = items.get("wbom_item")
    if wbom_item:
        timeline.append({"label": "WBOM 생성", "date": wbom_item["saved_at"], "accent": "#8b6f47"})

    work_item = items.get("work_item")
    if work_item:
        timeline.append({"label": "작업지시서 생성", "date": work_item["saved_at"], "accent": "#2d3748"})

    return sorted(timeline, key=_timeline_sort_key)


def _timeline_sort_key(item: dict) -> datetime:
    try:
        return datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.max


def _build_edges() -> list[dict]:
    return [
        {"from": "project", "to": "spec"},
        {"from": "project", "to": "tag"},
        {"from": "spec", "to": "tag"},
        {"from": "tag", "to": "pos"},
        {"from": "pos", "to": "model"},
        {"from": "model", "to": "dp"},
        {"from": "model", "to": "change"},
        {"from": "model", "to": "block"},
        {"from": "block", "to": "mbom"},
        {"from": "mbom", "to": "wbom"},
        {"from": "wbom", "to": "work"},
    ]
