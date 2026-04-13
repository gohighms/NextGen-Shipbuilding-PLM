def recommend_models(pos_draft_item: dict, model_items: list[dict], top_k: int = 3) -> list[dict]:
    pos_tags = {item["tag_name"] for item in pos_draft_item.get("tags", [])}
    scored = []

    for model_item in model_items:
        model_tags = set(model_item.get("tags", []))
        matched_tags = sorted(pos_tags & model_tags)
        score = len(matched_tags)
        scored.append(
            {
                "model_id": model_item["model_id"],
                "title": model_item["title"],
                "discipline": model_item["discipline"],
                "score": score,
                "matched_tags": matched_tags,
                "document": model_item,
            }
        )

    scored.sort(key=lambda item: (item["score"], item["model_id"]), reverse=True)
    return scored[:top_k]


def build_model_draft(pos_draft_item: dict, model_item: dict) -> dict:
    return {
        "new_model_id": f"{pos_draft_item['draft_id']}-MODEL-DRAFT",
        "source_pos_draft_id": pos_draft_item["draft_id"],
        "source_name": pos_draft_item["title"],
        "based_on_model_id": model_item["model_id"],
        "title": f"{model_item['title']} - 편집설계 초안",
        "discipline": model_item["discipline"],
        "tags": pos_draft_item.get("tags", []),
        "ebom_items": model_item["ebom_items"],
        "model_notes": model_item.get("model_notes", []),
    }


def build_model_document_text(model_item: dict, change_note: str = "") -> str:
    if model_item.get("document_text"):
        return model_item["document_text"]

    lines = [
        "EDIT DESIGN MODEL / EBOM SUMMARY",
        "",
        f"Model ID   : {model_item.get('model_id', model_item.get('new_model_id', '-'))}",
        f"Title      : {model_item.get('title', '-')}",
        f"Discipline : {model_item.get('discipline', '-')}",
        "",
        "1. Model Overview",
        "This model summary defines the reusable engineering basis and EBOM scope for edit design.",
        "",
        "2. EBOM Items",
    ]

    for item in model_item.get("ebom_items", []):
        lines.append(f"- {item['item_code']} / {item['description']} / Qty {item['quantity']}")

    lines.append("")
    lines.append("3. Design Notes")
    for note in model_item.get("model_notes", []):
        lines.append(f"- {note}")

    if change_note:
        lines.append("")
        lines.append("Change Note")
        lines.append(change_note)

    return "\n".join(lines).strip()
