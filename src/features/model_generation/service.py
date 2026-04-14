from src.features.spec_search.attribute_utils import flatten_attributes


FIELD_LABELS = {
    "basic_info.ship_type": "선종",
    "basic_info.ship_type_hint": "선종 힌트",
    "principal_dimensions.loa_m": "전장(LOA)",
    "principal_dimensions.breadth_m": "선폭(Breadth)",
    "principal_dimensions.draft_m": "만재흘수(Draft)",
    "machinery.main_engine": "기자재 / Main Engine",
    "cargo_system.cargo_capacity_m3": "화물창 용적",
    "cargo_system.cargo_tank_system": "화물창 형식",
    "cargo_system.capacity_teu": "적재 용량(TEU)",
}


def find_models_for_project(selected_project: dict, model_items: list[dict]) -> list[dict]:
    spec_id = selected_project.get("spec_id")
    matched_items = [item for item in model_items if item.get("source_spec_id") == spec_id]
    matched_items.sort(key=lambda item: item["model_id"])
    return matched_items


def summarize_model_similarity(current_attributes: dict, model_item: dict) -> dict:
    current_flat = flatten_attributes(current_attributes)
    baseline_flat = flatten_attributes(model_item.get("model_profile", {}))

    comparison_rows = []
    matched_count = 0

    for field_name, baseline_value in baseline_flat.items():
        current_value = current_flat.get(field_name)
        field_label = FIELD_LABELS.get(field_name, field_name)

        if current_value is None:
            comparison_rows.append(
                {
                    "field_name": field_name,
                    "field_label": field_label,
                    "current_value": "-",
                    "baseline_value": baseline_value,
                    "difference": "입력 없음",
                    "review_status": "입력 보완 필요",
                }
            )
            continue

        if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
            gap_ratio = _calculate_gap_ratio(float(current_value), float(baseline_value))
            difference = abs(float(current_value) - float(baseline_value))
            if gap_ratio <= 0.05:
                review_status = "재활용 적합"
                matched_count += 1
            elif gap_ratio <= 0.12:
                review_status = "조건부 검토"
            else:
                review_status = "차이 있음"
            difference_text = f"{difference:,.3f}"
        else:
            if str(current_value).strip().upper() == str(baseline_value).strip().upper():
                review_status = "재활용 적합"
                difference_text = "동일"
                matched_count += 1
            else:
                review_status = "차이 있음"
                difference_text = "상이"

        comparison_rows.append(
            {
                "field_name": field_name,
                "field_label": field_label,
                "current_value": current_value,
                "baseline_value": baseline_value,
                "difference": difference_text,
                "review_status": review_status,
            }
        )

    total = max(len(baseline_flat), 1)
    return {
        "score": round(matched_count / total, 3),
        "matched_count": matched_count,
        "comparison_rows": comparison_rows,
    }


def build_model_reuse_suggestions(current_attributes: dict, model_item: dict) -> list[dict]:
    comparison = summarize_model_similarity(current_attributes, model_item)
    comparison_map = {row["field_name"]: row for row in comparison["comparison_rows"]}

    suggestions = []
    for item in model_item.get("model_hierarchy", []):
        hint_fields = item.get("reuse_hint_fields", [])
        if not hint_fields:
            continue

        evidence_rows = [comparison_map[field] for field in hint_fields if field in comparison_map]
        if not evidence_rows:
            continue

        score = _score_evidence_rows(evidence_rows)
        if score < 0.35:
            continue

        review_status = _to_review_status(score)
        evidence = " / ".join(
            f"{row['field_label']}: 현재 `{row['current_value']}` / 기준 `{row['baseline_value']}`"
            for row in evidence_rows
        )
        suggestions.append(
            {
                "path": item["path"],
                "node_code": item.get("node_code", item["path"].split("/")[-1]),
                "node_name": item.get("name", item["path"].split("/")[-1]),
                "design_structure": item.get("design_structure", _default_design_structure(item["path"])),
                "model_type": item.get("model_type", item.get("type", "모델 항목")),
                "score": round(score, 3),
                "review_status": review_status,
                "evidence": evidence,
            }
        )

    suggestions.sort(key=lambda item: (item["score"], item["path"]), reverse=True)
    return suggestions[:8]


def build_model_draft(
    current_spec: dict,
    selected_project: dict,
    model_item: dict,
    approved_paths: list[str] | None = None,
    pos_draft_item: dict | None = None,
) -> dict:
    current_project_name = current_spec["project_name"]

    if pos_draft_item:
        current_attributes = pos_draft_item.get("current_project_attributes", current_spec.get("attributes", {}))
        source_pos_draft_id = pos_draft_item["draft_id"]
    else:
        current_attributes = current_spec.get("attributes", {})
        source_pos_draft_id = ""

    hierarchy_items = _rename_hierarchy_project(
        model_item.get("model_hierarchy", []),
        selected_project["project_name"],
        current_project_name,
    )

    if approved_paths:
        renamed_paths = [
            path.replace(f"PROJECT/{selected_project['project_name']}", f"PROJECT/{current_project_name}", 1)
            for path in approved_paths
        ]
        hierarchy_items = _filter_hierarchy_items(hierarchy_items, renamed_paths)

    return {
        "new_model_id": f"MODEL-{current_project_name}-001",
        "source_project_spec_id": selected_project["spec_id"],
        "source_project_name": selected_project["project_name"],
        "current_project_name": current_project_name,
        "source_pos_draft_id": source_pos_draft_id,
        "based_on_model_id": model_item["model_id"],
        "title": f"{current_project_name} 모델 편집설계 초안",
        "discipline": model_item["discipline"],
        "current_project_attributes": current_attributes,
        "model_hierarchy": hierarchy_items,
        "selected_structure_count": len(hierarchy_items),
    }


def build_hierarchy_rows(
    hierarchy_items: list[dict],
    suggestion_map: dict[str, dict] | None = None,
    selected_paths: set[str] | None = None,
) -> list[dict]:
    suggestion_map = suggestion_map or {}
    selected_paths = selected_paths or set()

    rows = []
    for item in hierarchy_items:
        path = item["path"]
        node_name = item.get("name", path.split("/")[-1])
        level = max(path.count("/") - 1, 0)
        suggestion = suggestion_map.get(path)

        rows.append(
            {
                "구조레벨": level,
                "노드코드": item.get("node_code", path.split("/")[-1]),
                "노드명": node_name,
                "설계구조": item.get("design_structure", _default_design_structure(path)),
                "모델타입": item.get("model_type", item.get("type", "모델 항목")),
                "사양기준": item.get("spec_basis", "-"),
                "생성일": item.get("created_on", "2026-03-01"),
                "생성조직": item.get("organization", _default_organization(item)),
                "담당설계": item.get("designer", _default_designer(item)),
                "개정": item.get("revision", "R00"),
                "모델경로": path,
                "재활용 추천": suggestion["review_status"] if suggestion else "-",
                "재활용 근거": suggestion["evidence"] if suggestion else "-",
                "선택 상태": "가져오기" if path in selected_paths else "-",
            }
        )
    return rows


def _score_evidence_rows(evidence_rows: list[dict]) -> float:
    score = 0.0
    for row in evidence_rows:
        if row["review_status"] == "재활용 적합":
            score += 1.0
        elif row["review_status"] == "조건부 검토":
            score += 0.55
        elif row["review_status"] == "입력 보완 필요":
            score += 0.25
    return score / max(len(evidence_rows), 1)


def _to_review_status(score: float) -> str:
    if score >= 0.8:
        return "재활용 추천"
    if score >= 0.55:
        return "검토 가능"
    return "참고 가능"


def _calculate_gap_ratio(current_value: float, baseline_value: float) -> float:
    if baseline_value == 0:
        return 0.0 if current_value == baseline_value else 1.0
    return abs(current_value - baseline_value) / abs(baseline_value)


def _rename_hierarchy_project(hierarchy_items: list[dict], source_project_name: str, target_project_name: str) -> list[dict]:
    renamed_items = []
    for item in hierarchy_items:
        path = item["path"].replace(f"PROJECT/{source_project_name}", f"PROJECT/{target_project_name}", 1)
        renamed_items.append({**item, "path": path})
    return renamed_items


def _filter_hierarchy_items(hierarchy_items: list[dict], approved_paths: list[str]) -> list[dict]:
    approved_set = set(approved_paths)
    filtered_items = []

    for item in hierarchy_items:
        path = item["path"]
        keep = False

        for approved_path in approved_set:
            if path == approved_path or path.startswith(f"{approved_path}/"):
                keep = True
                break
            if approved_path.startswith(f"{path}/"):
                keep = True
                break

        if keep:
            filtered_items.append(item)

    return filtered_items


def _default_design_structure(path: str) -> str:
    upper_path = path.upper()
    if "/HULL" in upper_path:
        return "선체"
    if "/OUTFIT-STEEL" in upper_path:
        return "의장-철의"
    if "/OUTFIT-JOINERY" in upper_path:
        return "의장-목의"
    if "/OUTFIT-PIPING" in upper_path:
        return "의장-배관"
    if "/OUTFIT-ELECTRIC" in upper_path:
        return "의장-전장"
    if "/OUTFIT-MACHINERY" in upper_path:
        return "의장-기계"
    return "모델 구조"


def _default_organization(item: dict) -> str:
    design_structure = item.get("design_structure") or _default_design_structure(item["path"])
    organization_map = {
        "선체": "선체설계부",
        "의장-철의": "철의설계부",
        "의장-목의": "목의설계부",
        "의장-배관": "배관설계부",
        "의장-전장": "전장설계부",
        "의장-기계": "기계설계부",
    }
    return organization_map.get(design_structure, "설계부")


def _default_designer(item: dict) -> str:
    design_structure = item.get("design_structure") or _default_design_structure(item["path"])
    designer_map = {
        "선체": "설계자 H",
        "의장-철의": "설계자 S",
        "의장-목의": "설계자 J",
        "의장-배관": "설계자 P",
        "의장-전장": "설계자 E",
        "의장-기계": "설계자 M",
    }
    return designer_map.get(design_structure, "설계자")
