def find_pos_documents_for_project(selected_project: dict, pos_items: list[dict]) -> list[dict]:
    spec_id = selected_project.get("spec_id")
    matched_items = [item for item in pos_items if item.get("source_spec_id") == spec_id]
    matched_items.sort(key=lambda item: item["pos_id"])
    return matched_items


def build_pos_draft(current_spec: dict, selected_project: dict, pos_item: dict) -> dict:
    current_project_name = current_spec["project_name"]
    draft_key = _slugify(current_project_name)

    return {
        "new_pos_id": f"POS-{draft_key}-001",
        "source_project_spec_id": selected_project["spec_id"],
        "source_project_name": selected_project["project_name"],
        "current_project_name": current_project_name,
        "current_project_attributes": current_spec.get("attributes", {}),
        "based_on_pos_id": pos_item["pos_id"],
        "title": f"{current_project_name} POS 편집 초안",
        "department": pos_item["department"],
        "sections": pos_item["sections"],
    }


def build_pos_document_text(pos_item: dict, change_note: str = "") -> str:
    if pos_item.get("document_text") and not pos_item.get("_force_regenerate") and not change_note:
        return pos_item["document_text"]

    document_id = pos_item.get("pos_id", pos_item.get("new_pos_id", "-"))
    lines = [
        "PURCHASE ORDER SPECIFICATION",
        "",
        f"Document ID : {document_id}",
        f"Title       : {pos_item.get('title', '-')}",
        f"Department  : {pos_item.get('department', '-')}",
        "",
        "1. General",
        "This specification defines the reusable purchase basis and edit-design scope for the current project.",
        "",
    ]

    for index, section in enumerate(pos_item.get("sections", []), start=2):
        lines.append(f"{index}. {section['section']}")
        lines.append(section["content"])
        lines.append("")

    if change_note:
        lines.append("Change Note")
        lines.append(change_note)
        lines.append("")

    return "\n".join(lines).strip()


def build_pos_edit_direction(section_name: str, current_attributes: dict) -> str:
    flat_attributes = {}
    for group_name, values in current_attributes.items():
        if isinstance(values, dict):
            for key, value in values.items():
                flat_attributes[f"{group_name}.{key}"] = value

    if section_name == "주요치수" and any(key.startswith("principal_dimensions.") for key in flat_attributes):
        return "현재 프로젝트의 주요치수 변경 여부를 확인해 본문을 조정합니다."
    if section_name == "기관" and "machinery.main_engine" in flat_attributes:
        return "주기관과 추진 관련 조건을 현재 사양 기준으로 다시 정리합니다."
    if section_name == "화물시스템" and any(key.startswith("cargo_system.") for key in flat_attributes):
        return "화물창 용적과 화물 시스템 차이를 반영해 문구를 보완합니다."
    return "기준 POS 내용을 유지하되 현재 프로젝트 차이가 있는 부분만 편집합니다."


def _slugify(value: str) -> str:
    cleaned = value.upper().replace(" ", "")
    return "".join(char for char in cleaned if char.isalnum())
