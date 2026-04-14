from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import date, timedelta


def build_mds_schedule(project_name: str) -> list[dict]:
    base_date = date(2026, 4, 20)
    return [
        _task("MDS-001", "영업설계 기준 확정", "영업설계팀", base_date, 12, [], "MDS", project_name),
        _task("MDS-002", "선체 기본설계", "선체설계부", base_date + timedelta(days=12), 20, ["MDS-001"], "MDS", project_name),
        _task("MDS-003", "의장 기본설계", "의장설계부", base_date + timedelta(days=16), 18, ["MDS-001"], "MDS", project_name),
        _task("MDS-004", "선체 상세설계", "선체설계부", base_date + timedelta(days=32), 22, ["MDS-002"], "MDS", project_name),
        _task("MDS-005", "의장 상세설계", "의장설계부", base_date + timedelta(days=34), 24, ["MDS-003"], "MDS", project_name),
        _task("MDS-006", "생산설계 착수", "생산설계부", base_date + timedelta(days=58), 15, ["MDS-004", "MDS-005"], "MDS", project_name),
    ]


def build_dp_schedule(project_name: str) -> list[dict]:
    base_date = date(2026, 4, 20)
    return [
        _task(
            "DP-001",
            "선체 기본설계",
            "선체설계부",
            base_date + timedelta(days=8),
            5,
            [],
            "DP",
            project_name,
            linked_mds_id="MDS-002",
            key_event="Hull Plan",
            linked_model_design="선체 기본 배치도 작성",
        ),
        _task(
            "DP-002",
            "선체 기본설계",
            "선체설계부",
            base_date + timedelta(days=13),
            5,
            ["DP-001"],
            "DP",
            project_name,
            linked_mds_id="MDS-002",
            key_event="Midship Section",
            linked_model_design="중앙단면 구조 검토",
        ),
        _task(
            "DP-003",
            "배관 기본설계",
            "배관설계부",
            base_date + timedelta(days=14),
            4,
            [],
            "DP",
            project_name,
            linked_mds_id="MDS-003",
            key_event="Pipe Routing Review",
            linked_model_design="주 배관 routing 확정",
        ),
        _task(
            "DP-004",
            "철의 기본설계",
            "철의설계부",
            base_date + timedelta(days=16),
            4,
            [],
            "DP",
            project_name,
            linked_mds_id="MDS-003",
            key_event="Foundation Plan",
            linked_model_design="기자재 foundation 계획 검토",
        ),
        _task(
            "DP-005",
            "선체 상세설계",
            "선체설계부",
            base_date + timedelta(days=22),
            6,
            ["DP-001", "DP-002"],
            "DP",
            project_name,
            linked_mds_id="MDS-004",
            key_event="Shell Expansion",
            linked_model_design="외판 전개도 작성",
        ),
        _task(
            "DP-006",
            "선체 상세설계",
            "선체설계부",
            base_date + timedelta(days=28),
            6,
            ["DP-005"],
            "DP",
            project_name,
            linked_mds_id="MDS-004",
            key_event="Block Key Plan",
            linked_model_design="블록 key plan 작성",
        ),
        _task(
            "DP-007",
            "의장 상세설계",
            "의장설계부",
            base_date + timedelta(days=24),
            6,
            ["DP-003", "DP-004"],
            "DP",
            project_name,
            linked_mds_id="MDS-005",
            key_event="Equipment Arrangement",
            linked_model_design="기자재 배치도 확정",
        ),
        _task(
            "DP-008",
            "의장 상세설계",
            "의장설계부",
            base_date + timedelta(days=30),
            5,
            ["DP-007"],
            "DP",
            project_name,
            linked_mds_id="MDS-005",
            key_event="Cable Plan",
            linked_model_design="전장 cable plan 작성",
        ),
        _task(
            "DP-009",
            "출도 준비",
            "기본설계1부",
            base_date + timedelta(days=38),
            5,
            ["DP-006", "DP-008"],
            "DP",
            project_name,
            linked_mds_id="MDS-005",
            key_event="Drawing Issue List",
            linked_model_design="출도 목록 고정",
        ),
        _task(
            "DP-010",
            "생산설계 착수 준비",
            "생산설계부",
            base_date + timedelta(days=44),
            6,
            ["DP-009"],
            "DP",
            project_name,
            linked_mds_id="MDS-006",
            key_event="Production Input Package",
            linked_model_design="생산설계 입력 패키지 준비",
        ),
    ]


def roll_dp_schedule(dp_rows: list[dict], selected_task_id: str, shift_days: int) -> list[dict]:
    rolled = deepcopy(dp_rows)
    task_map = {item["task_id"]: item for item in rolled}

    if selected_task_id not in task_map or shift_days == 0:
        return rolled

    dependents_map = _build_dependents_map(rolled)
    affected_ids = _collect_affected_ids(selected_task_id, dependents_map)

    selected_task = task_map[selected_task_id]
    selected_task["start_date"] = selected_task["start_date"] + timedelta(days=shift_days)
    selected_task["end_date"] = selected_task["end_date"] + timedelta(days=shift_days)

    ordered_rows = sorted(rolled, key=lambda item: item["start_date"])
    for row in ordered_rows:
        if row["task_id"] == selected_task_id:
            continue
        if row["task_id"] not in affected_ids:
            continue

        new_start = row["start_date"]
        for predecessor_id in row["depends_on"]:
            predecessor_end = task_map[predecessor_id]["end_date"]
            candidate_start = predecessor_end + timedelta(days=1)
            if candidate_start > new_start:
                new_start = candidate_start

        if new_start != row["start_date"]:
            duration = row["duration_days"]
            row["start_date"] = new_start
            row["end_date"] = new_start + timedelta(days=duration - 1)

    return rolled


def build_schedule_chart_rows(schedule_rows: list[dict], label: str) -> list[dict]:
    rows = []
    for item in schedule_rows:
        rows.append(
            {
                "작업ID": item["task_id"],
                "작업명": item["task_name"],
                "설계 Key Event": item.get("key_event", item["task_name"]),
                "부서": item["department"],
                "시작일": item["start_date"],
                "종료일": item["end_date"],
                "계획구분": label,
                "의존관계": ", ".join(item["depends_on"]) if item["depends_on"] else "-",
                "연계 모델 설계": item.get("linked_model_design", "-"),
                "연계 MDS": item.get("linked_mds_id", "-"),
            }
        )
    return rows


def build_overlay_rows(mds_rows: list[dict], dp_rows: list[dict]) -> list[dict]:
    mds_map = {item["task_id"]: item for item in mds_rows}
    overlay_rows = []
    for item in dp_rows:
        linked_mds_id = item.get("linked_mds_id")
        if linked_mds_id not in mds_map:
            continue
        linked_mds = mds_map[linked_mds_id]
        overlay_rows.append(
            {
                "작업ID": item["task_id"],
                "설계 Key Event": item.get("key_event", item["task_name"]),
                "MDS 작업명": linked_mds["task_name"],
                "부서": item["department"],
                "DP 시작일": item["start_date"],
                "DP 종료일": item["end_date"],
                "연계 모델 설계": item.get("linked_model_design", "-"),
            }
        )
    return overlay_rows


def build_rolling_impact_summary(base_rows: list[dict], rolled_rows: list[dict], selected_task_id: str, shift_days: int) -> dict:
    base_map = {item["task_id"]: item for item in base_rows}
    rolled_map = {item["task_id"]: item for item in rolled_rows}

    changed_rows = []
    affected_departments = set()
    for task_id, rolled_item in rolled_map.items():
        base_item = base_map[task_id]
        moved_days = (rolled_item["start_date"] - base_item["start_date"]).days
        if moved_days != 0:
            affected_departments.add(rolled_item["department"])
            changed_rows.append(
                {
                    "작업ID": task_id,
                    "설계 Key Event": rolled_item.get("key_event", rolled_item["task_name"]),
                    "부서": rolled_item["department"],
                    "연계 모델 설계": rolled_item.get("linked_model_design", "-"),
                    "기준 시작일": base_item["start_date"],
                    "롤링 시작일": rolled_item["start_date"],
                    "이동일수": moved_days,
                }
            )

    baseline_finish = max(item["end_date"] for item in base_rows)
    rolled_finish = max(item["end_date"] for item in rolled_rows)

    return {
        "selected_task_id": selected_task_id,
        "input_shift_days": shift_days,
        "changed_task_count": len(changed_rows),
        "project_finish_shift_days": (rolled_finish - baseline_finish).days,
        "affected_departments": sorted(affected_departments),
        "changed_rows": changed_rows,
    }


def _task(
    task_id: str,
    task_name: str,
    department: str,
    start: date,
    duration_days: int,
    depends_on: list[str],
    plan_type: str,
    project_name: str,
    linked_mds_id: str = "",
    key_event: str = "",
    linked_model_design: str = "",
) -> dict:
    return {
        "task_id": task_id,
        "task_name": task_name,
        "department": department,
        "start_date": start,
        "end_date": start + timedelta(days=duration_days - 1),
        "duration_days": duration_days,
        "depends_on": depends_on,
        "plan_type": plan_type,
        "project_name": project_name,
        "linked_mds_id": linked_mds_id,
        "key_event": key_event,
        "linked_model_design": linked_model_design,
    }


def _build_dependents_map(schedule_rows: list[dict]) -> dict[str, list[str]]:
    dependents_map: dict[str, list[str]] = {}
    for item in schedule_rows:
        for predecessor_id in item["depends_on"]:
            dependents_map.setdefault(predecessor_id, []).append(item["task_id"])
    return dependents_map


def _collect_affected_ids(start_task_id: str, dependents_map: dict[str, list[str]]) -> set[str]:
    affected_ids: set[str] = set()
    queue = deque([start_task_id])

    while queue:
        current = queue.popleft()
        for dependent_id in dependents_map.get(current, []):
            if dependent_id in affected_ids:
                continue
            affected_ids.add(dependent_id)
            queue.append(dependent_id)

    return affected_ids
