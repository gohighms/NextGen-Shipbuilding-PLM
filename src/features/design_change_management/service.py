def build_assumed_current_project_model(model_draft: dict) -> dict:
    base_hierarchy = [dict(item) for item in model_draft.get("model_hierarchy", [])]
    current_project_name = model_draft["current_project_name"]
    existing_paths = {item["path"] for item in base_hierarchy}

    additional_nodes = [
        {
            "path": f"PROJECT/{current_project_name}/HULL/SHELL-PLATING/SIDE-SHELL/PLATE-SS-002",
            "node_code": "PLATE-SS-002",
            "name": "현측 외판 보강 반영판",
            "type": "Part",
            "design_structure": "선체",
            "model_type": "플레이트",
            "spec_basis": "배관 간섭 검토",
            "organization": "선체설계부",
            "designer": "설계자 H",
            "created_on": "2026-04-12",
            "revision": "R01",
        },
        {
            "path": f"PROJECT/{current_project_name}/HULL/INTERNAL-STRUCTURE/LONGITUDINAL-MEMBER/STIFFENER-LG-002",
            "node_code": "STIFFENER-LG-002",
            "name": "종보강재 추가부",
            "type": "Part",
            "design_structure": "선체",
            "model_type": "스티프너",
            "spec_basis": "배관 간섭 검토",
            "organization": "선체설계부",
            "designer": "설계자 H",
            "created_on": "2026-04-12",
            "revision": "R01",
        },
        {
            "path": f"PROJECT/{current_project_name}/OUTFIT-PIPING/FUEL-GAS-LINE/PIPE-FG-002",
            "node_code": "PIPE-FG-002",
            "name": "연료가스 주 배관 확장부",
            "type": "Part",
            "design_structure": "의장-배관",
            "model_type": "파이프",
            "spec_basis": "배관 통과 경로 확정",
            "organization": "배관설계부",
            "designer": "설계자 P",
            "created_on": "2026-04-13",
            "revision": "R01",
        },
        {
            "path": f"PROJECT/{current_project_name}/OUTFIT-PIPING/FUEL-GAS-LINE/PIPE-SUPPORT-002",
            "node_code": "PIPE-SUPPORT-002",
            "name": "연료가스 배관 서포트 002",
            "type": "Part",
            "design_structure": "의장-배관",
            "model_type": "서포트",
            "spec_basis": "배관 통과 경로 확정",
            "organization": "배관설계부",
            "designer": "설계자 P",
            "created_on": "2026-04-13",
            "revision": "R01",
        },
        {
            "path": f"PROJECT/{current_project_name}/OUTFIT-STEEL/FOUNDATION/SUPPORT-OPENING-001",
            "node_code": "SUPPORT-OPENING-001",
            "name": "개구 보강용 서포트",
            "type": "Part",
            "design_structure": "의장-철의",
            "model_type": "서포트",
            "spec_basis": "개구 보강 검토",
            "organization": "철의설계부",
            "designer": "설계자 S",
            "created_on": "2026-04-13",
            "revision": "R01",
        },
        {
            "path": f"PROJECT/{current_project_name}/OUTFIT-ELECTRIC/POWER-DISTRIBUTION/CABLE-TRAY-002",
            "node_code": "CABLE-TRAY-002",
            "name": "인접 케이블 트레이 002",
            "type": "Part",
            "design_structure": "의장-전장",
            "model_type": "케이블트레이",
            "spec_basis": "간섭 확인",
            "organization": "전장설계부",
            "designer": "설계자 E",
            "created_on": "2026-04-12",
            "revision": "R01",
        }
    ]

    for item in additional_nodes:
        parent_path = item["path"].rsplit("/", 1)[0]
        if item["path"] not in existing_paths and parent_path in existing_paths:
            base_hierarchy.append(item)

    return {
        "project_name": current_project_name,
        "source_project_name": model_draft.get("source_project_name", "-"),
        "base_model_id": model_draft.get("based_on_model_id", "-"),
        "discipline": model_draft.get("discipline", "-"),
        "current_attributes": model_draft.get("current_project_attributes", {}),
        "model_hierarchy": sorted(base_hierarchy, key=lambda item: item["path"]),
        "design_status": "설계 초안 진행 중",
    }


def build_change_scenario(
    assumed_model: dict,
    pos_draft: dict | None,
    request_title: str,
    request_reason: str,
    target_field: str,
    before_value: str,
    after_value: str,
    requester: str,
    urgency: str,
) -> dict:
    impacted_structures = _build_impacted_structures(assumed_model["model_hierarchy"], target_field)
    impact_rows = _build_impact_rows(impacted_structures)
    revision_rows = _build_revision_rows(request_title, requester)
    lifecycle_rows = _build_lifecycle_rows(requester)

    return {
        "project_name": assumed_model["project_name"],
        "request_title": request_title,
        "request_reason": request_reason,
        "target_field": target_field,
        "before_value": before_value,
        "after_value": after_value,
        "requester": requester,
        "urgency": urgency,
        "pos_reference": pos_draft["draft_id"] if pos_draft else "-",
        "model_reference": assumed_model["base_model_id"],
        "impacted_structures": impacted_structures,
        "impact_rows": impact_rows,
        "revision_rows": revision_rows,
        "lifecycle_rows": lifecycle_rows,
    }


def _build_impacted_structures(model_hierarchy: list[dict], target_field: str) -> list[dict]:
    path_keywords = {
        "coordination.pipe_hole": [
            "HULL/SHELL-PLATING/SIDE-SHELL",
            "HULL/INTERNAL-STRUCTURE/LONGITUDINAL-MEMBER",
            "OUTFIT-PIPING/FUEL-GAS-LINE",
            "OUTFIT-STEEL/FOUNDATION",
        ]
    }
    reason_text = {
        "coordination.pipe_hole": "배관 통과를 위한 hole 추가가 필요하여 선체/의장 협업 검토가 필요합니다."
    }

    keywords = path_keywords.get(target_field, [])
    impacted = []
    for item in model_hierarchy:
        path = item["path"].upper()
        if not any(keyword in path for keyword in keywords):
            continue
        if item.get("type") == "Project":
            continue

        impacted.append(
            {
                "노드코드": item.get("node_code", item["path"].split("/")[-1]),
                "노드명": item.get("name", item["path"].split("/")[-1]),
                "설계구조": item.get("design_structure", "-"),
                "모델타입": item.get("model_type", item.get("type", "모델 항목")),
                "모델경로": item["path"],
                "영향사유": reason_text.get(target_field, "연계 구조 검토 필요"),
            }
        )

    return impacted[:12]


def _build_impact_rows(impacted_structures: list[dict]) -> list[dict]:
    return [
        {
            "영향대상": "선체설계부",
            "상세": "현측 외판 및 보강재에 배관 관통용 hole 추가 위치 검토",
            "검토부서": "선체설계부",
            "영향도": "상",
        },
        {
            "영향대상": "배관설계부",
            "상세": "배관 통과 경로와 hole 직경, 여유치 재검토",
            "검토부서": "배관설계부",
            "영향도": "상",
        },
        {
            "영향대상": "철의설계부",
            "상세": "개구부 주위 서포트 및 보강 구조 반영 검토",
            "검토부서": "철의설계부",
            "영향도": "중",
        },
        {
            "영향대상": "POS",
            "상세": "구매 사양보다는 설계 협업 이슈 중심으로 참고만 수행",
            "검토부서": "영업설계팀",
            "영향도": "하",
        },
        {
            "영향대상": "모델 구조",
            "상세": f"영향 예상 노드 {len(impacted_structures)}건 검토",
            "검토부서": "기본설계1부",
            "영향도": "상",
        },
    ]


def _build_revision_rows(request_title: str, requester: str) -> list[dict]:
    return [
        {
            "Rev": "Rev.00",
            "상태": "기준 설계 초안",
            "설명": "편집설계를 통해 초기 구조가 마련된 상태",
            "작성자": requester,
        },
        {
            "Rev": "Rev.01",
            "상태": "변경 반영 완료",
            "설명": f"{request_title} 반영",
            "작성자": "설계 변경 관리자",
        },
    ]


def _build_lifecycle_rows(requester: str) -> list[dict]:
    return [
        {
            "단계": "ECR",
            "명칭": "Engineering Change Request",
            "설명": "배관 통과용 hole 누락 이슈 접수",
            "작성자": requester,
            "상태": "완료",
        },
        {
            "단계": "ECO",
            "명칭": "Engineering Change Order",
            "설명": "선체/배관/철의 협업으로 반영 범위와 설계 조치 결정",
            "작성자": "설계 변경 관리자",
            "상태": "진행중",
        },
        {
            "단계": "ECN",
            "명칭": "Engineering Change Notice",
            "설명": "승인된 변경안을 관련 조직에 통보",
            "작성자": "설계 변경 관리자",
            "상태": "대기",
        },
    ]
