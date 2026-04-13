from src.features.spec_search.attribute_utils import flatten_attributes


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
        if current_value is None:
            comparison_rows.append(
                {
                    "field_name": field_name,
                    "current_value": "-",
                    "baseline_value": baseline_value,
                    "difference": "입력 없음",
                    "review_status": "정보 부족",
                }
            )
            continue

        if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
            gap_ratio = _calculate_gap_ratio(current_value, baseline_value)
            difference = f"{abs(current_value - baseline_value):,.3f}"
            if gap_ratio <= 0.05:
                review_status = "재활용 적합"
                matched_count += 1
            elif gap_ratio <= 0.12:
                review_status = "조건부 검토"
            else:
                review_status = "차이 큼"
        else:
            if str(current_value).upper() == str(baseline_value).upper():
                review_status = "재활용 적합"
                difference = "동일"
                matched_count += 1
            else:
                review_status = "차이 큼"
                difference = "상이"

        comparison_rows.append(
            {
                "field_name": field_name,
                "current_value": current_value,
                "baseline_value": baseline_value,
                "difference": difference,
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

    suggestion_specs = [
        {
            "name": "선체 구조",
            "paths": ["PROJECT/{project}/HULL"],
            "fields": [
                "principal_dimensions.loa_m",
                "principal_dimensions.breadth_m",
                "principal_dimensions.draft_m",
            ],
        },
        {
            "name": "의장-철의",
            "paths": ["PROJECT/{project}/OUTFIT/STEEL-OUTFIT"],
            "fields": ["principal_dimensions.loa_m", "principal_dimensions.breadth_m"],
        },
        {
            "name": "의장-목의",
            "paths": ["PROJECT/{project}/OUTFIT/JOINERY"],
            "fields": ["basic_info.ship_type_hint", "basic_info.ship_type"],
        },
        {
            "name": "의장-배관",
            "paths": ["PROJECT/{project}/OUTFIT/PIPING"],
            "fields": ["cargo_system.cargo_capacity_m3", "cargo_system.cargo_tank_system"],
        },
        {
            "name": "의장-전장",
            "paths": ["PROJECT/{project}/OUTFIT/ELECTRIC"],
            "fields": ["machinery.main_engine"],
        },
    ]

    project_name = model_item.get("source_project_name", "")
    available_paths = [item["path"] for item in model_item.get("model_hierarchy", [])]
    suggestions = []

    for spec in suggestion_specs:
        evidence_rows = [comparison_map[field] for field in spec["fields"] if field in comparison_map]
        if not evidence_rows:
            continue

        matched = sum(1 for row in evidence_rows if row["review_status"] == "재활용 적합")
        conditional = sum(1 for row in evidence_rows if row["review_status"] == "정보 부족")
        score = round((matched + conditional * 0.4) / len(evidence_rows), 3)

        if score >= 0.66:
            review_status = "재활용 추천"
        elif score >= 0.33:
            review_status = "조건부 검토"
        else:
            review_status = "제외"

        root_paths = [path.format(project=project_name) for path in spec["paths"]]
        root_paths = [path for path in root_paths if any(item_path == path or item_path.startswith(f"{path}/") for item_path in available_paths)]
        if not root_paths:
            continue

        evidence = " / ".join(
            f"{row['field_name']}: 현재 `{row['current_value']}` / 기준 `{row['baseline_value']}`"
            for row in evidence_rows
        )
        suggestions.append(
            {
                "name": spec["name"],
                "score": score,
                "review_status": review_status,
                "root_paths": root_paths,
                "evidence": evidence,
            }
        )

    selected_suggestions = [item for item in suggestions if item["review_status"] != "제외"]
    return selected_suggestions[:3]


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
        "title": f"{current_project_name} 모델 편집 초안",
        "discipline": model_item["discipline"],
        "current_project_attributes": current_attributes,
        "model_hierarchy": hierarchy_items,
        "selected_structure_count": len(hierarchy_items),
    }


def build_hierarchy_rows(hierarchy_items: list[dict], highlighted_paths: set[str] | None = None) -> list[dict]:
    highlighted_paths = highlighted_paths or set()
    rows = []
    for item in hierarchy_items:
        path = item["path"]
        node_name = item.get("name", path.split("/")[-1])
        level = max(path.count("/") - 1, 0)
        rows.append(
            {
                "구조레벨": level,
                "노드코드": item.get("node_code", path.split("/")[-1]),
                "노드명": node_name,
                "설계구조": item.get("structure_role", _default_structure_role(path)),
                "모델경로": path,
                "생성일": item.get("created_on", "2026-03-01"),
                "생성조직": item.get("organization", _default_organization(path)),
                "담당설계": item.get("designer", _default_designer(path)),
                "개정": item.get("revision", "R00"),
                "재활용 제안": "선택 구조" if _is_highlighted(path, highlighted_paths) else "-",
            }
        )
    return rows


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
    return [
        item
        for item in hierarchy_items
        if any(item["path"] == path or item["path"].startswith(f"{path}/") for path in approved_paths)
    ]


def _is_highlighted(path: str, highlighted_paths: set[str]) -> bool:
    return any(path == target_path or path.startswith(f"{target_path}/") for target_path in highlighted_paths)


def _default_structure_role(path: str) -> str:
    upper_path = path.upper()
    if "/HULL" in upper_path:
        return "선체"
    if "/STEEL-OUTFIT" in upper_path:
        return "의장-철의"
    if "/JOINERY" in upper_path:
        return "의장-목의"
    if "/PIPING" in upper_path:
        return "의장-배관"
    if "/ELECTRIC" in upper_path:
        return "의장-전장"
    if "/MACHINERY" in upper_path:
        return "의장-기계"
    if "/OUTFIT" in upper_path:
        return "의장"
    return "모델 구조"


def _default_organization(path: str) -> str:
    upper_path = path.upper()
    if "/HULL" in upper_path:
        return "선체설계부"
    if "/STEEL-OUTFIT" in upper_path:
        return "철의설계부"
    if "/JOINERY" in upper_path:
        return "목의설계부"
    if "/PIPING" in upper_path:
        return "배관설계부"
    if "/ELECTRIC" in upper_path:
        return "전장설계부"
    return "의장설계부"


def _default_designer(path: str) -> str:
    upper_path = path.upper()
    if "/HULL" in upper_path:
        return "설계자-H"
    if "/STEEL-OUTFIT" in upper_path:
        return "설계자-S"
    if "/JOINERY" in upper_path:
        return "설계자-J"
    if "/PIPING" in upper_path:
        return "설계자-P"
    if "/ELECTRIC" in upper_path:
        return "설계자-E"
    return "설계자-O"
