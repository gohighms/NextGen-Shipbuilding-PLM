from __future__ import annotations

from collections import Counter, defaultdict


def build_model_structure_rows(model_hierarchy: list[dict]) -> list[dict]:
    rows: list[dict] = []
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
                "생성조직": item.get("organization", _default_organization(item.get("design_structure", ""))),
                "개정": item.get("revision", "R00"),
            }
        )
    return rows


def build_fixed_block_division_rows(model_draft: dict) -> list[dict]:
    rows: list[dict] = []
    for item in model_draft.get("model_hierarchy", []):
        if item.get("design_structure") != "선체":
            continue
        if item.get("type") not in {"Assembly", "Part"}:
            continue

        block_code = _suggest_logical_block(item)
        node_code = item.get("node_code", item["path"].split("/")[-1])
        node_name = item.get("name", item["path"].split("/")[-1])
        rows.append(
            {
                "프로젝트": model_draft["current_project_name"],
                "논리 블록": block_code,
                "노드코드": node_code,
                "노드명": node_name,
                "SFD 타입": _to_sfd_type(item),
                "모델경로": item["path"],
                "분류 근거": _suggest_block_reason(item),
            }
        )

    rows.sort(key=lambda row: (row["논리 블록"], row["노드코드"]))
    return rows


def build_sdd_rows(logical_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for row in logical_rows:
        rows.append(
            {
                "프로젝트": row["프로젝트"],
                "SDD 블록": row["논리 블록"],
                "솔리드 모델명": f"{row['논리 블록']}-{row['노드코드']}",
                "기준 항목": row["노드명"],
                "변환 개념": "SFD surface 기준 형상을 바탕으로 solid volume model 구성",
            }
        )
    rows.sort(key=lambda row: (row["SDD 블록"], row["솔리드 모델명"]))
    return rows


def build_block_division_summary_rows(logical_rows: list[dict]) -> list[dict]:
    grouped = Counter(row["논리 블록"] for row in logical_rows)
    return [
        {
            "논리 블록": block_code,
            "포함 항목 수": count,
            "다음 단계": "SDD solid block model 구성",
        }
        for block_code, count in sorted(grouped.items())
    ]


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


def build_bom_model_structure_rows(model_hierarchy: list[dict]) -> list[dict]:
    project_row = next((item for item in model_hierarchy if item.get("type") == "Project"), {})
    project_code = project_row.get("node_code", "PROJECT")
    base_path = f"PROJECT/{project_code}/BOM-VIEW"

    rows: list[dict] = []
    for index, item in enumerate(_collect_model_parts(model_hierarchy), start=1):
        grand_block = _assign_grand_block(item, index)
        sub_block = _sub_block_code(grand_block, index)
        mid_block = _mid_block_code(grand_block, index)
        pe_block = _assign_pe_block(grand_block)
        node_code = item.get("node_code", item.get("path", f"PART-{index:03d}").split("/")[-1])
        node_name = item.get("name", node_code)
        design_structure = item.get("design_structure", item.get("type", "모델 구조"))
        model_type = item.get("model_type", item.get("type", "모델 항목"))

        rows.append(
            {
                "구조레벨": max(item.get("path", "").count("/") - 1, 0),
                "노드코드": node_code,
                "노드명": node_name,
                "설계구조": design_structure,
                "모델타입": model_type,
                "모델경로": item.get("path", f"{base_path}/{node_code}"),
                "생성조직": item.get("organization", _default_organization(design_structure)),
                "개정": item.get("revision", "R00"),
                "블록힌트": grand_block,
                "조립단계힌트": "파트",
                "소조블록힌트": sub_block,
                "중조블록힌트": mid_block,
                "대조블록힌트": grand_block,
                "PE블록힌트": pe_block,
            }
        )

    return rows


def build_mbom_rows(block_division_item: dict, full_model_rows: list[dict]) -> list[dict]:
    project_name = block_division_item["project_name"]
    part_rows = _build_part_input_rows(block_division_item, full_model_rows)
    rows: list[dict] = []
    row_keys: set[str] = set()

    def add_row(row: dict) -> None:
        key = row["품목코드"]
        if key in row_keys:
            return
        row_keys.add(key)
        rows.append(row)

    add_row(
        _make_mbom_row(
            project_name=project_name,
            assembly_level="SHIP",
            stage_name="탑재",
            item_code="SHIP-HULL",
            item_name=f"{project_name} 선박",
            parent_code="",
            grand_block="",
            pe_block="",
            sub_block="",
            mid_block="",
            design_structure="선박",
            family="선박",
            source_model="",
            send_code="G9-DK",
            view_note="대조/PE 블록 탑재 완료 기준 선박 구성",
        )
    )

    for pe_block in sorted({row["PE블록"] for row in part_rows if row["PE블록"]}):
        grand_blocks = sorted({row["대조블록"] for row in part_rows if row["PE블록"] == pe_block})
        add_row(
            _make_mbom_row(
                project_name=project_name,
                assembly_level="PE_BLOCK",
                stage_name="PE",
                item_code=f"PE-{pe_block}",
                item_name=f"{pe_block} PE 블록",
                parent_code="SHIP-HULL",
                grand_block=", ".join(grand_blocks),
                pe_block=pe_block,
                sub_block="",
                mid_block="",
                design_structure="선체",
                family="PE 블록",
                source_model="",
                send_code=_send_code_for("PE", pe_block),
                view_note="대조 블록을 탑재 전 단위로 선행 결합",
            )
        )

    for grand_block in sorted({row["대조블록"] for row in part_rows}):
        pe_block = _assign_pe_block(grand_block)
        parent_code = f"PE-{pe_block}" if pe_block else "SHIP-HULL"
        add_row(
            _make_mbom_row(
                project_name=project_name,
                assembly_level="GRAND_BLOCK",
                stage_name="대조",
                item_code=grand_block,
                item_name=f"{grand_block} 대조 블록",
                parent_code=parent_code,
                grand_block=grand_block,
                pe_block=pe_block,
                sub_block="",
                mid_block="",
                design_structure="선체",
                family="대조 블록",
                source_model="",
                send_code=_send_code_for("대조", grand_block),
                view_note="중조 블록을 대조 단위로 결합",
            )
        )

    for mid_block in sorted({row["중조블록"] for row in part_rows}):
        sample = next(row for row in part_rows if row["중조블록"] == mid_block)
        add_row(
            _make_mbom_row(
                project_name=project_name,
                assembly_level="MID_BLOCK",
                stage_name="중조",
                item_code=mid_block,
                item_name=f"{mid_block} 중조 블록",
                parent_code=sample["대조블록"],
                grand_block=sample["대조블록"],
                pe_block=sample["PE블록"],
                sub_block="",
                mid_block=mid_block,
                design_structure=sample["설계구조"],
                family="중조 블록",
                source_model="",
                send_code=_send_code_for("중조", mid_block),
                view_note="소조 블록을 중간 조립체로 결합",
            )
        )

    for sub_block in sorted({row["소조블록"] for row in part_rows}):
        sample = next(row for row in part_rows if row["소조블록"] == sub_block)
        add_row(
            _make_mbom_row(
                project_name=project_name,
                assembly_level="SUB_BLOCK",
                stage_name="소조",
                item_code=sub_block,
                item_name=f"{sub_block} 소조 블록",
                parent_code=sample["중조블록"],
                grand_block=sample["대조블록"],
                pe_block=sample["PE블록"],
                sub_block=sub_block,
                mid_block=sample["중조블록"],
                design_structure=sample["설계구조"],
                family="소조 블록",
                source_model="",
                send_code=_send_code_for("소조", sub_block),
                view_note="모델 파트를 소조 단위로 군집화",
            )
        )

    for part in part_rows:
        family = _to_mbom_family(part["설계구조"], part["모델타입"])
        add_row(
            _make_mbom_row(
                project_name=project_name,
                assembly_level="PART",
                stage_name="파트",
                item_code=f"{part['소조블록']}-{part['노드코드']}",
                item_name=part["노드명"],
                parent_code=part["소조블록"],
                grand_block=part["대조블록"],
                pe_block=part["PE블록"],
                sub_block=part["소조블록"],
                mid_block=part["중조블록"],
                design_structure=part["설계구조"],
                family=family,
                source_model=part["노드코드"],
                send_code=_send_code_for("파트", part["소조블록"]),
                view_note="모델 파트 기준 물량/발주 가능 항목",
            )
        )

    level_order = {"SHIP": 0, "PE_BLOCK": 1, "GRAND_BLOCK": 2, "MID_BLOCK": 3, "SUB_BLOCK": 4, "PART": 5}
    rows.sort(key=lambda item: (item["대조블록"] or "ZZZ", item["PE블록"] or "ZZZ", level_order[item["조립레벨"]], item["품목코드"]))
    return rows


def build_mbom_summary_rows(mbom_rows: list[dict]) -> list[dict]:
    grouped = Counter((row["조립레벨"], row["MBOM 단계"], row.get("송선코드", "")) for row in mbom_rows)
    level_order = {"SHIP": 0, "PE_BLOCK": 1, "GRAND_BLOCK": 2, "MID_BLOCK": 3, "SUB_BLOCK": 4, "PART": 5}
    summary = [
        {
            "조립레벨": assembly_level,
            "MBOM 단계": stage_name,
            "송선코드": send_code,
            "구성 품목 수": count,
        }
        for (assembly_level, stage_name, send_code), count in grouped.items()
    ]
    summary.sort(key=lambda row: (level_order.get(row["조립레벨"], 9), row["MBOM 단계"], row["송선코드"]))
    return summary


def build_wbom_rows(mbom_item: dict) -> list[dict]:
    rows: list[dict] = []
    for row in mbom_item.get("mbom_rows", []):
        if row.get("조립레벨") == "SHIP":
            continue
        package_name = f"{row.get('송선To', '-')}-{row['MBOM 단계']}-{row['품목코드']}"
        rows.append(
            {
                "프로젝트": row["프로젝트"],
                "블록": row["블록"],
                "조립단계": row["MBOM 단계"],
                "조립레벨": row.get("조립레벨", ""),
                "상위품목코드": row.get("상위품목코드", ""),
                "소조블록": row.get("소조블록", ""),
                "중조블록": row.get("중조블록", ""),
                "대조블록": row.get("대조블록", row["블록"]),
                "PE블록": row.get("PE블록", ""),
                "송선코드": row.get("송선코드", ""),
                "송선From": row.get("송선From", ""),
                "송선To": row.get("송선To", ""),
                "설계구조": row["설계구조"],
                "작업 패키지": package_name,
                "WBOM 구분": "본체 작업",
                "품목코드": row["품목코드"],
                "품목명": row["품목명"],
                "모델ID": row["원천 모델"],
                "모델타입": row["품목군"],
                "작업 목적": _to_work_purpose(row["품목군"]),
                "비고": "MBOM 기반 본체 작업 항목",
            }
        )
        rows.append(_build_support_item(row))

    rows.sort(key=lambda item: (item["작업 패키지"], item["WBOM 구분"], item["품목코드"]))
    return rows


def build_wbom_summary_rows(wbom_rows: list[dict]) -> list[dict]:
    grouped = Counter((row["작업 패키지"], row["WBOM 구분"]) for row in wbom_rows)
    return [
        {
            "작업 패키지": package_name,
            "WBOM 구분": division_name,
            "구성 항목 수": count,
        }
        for (package_name, division_name), count in sorted(grouped.items())
    ]


def build_work_instruction_rows(wbom_item: dict) -> list[dict]:
    rows: list[dict] = []
    seen_packages: set[str] = set()
    for row in wbom_item.get("wbom_rows", []):
        package_name = row["작업 패키지"]
        if package_name in seen_packages:
            continue
        seen_packages.add(package_name)

        package_rows = [item for item in wbom_item["wbom_rows"] if item["작업 패키지"] == package_name]
        rows.append(
            {
                "작업지시 ID": f"WI-{package_name}",
                "블록": row.get("블록", package_name.split("-")[0]),
                "조립단계": row.get("조립단계", package_name.split("-")[-1]),
                "송선코드": row.get("송선코드", ""),
                "송선From": row.get("송선From", ""),
                "송선To": row.get("송선To", ""),
                "설계구조": row.get("설계구조", "-"),
                "작업 패키지": package_name,
                "주 작업": _to_primary_work(row.get("조립단계", package_name)),
                "준비 항목": _to_preparation_items(row.get("조립단계", package_name)),
                "참조 항목 수": len(package_rows),
                "작업 순서": "자재 준비 → 조립/취부 → 검사/보완 → 작업 지원물 정리",
                "담당 조직": _to_work_team(row.get("조립단계", package_name)),
            }
        )
    return rows


def build_work_instruction_summary_rows(instruction_rows: list[dict]) -> list[dict]:
    return [
        {
            "블록": row["블록"],
            "조립단계": row["조립단계"],
            "작업 패키지": row["작업 패키지"],
            "주 작업": row["주 작업"],
            "참조 항목 수": row["참조 항목 수"],
            "송선코드": row.get("송선코드", ""),
            "담당 조직": row["담당 조직"],
        }
        for row in instruction_rows
    ]


def _collect_model_parts(model_hierarchy: list[dict]) -> list[dict]:
    parts = [
        item
        for item in model_hierarchy
        if item.get("type") in {"Part", "Assembly"} and item.get("node_code")
    ]
    if parts:
        return parts
    return [
        {
            "type": "Part",
            "node_code": component["model_id"],
            "name": component["model_name"],
            "design_structure": block["design_structure"],
            "model_type": component["model_type"],
            "path": f"FALLBACK/{block['block_code']}/{component['model_id']}",
            "organization": block["organization"],
            "revision": "R00",
        }
        for block in _block_blueprints()
        for stage in block["stages"]
        for component in stage["components"]
    ]


def _build_part_input_rows(block_division_item: dict, full_model_rows: list[dict]) -> list[dict]:
    source_rows = block_division_item.get("logical_rows") or full_model_rows
    part_rows: list[dict] = []
    for index, row in enumerate(source_rows, start=1):
        grand_block = _assign_grand_block(row, index)
        part_rows.append(
            {
                "노드코드": row.get("노드코드", row.get("모델ID", f"PART-{index:03d}")),
                "노드명": row.get("노드명", row.get("모델명", f"파트 {index:03d}")),
                "설계구조": row.get("설계구조", "선체"),
                "모델타입": row.get("모델타입", row.get("SFD 타입", "모델 파트")),
                "소조블록": _sub_block_code(grand_block, index),
                "중조블록": _mid_block_code(grand_block, index),
                "대조블록": grand_block,
                "PE블록": _assign_pe_block(grand_block),
            }
        )
    return part_rows


def _make_mbom_row(
    *,
    project_name: str,
    assembly_level: str,
    stage_name: str,
    item_code: str,
    item_name: str,
    parent_code: str,
    grand_block: str,
    pe_block: str,
    sub_block: str,
    mid_block: str,
    design_structure: str,
    family: str,
    source_model: str,
    send_code: str,
    view_note: str,
) -> dict:
    send_from, send_to = _split_send_code(send_code)
    return {
        "프로젝트": project_name,
        "조립레벨": assembly_level,
        "MBOM 단계": stage_name,
        "블록": grand_block or pe_block or item_code,
        "소조블록": sub_block,
        "중조블록": mid_block,
        "대조블록": grand_block,
        "PE블록": pe_block,
        "상위품목코드": parent_code,
        "송선코드": send_code,
        "송선From": send_from,
        "송선To": send_to,
        "설계구조": design_structure,
        "품목군": family,
        "품목코드": item_code,
        "품목명": item_name,
        "원천 모델": source_model,
        "구성 view": view_note,
    }


def _assign_grand_block(item: dict, index: int) -> str:
    raw_block = item.get("논리 블록") or item.get("블록힌트") or item.get("대조블록힌트") or ""
    block_map = {
        "BLOCK-109": "BLOCK-102",
        "BLOCK-152": "BLOCK-103",
        "BLOCK-221": "BLOCK-104",
        "BLOCK-301": "BLOCK-105",
    }
    if raw_block in block_map:
        return block_map[raw_block]
    if raw_block.startswith("BLOCK-10"):
        return raw_block
    return f"BLOCK-{102 + ((index - 1) % 4):03d}"


def _sub_block_code(grand_block: str, index: int) -> str:
    return f"SB-{grand_block.removeprefix('BLOCK-')}-{((index - 1) // 2) + 1:02d}"


def _mid_block_code(grand_block: str, index: int) -> str:
    return f"MB-{grand_block.removeprefix('BLOCK-')}-{((index - 1) // 4) + 1:02d}"


def _assign_pe_block(grand_block: str) -> str:
    mapping = {
        "BLOCK-102": "10A",
        "BLOCK-103": "10A",
        "BLOCK-104": "10B",
    }
    return mapping.get(grand_block, "")


def _send_code_for(stage_name: str, item_code: str) -> str:
    if stage_name == "파트":
        return "R1-R1"
    if stage_name == "소조":
        return "R1-C5" if _stable_number(item_code) % 2 == 0 else "R2-C6"
    if stage_name == "중조":
        return "C5-C8" if _stable_number(item_code) % 2 == 0 else "C6-C8"
    if stage_name == "대조":
        return "C8-B1" if item_code in {"BLOCK-102", "BLOCK-104"} else "C8-B2"
    if stage_name == "PE":
        return "B1-G9" if item_code == "10A" else "B2-G9"
    return "G9-DK"


def _split_send_code(send_code: str) -> tuple[str, str]:
    if "-" not in send_code:
        return send_code, send_code
    send_from, send_to = send_code.split("-", 1)
    return send_from, send_to


def _stable_number(text: str) -> int:
    return sum(ord(char) for char in text)


def _block_blueprints() -> list[dict]:
    return [
        _make_block(
            "BLOCK-101",
            "선수 브라켓 소조 블록",
            "선체",
            "선체설계팀",
            [
                ("소조", "Sub assembly", [("BRKT-101-01", "선수 브라켓 01", "브라켓"), ("FRM-101-01", "선수 프레임 01", "프레임"), ("WEB-101-01", "선수 웹 01", "웹")]),
            ],
        ),
        _make_block(
            "BLOCK-102",
            "선미 패널 소조 블록",
            "선체",
            "선체설계팀",
            [
                ("소조", "Sub assembly", [("PLT-102-01", "선미 패널 플레이트 01", "플레이트"), ("BRKT-102-01", "선미 브라켓 01", "브라켓"), ("FACE-102-01", "선미 페이스플레이트 01", "페이스 플레이트")]),
            ],
        ),
        _make_block(
            "BLOCK-103",
            "저판 소조 블록",
            "선체",
            "선체설계팀",
            [
                ("소조", "Sub assembly", [("PLT-103-01", "저판 플레이트 01", "플레이트"), ("STF-103-01", "저판 스티프너 01", "스티프너"), ("WEB-103-01", "저판 웹 01", "웹")]),
            ],
        ),
        _make_block(
            "BLOCK-104",
            "현측 중조 블록",
            "선체",
            "선체설계팀",
            [
                ("중조", "Semi final assembly", [("PNL-104-01", "현측 패널 조립 01", "패널"), ("GDR-104-01", "현측 거더 조립 01", "거더"), ("FRM-104-01", "현측 프레임 조립 01", "프레임 어셈블리")]),
            ],
        ),
        _make_block(
            "BLOCK-105",
            "저판 중조 블록",
            "선체",
            "선체설계팀",
            [
                ("중조", "Semi final assembly", [("PNL-105-01", "저판 패널 조립 01", "패널"), ("GDR-105-01", "저판 거더 조립 01", "거더"), ("BLHD-105-01", "저판 격벽 조립 01", "격벽 어셈블리")]),
            ],
        ),
        _make_block(
            "BLOCK-106",
            "기관실 철의 중조 블록",
            "의장-철의",
            "철의설계팀",
            [
                ("중조", "Semi final assembly", [("FND-106-01", "기관실 기초 조립 01", "파운데이션"), ("BED-106-01", "메인엔진 베드 조립 01", "베드"), ("SUP-106-01", "기관실 서포트 조립 01", "서포트")]),
            ],
        ),
        _make_block(
            "BLOCK-107",
            "현측 대조 블록",
            "선체",
            "선체설계팀",
            [
                ("대조", "Final assembly", [("BLK-107-FA", "현측 블록 최종 조립", "블록 어셈블리"), ("NDT-107-01", "현측 NDT 검사 패키지", "검사 패키지"), ("INS-107-01", "현측 최종검사 패키지", "검사 패키지")]),
            ],
        ),
        _make_block(
            "BLOCK-108",
            "저판 대조 블록",
            "선체",
            "선체설계팀",
            [
                ("대조", "Final assembly", [("BLK-108-FA", "저판 블록 최종 조립", "블록 어셈블리"), ("NDT-108-01", "저판 NDT 검사 패키지", "검사 패키지"), ("INS-108-01", "저판 최종검사 패키지", "검사 패키지")]),
            ],
        ),
        _make_block(
            "BLOCK-109",
            "기관실 대조 블록",
            "의장-철의",
            "철의설계팀",
            [
                ("대조", "Final assembly", [("BLK-109-FA", "기관실 블록 최종 조립", "블록 어셈블리"), ("AT-109-01", "기관실 A/T 패키지", "검사 패키지"), ("INS-109-01", "기관실 최종검사 패키지", "검사 패키지")]),
            ],
        ),
        _make_block(
            "BLOCK-110",
            "선수 PE 블록",
            "선체",
            "탑재설계팀",
            [
                ("PE", "Pre-Erection", [("PE-110-01", "선수 탑재 인터페이스", "탑재 인터페이스"), ("PE-110-02", "선수 탑재 정렬 패드", "탑재 정렬 패드"), ("PE-110-03", "선수 탑재 용접 조인트", "탑재 조인트")]),
            ],
        ),
    ]


def _make_block(
    block_code: str,
    block_name: str,
    design_structure: str,
    organization: str,
    stages: list[tuple[str, str, list[tuple[str, str, str]]]],
) -> dict:
    stage_rows: list[dict] = []
    for stage_name, model_type, components in stages:
        stage_code = _stage_code(stage_name)
        stage_rows.append(
            {
                "stage_code": stage_code,
                "stage_name": stage_name,
                "model_type": model_type,
                "components": [
                    {"model_id": model_id, "model_name": model_name, "model_type": component_type}
                    for model_id, model_name, component_type in components
                ],
            }
        )
    return {
        "block_code": block_code,
        "block_name": block_name,
        "design_structure": design_structure,
        "organization": organization,
        "stages": stage_rows,
    }


def _build_support_item(mbom_row: dict) -> dict:
    support_map = {
        "파이프류": ("SUPPORT-SCAFFOLD", "작업 발판", "배관 취부 작업 보조"),
        "보강재류": ("SUPPORT-JIG", "취부 지그", "보강재 정렬 및 취부 보조"),
        "강판 구조물": ("SUPPORT-LIFT", "양중 보조대", "강판 구조물 설치 보조"),
        "선체 구조물": ("SUPPORT-STAND", "임시 지지대", "구조물 인양 및 고정 보조"),
        "배관류": ("SUPPORT-RACK", "배관 작업대", "배관 취부 및 정렬 보조"),
        "전장류": ("SUPPORT-CABLE", "케이블 작업대", "케이블 정리 및 설치 보조"),
        "기계/기자재": ("SUPPORT-LIFT", "설비 설치 보조대", "기자재 설치 보조"),
        "목의류": ("SUPPORT-CART", "내장 작업 카트", "내장 자재 이동 보조"),
    }
    item_code, item_name, purpose = support_map.get(
        mbom_row["품목군"],
        ("SUPPORT-GENERAL", "작업 보조물", "작업 수행 보조"),
    )
    package_name = f"{mbom_row.get('송선To', '-')}-{mbom_row['MBOM 단계']}-{mbom_row['품목코드']}"
    return {
        "프로젝트": mbom_row["프로젝트"],
        "블록": mbom_row["블록"],
        "조립단계": mbom_row["MBOM 단계"],
        "조립레벨": mbom_row.get("조립레벨", ""),
        "상위품목코드": mbom_row.get("상위품목코드", ""),
        "소조블록": mbom_row.get("소조블록", ""),
        "중조블록": mbom_row.get("중조블록", ""),
        "대조블록": mbom_row.get("대조블록", mbom_row["블록"]),
        "PE블록": mbom_row.get("PE블록", ""),
        "송선코드": mbom_row.get("송선코드", ""),
        "송선From": mbom_row.get("송선From", ""),
        "송선To": mbom_row.get("송선To", ""),
        "설계구조": mbom_row["설계구조"],
        "작업 패키지": package_name,
        "WBOM 구분": "작업 지원",
        "품목코드": f"{mbom_row['품목코드']}-{item_code}",
        "품목명": item_name,
        "모델ID": mbom_row["원천 모델"],
        "모델타입": mbom_row["품목군"],
        "작업 목적": purpose,
        "비고": "배 자체와 무관한 작업 보조 항목",
    }


def _default_organization(design_structure: str) -> str:
    mapping = {
        "선체": "선체설계팀",
        "의장-철의": "철의설계팀",
        "의장-목의": "목의설계팀",
        "의장-배관": "배관설계팀",
        "의장-전장": "전장설계팀",
        "의장-기계": "기계설계팀",
    }
    return mapping.get(design_structure, "설계부")


def _suggest_logical_block(item: dict) -> str:
    path = item.get("path", "")
    node_code = item.get("node_code", "")
    if "SIDE-SHELL" in path:
        return "BLOCK-109"
    if "BOTTOM-SHELL" in path:
        return "BLOCK-152"
    if "LONGITUDINAL" in path or "STIFFENER" in node_code:
        return "BLOCK-221"
    return "BLOCK-301"


def _to_sfd_type(item: dict) -> str:
    model_type = item.get("model_type", "")
    if item.get("type") == "Part":
        return f"Surface {model_type}"
    return f"Surface {item.get('type', 'Model')}"


def _suggest_block_reason(item: dict) -> str:
    path = item.get("path", "")
    if "SIDE-SHELL" in path:
        return "현측 외판 영역 기준"
    if "BOTTOM-SHELL" in path:
        return "저판 구조 기준"
    if "LONGITUDINAL" in path or "STIFFENER" in path:
        return "종보강재 구조 기준"
    return "선체 기본 구조 기준"


def _to_mbom_family(design_structure: str, model_type: str) -> str:
    model_type = model_type.lower()
    if design_structure == "선체":
        if any(keyword in model_type for keyword in ["브라켓", "프레임", "거더", "스티프너", "웹"]):
            return "보강재류"
        if any(keyword in model_type for keyword in ["플레이트", "패널"]):
            return "강판 구조물"
        return "선체 구조물"
    if design_structure == "의장-배관":
        return "배관류"
    if design_structure == "의장-전장":
        return "전장류"
    if design_structure == "의장-목의":
        return "목의류"
    return "기계/기자재"


def _to_work_purpose(family_name: str) -> str:
    mapping = {
        "보강재류": "소부재 정렬 및 취부",
        "강판 구조물": "패널/판계 조립",
        "선체 구조물": "블록 조립 및 검사",
        "배관류": "배관 스풀 조립 및 설치",
        "전장류": "전장 설치 및 결선",
        "기계/기자재": "기자재 설치 및 정렬",
        "목의류": "내장 구조 조립",
    }
    return mapping.get(family_name, "현장 작업 수행")


def _to_primary_work(package_name: str) -> str:
    if package_name == "파트":
        return "파트 선별 및 소조 투입"
    if package_name == "소조" or package_name.endswith("-소조"):
        return "소부재 조립"
    if package_name == "중조" or package_name.endswith("-중조"):
        return "중간 조립체 제작"
    if package_name == "대조" or package_name.endswith("-대조"):
        return "블록 최종 조립 및 검사"
    return "탑재 준비 및 현장 연계"


def _to_preparation_items(package_name: str) -> str:
    if package_name == "PE" or package_name.endswith("-PE"):
        return "도장 완료 확인, 탑재 인터페이스 확인, 양중 계획 검토"
    if package_name == "대조" or package_name.endswith("-대조"):
        return "A/T, PT·MT·UT, 정도 확인, Final Inspection 준비"
    if package_name == "중조" or package_name.endswith("-중조"):
        return "치공구, 취부 지그, 중간 조립 자재 준비"
    if package_name == "파트":
        return "절단 자재, 부재 선별, 송선 투입 코드 확인"
    return "절단 자재, 소부재, 취부 지그 준비"


def _to_work_team(package_name: str) -> str:
    if package_name == "PE" or package_name.endswith("-PE"):
        return "탑재생산팀"
    if package_name == "대조" or package_name.endswith("-대조"):
        return "블록생산팀"
    if package_name == "중조" or package_name.endswith("-중조"):
        return "중조립팀"
    return "소조립팀"


def _stage_code(stage_name: str) -> str:
    mapping = {"소조": "SUB", "중조": "SFA", "대조": "FA", "PE": "PE"}
    return mapping[stage_name]
