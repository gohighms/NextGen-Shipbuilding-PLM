def recommend_pos_documents(registry_item: dict, pos_items: list[dict], top_k: int = 3) -> list[dict]:
    registry_tags = {item["tag_name"] for item in registry_item["tags"]}
    scored = []

    for pos_item in pos_items:
        pos_tags = set(pos_item.get("tags", []))
        matched_tags = sorted(registry_tags & pos_tags)
        score = len(matched_tags)
        scored.append(
            {
                "pos_id": pos_item["pos_id"],
                "title": pos_item["title"],
                "department": pos_item["department"],
                "score": score,
                "matched_tags": matched_tags,
                "document": pos_item,
            }
        )

    scored.sort(key=lambda item: (item["score"], item["pos_id"]), reverse=True)
    return scored[:top_k]


def build_pos_draft(registry_item: dict, pos_item: dict) -> dict:
    return {
        "new_pos_id": f"{registry_item['registry_id']}-POS-DRAFT",
        "source_registry_id": registry_item["registry_id"],
        "source_name": registry_item["source_name"],
        "based_on_pos_id": pos_item["pos_id"],
        "title": f"{pos_item['title']} - 수정 초안",
        "department": pos_item["department"],
        "tags": registry_item.get("tags", []),
        "sections": pos_item["sections"],
    }


def build_pos_document_text(pos_item: dict, change_note: str = "") -> str:
    if pos_item.get("document_text"):
        return pos_item["document_text"]

    lines = [
        "PURCHASE ORDER SPECIFICATION",
        "",
        f"Document ID : {pos_item.get('pos_id', '-')}",
        f"Title       : {pos_item.get('title', '-')}",
        f"Department  : {pos_item.get('department', '-')}",
        "",
        "1. General",
        "This specification defines the supply scope and technical basis for the related package.",
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
