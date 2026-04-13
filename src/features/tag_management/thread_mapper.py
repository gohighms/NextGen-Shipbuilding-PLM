STAGE_LABELS = {
    "POS": "POS",
    "MODEL": "모델",
    "BOM": "BOM",
    "PRODUCTION": "생산",
}


def build_thread_rows(tags: list[dict]) -> list[dict]:
    rows = []

    for tag in tags:
        field_name = tag["field_name"]
        tag_name = tag["tag_name"]

        if field_name.startswith("principal_dimensions."):
            rows.extend(
                [
                    _row("POS", "선형/기본 계획 사양", tag_name, "기본 선형 및 주요치수 계획 검토"),
                    _row("MODEL", "선체 기본 모델", tag_name, "선체 3D 기준 모델 반영"),
                    _row("BOM", "선체 강재 BOM", tag_name, "주요치수 기반 자재 산출"),
                    _row("PRODUCTION", "선체 블록 생산 계획", tag_name, "블록 분할 및 생산 일정 반영"),
                ]
            )

        if field_name == "machinery.main_engine":
            rows.extend(
                [
                    _row("POS", "기관부 사양서", tag_name, "주기관 패키지 사양 확정"),
                    _row("MODEL", "기관실 모델", tag_name, "주기관 배치 및 간섭 검토"),
                    _row("BOM", "기관 기자재 BOM", tag_name, "주기관 관련 기자재 구성 확정"),
                    _row("PRODUCTION", "기관실 탑재 계획", tag_name, "설치 및 시운전 순서 반영"),
                ]
            )

        if field_name.startswith("cargo_system."):
            rows.extend(
                [
                    _row("POS", "화물 시스템 사양서", tag_name, "화물 시스템 설계 기준 확정"),
                    _row("MODEL", "화물창/화물처리 모델", tag_name, "화물창 및 배관 모델 반영"),
                    _row("BOM", "화물 시스템 BOM", tag_name, "탱크 및 화물 처리 기자재 반영"),
                    _row("PRODUCTION", "화물 구역 생산 계획", tag_name, "설치/시공 순서 반영"),
                ]
            )

        if field_name.startswith("basic_info."):
            rows.extend(
                [
                    _row("POS", "프로젝트 기본 기준서", tag_name, "선종 및 기본 기준 관리"),
                ]
            )

    deduped = []
    seen = set()
    for row in rows:
        row_key = (row["단계"], row["연결 대상"], row["기준 TAG"])
        if row_key in seen:
            continue
        seen.add(row_key)
        deduped.append(row)

    return deduped


def summarize_thread_counts(rows: list[dict]) -> dict:
    summary = {stage: 0 for stage in STAGE_LABELS}
    for row in rows:
        summary[row["단계"]] += 1
    return summary


def _row(stage: str, target_name: str, tag_name: str, note: str) -> dict:
    return {
        "단계": stage,
        "연결 대상": target_name,
        "기준 TAG": tag_name,
        "설명": note,
    }
