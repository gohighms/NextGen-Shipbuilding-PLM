def build_model_structure_rows(model_hierarchy: list[dict]) -> list[dict]:
    rows = []
    for item in model_hierarchy:
        path = item["path"]
        rows.append(
            {
                "구조레벨": max(path.count("/") - 1, 0),
                "노드코드": item.get("node_code", path.split("/")[-1]),
                "노드명": item.get("name", path.split("/")[-1]),
                "설계구조": item.get("design_structure", item.get("type", "모델 구조")),
                "모델타입": item.get("model_type", item.get("type", "모델 항목")),
                "모델경로": path,
                "생성조직": item.get("organization", "-"),
                "개정": item.get("revision", "R00"),
            }
        )
    return rows


def build_fixed_block_division_rows(model_draft: dict) -> list[dict]:
    rows = []
    for item in model_draft.get("model_hierarchy", []):
        if item.get("design_structure") != "선체":
            continue
        if item.get("type") not in {"Assembly", "Part"}:
            continue

        block_code = _suggest_logical_block(item)
        rows.append(
            {
                "프로젝트": model_draft["current_project_name"],
                "논리 블록": block_code,
                "노드코드": item.get("node_code", item["path"].split("/")[-1]),
                "노드명": item.get("name", item["path"].split("/")[-1]),
                "SFD 타입": _to_sfd_type(item),
                "모델경로": item["path"],
                "분류 근거": _suggest_block_reason(item),
            }
        )

    rows.sort(key=lambda row: (row["논리 블록"], row["노드코드"]))
    return rows


def build_sdd_rows(logical_rows: list[dict]) -> list[dict]:
    rows = []
    for row in logical_rows:
        rows.append(
            {
                "프로젝트": row["프로젝트"],
                "SDD 블록": row["논리 블록"],
                "솔리드 모델명": f"{row['논리 블록']}-{row['노드코드']}",
                "기준 항목": row["노드명"],
                "변환 개념": "SFD 기준 형상을 바탕으로 solid volume 모델 구성",
            }
        )
    rows.sort(key=lambda row: (row["SDD 블록"], row["솔리드 모델명"]))
    return rows


def build_block_division_summary_rows(logical_rows: list[dict]) -> list[dict]:
    grouped = {}
    for row in logical_rows:
        grouped.setdefault(row["논리 블록"], 0)
        grouped[row["논리 블록"]] += 1

    summary_rows = []
    for block_code, count in sorted(grouped.items()):
        summary_rows.append(
            {
                "논리 블록": block_code,
                "포함 항목 수": count,
                "다음 단계": "SDD solid block 모델 구성",
            }
        )
    return summary_rows


def build_block_division_result(model_draft: dict) -> dict:
    logical_rows = build_fixed_block_division_rows(model_draft)
    return {
        "project_name": model_draft["current_project_name"],
        "source_model_draft_id": model_draft["draft_id"],
        "source_model_id": model_draft["based_on_model_id"],
        "title": f"{model_draft['current_project_name']} Block Division 초안",
        "logical_rows": logical_rows,
        "sdd_rows": build_sdd_rows(logical_rows),
        "summary_rows": build_block_division_summary_rows(logical_rows),
    }


def build_mbom_rows(block_division_item: dict, full_model_rows: list[dict]) -> list[dict]:
    block_map = {row["논리 블록"]: row for row in block_division_item.get("logical_rows", [])}
    default_blocks = ["BLOCK-109", "BLOCK-152", "BLOCK-221", "BLOCK-301"]
    default_stage_map = {
        "BLOCK-109": "대조",
        "BLOCK-152": "중조",
        "BLOCK-221": "소조",
        "BLOCK-301": "중조",
    }

    rows = []
    for model_row in full_model_rows:
        if model_row["구조레벨"] == 0:
            continue

        block_code = _infer_block_for_full_structure(model_row, block_map, default_blocks)
        rows.append(
            {
                "프로젝트": block_division_item["project_name"],
                "블록": block_code,
                "MBOM 단계": default_stage_map.get(block_code, "중조"),
                "설계구조": model_row["설계구조"],
                "품목군": _to_mbom_family(model_row["설계구조"], model_row["모델타입"]),
                "품목코드": f"{block_code}-{model_row['노드코드']}",
                "품목명": model_row["노드명"],
                "원천 모델": model_row["노드코드"],
                "구성 view": "선체 + 의장 전체 모델 구조 기준",
            }
        )

    rows.sort(key=lambda item: (item["블록"], item["MBOM 단계"], item["품목코드"]))
    return rows


def build_mbom_summary_rows(mbom_rows: list[dict]) -> list[dict]:
    grouped = {}
    for row in mbom_rows:
        key = (row["블록"], row["MBOM 단계"])
        grouped.setdefault(key, 0)
        grouped[key] += 1

    summary = []
    for (block_code, stage_name), count in sorted(grouped.items()):
        summary.append(
            {
                "블록": block_code,
                "MBOM 단계": stage_name,
                "구성 품목 수": count,
            }
        )
    return summary


def build_wbom_rows(mbom_item: dict) -> list[dict]:
    rows = []
    for row in mbom_item.get("mbom_rows", []):
        rows.append(
            {
                "프로젝트": row["프로젝트"],
                "작업 패키지": f"{row['블록']}-{row['MBOM 단계']}",
                "WBOM 구분": "본체 작업",
                "품목코드": row["품목코드"],
                "품목명": row["품목명"],
                "작업 목적": _to_work_purpose(row["품목군"]),
                "비고": "MBOM 기반 본체 작업 항목",
            }
        )
        rows.append(_build_support_item(row))

    rows.sort(key=lambda item: (item["작업 패키지"], item["WBOM 구분"], item["품목코드"]))
    return rows


def build_wbom_summary_rows(wbom_rows: list[dict]) -> list[dict]:
    grouped = {}
    for row in wbom_rows:
        key = (row["작업 패키지"], row["WBOM 구분"])
        grouped.setdefault(key, 0)
        grouped[key] += 1

    summary = []
    for (package_name, division_name), count in sorted(grouped.items()):
        summary.append(
            {
                "작업 패키지": package_name,
                "WBOM 구분": division_name,
                "구성 항목 수": count,
            }
        )
    return summary


def build_work_instruction_rows(wbom_item: dict) -> list[dict]:
    rows = []
    seen_packages = set()
    for row in wbom_item.get("wbom_rows", []):
        package_name = row["작업 패키지"]
        if package_name in seen_packages:
            continue
        seen_packages.add(package_name)

        rows.append(
            {
                "작업지시 ID": f"WI-{package_name}",
                "작업 패키지": package_name,
                "주 작업": _to_primary_work(package_name),
                "준비 항목": _to_preparation_items(package_name),
                "참조 품목 수": len([item for item in wbom_item["wbom_rows"] if item["작업 패키지"] == package_name]),
                "작업 순서": "자재 준비 → 본체 작업 → 작업 지원물 철거",
                "담당 조직": _to_work_team(package_name),
            }
        )
    return rows


def build_work_instruction_summary_rows(instruction_rows: list[dict]) -> list[dict]:
    return [
        {
            "작업 패키지": row["작업 패키지"],
            "주 작업": row["주 작업"],
            "참조 품목 수": row["참조 품목 수"],
            "담당 조직": row["담당 조직"],
        }
        for row in instruction_rows
    ]


def _build_support_item(mbom_row: dict) -> dict:
    support_map = {
        "판재류": ("SUPPORT-SCAFFOLD", "작업 발판", "판재 취부 작업 보조"),
        "보강재류": ("SUPPORT-JIG", "취부 지그", "보강재 정렬 및 취부 보조"),
        "갑판 구조물": ("SUPPORT-LIFT", "양중 보조대", "갑판 구조물 설치 보조"),
        "선체 구조물": ("SUPPORT-STAND", "임시 지지대", "구조물 세움 및 고정 보조"),
        "배관류": ("SUPPORT-RACK", "배관 작업대", "배관 취부 및 정렬 보조"),
        "전장류": ("SUPPORT-CABLE", "케이블 작업대", "케이블 정리 및 설치 보조"),
        "기계/기자재": ("SUPPORT-LIFT", "장비 설치 보조대", "기자재 설치 보조"),
        "목의류": ("SUPPORT-CART", "내장 작업 카트", "내장 자재 이동 보조"),
    }
    item_code, item_name, purpose = support_map.get(
        mbom_row["품목군"],
        ("SUPPORT-GENERAL", "작업 보조물", "작업 수행 보조"),
    )
    return {
        "프로젝트": mbom_row["프로젝트"],
        "작업 패키지": f"{mbom_row['블록']}-{mbom_row['MBOM 단계']}",
        "WBOM 구분": "작업 지원",
        "품목코드": f"{mbom_row['품목코드']}-{item_code}",
        "품목명": item_name,
        "작업 목적": purpose,
        "비고": "배 자체와 무관한 작업용 보조 항목",
    }


def _infer_block_for_full_structure(model_row: dict, block_map: dict, default_blocks: list[str]) -> str:
    path = model_row["모델경로"]
    for logical_row in block_map.values():
        if path == logical_row["모델경로"] or path.startswith(f"{logical_row['모델경로']}/"):
            return logical_row["논리 블록"]

    design_structure = model_row["설계구조"]
    if design_structure == "선체":
        return "BLOCK-109"
    if design_structure in {"의장-철의", "의장-배관", "의장-전장", "의장-기계"}:
        return "BLOCK-221"
    if design_structure == "의장-목의":
        return "BLOCK-301"
    return default_blocks[-1]


def _to_sfd_type(item: dict) -> str:
    model_type = item.get("model_type", "")
    mapping = {
        "플레이트": "Surface Plate",
        "스티프너": "Surface Stiffener",
        "플레이트 묶음": "Surface Panel",
        "갑판 구조": "Surface Deck",
        "보강 구조": "Surface Structure",
    }
    return mapping.get(model_type, "Surface Structure")


def _suggest_logical_block(item: dict) -> str:
    path = item["path"].upper()
    if "SIDE-SHELL" in path or "BOTTOM-SHELL" in path:
        return "BLOCK-109"
    if "DECK" in path:
        return "BLOCK-152"
    if "LONGITUDINAL" in path or "TRANSVERSE" in path:
        return "BLOCK-221"
    return "BLOCK-301"


def _suggest_block_reason(item: dict) -> str:
    path = item["path"].upper()
    if "SIDE-SHELL" in path:
        return "선체 외판 계열이므로 선수/선측 논리 블록에 우선 배치"
    if "DECK" in path:
        return "갑판 계열 형상으로 상부 블록 구성 후보"
    if "LONGITUDINAL" in path or "TRANSVERSE" in path:
        return "내부 보강 구조로 별도 논리 블록 후보"
    return "선체 SFD 형상을 기준으로 논리 블록 후보 제안"


def _to_mbom_family(design_structure: str, model_type: str) -> str:
    if design_structure == "선체":
        if model_type in {"플레이트", "플레이트 묶음"}:
            return "판재류"
        if model_type == "스티프너":
            return "보강재류"
        if model_type == "갑판 구조":
            return "갑판 구조물"
        return "선체 구조물"
    if design_structure == "의장-배관":
        return "배관류"
    if design_structure == "의장-전장":
        return "전장류"
    if design_structure == "의장-기계":
        return "기계/기자재"
    if design_structure == "의장-철의":
        return "의장 철의류"
    if design_structure == "의장-목의":
        return "목의류"
    return "기타 품목"


def _to_work_purpose(item_family: str) -> str:
    purpose_map = {
        "판재류": "판재 절단 및 취부",
        "보강재류": "보강재 조립 및 취부",
        "갑판 구조물": "갑판 구조 설치",
        "선체 구조물": "선체 구조 조립",
        "배관류": "배관 설치 및 정렬",
        "전장류": "케이블 및 전장품 설치",
        "기계/기자재": "기자재 설치 및 정렬",
        "의장 철의류": "철의 구조 설치",
        "목의류": "내장 구조 설치",
    }
    return purpose_map.get(item_family, "일반 작업")


def _to_primary_work(package_name: str) -> str:
    if package_name.startswith("BLOCK-109"):
        return "선체 외판 및 구조 조립"
    if package_name.startswith("BLOCK-152"):
        return "갑판 및 상부 구조 작업"
    if package_name.startswith("BLOCK-221"):
        return "의장/배관/기자재 설치 작업"
    return "내장 및 기타 구조 작업"


def _to_preparation_items(package_name: str) -> str:
    if package_name.startswith("BLOCK-109"):
        return "절단 자재, 작업 발판, 임시 지지대"
    if package_name.startswith("BLOCK-152"):
        return "양중 장비, 작업 발판, 위치 결정 지그"
    if package_name.startswith("BLOCK-221"):
        return "배관 작업대, 설치 지그, 임시 브라켓"
    return "작업 카트, 소형 지그, 보조 자재"


def _to_work_team(package_name: str) -> str:
    if package_name.startswith("BLOCK-109"):
        return "선체생산1부"
    if package_name.startswith("BLOCK-152"):
        return "선체생산2부"
    if package_name.startswith("BLOCK-221"):
        return "의장생산부"
    return "내장생산부"
