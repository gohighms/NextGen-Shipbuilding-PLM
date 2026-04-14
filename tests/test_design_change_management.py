from src.features.design_change_management.repository import DesignChangeRepository
from src.features.design_change_management.service import (
    build_assumed_current_project_model,
    build_change_scenario,
)


def test_build_assumed_current_project_model_adds_progressed_nodes() -> None:
    model_draft = {
        "current_project_name": "HD9001",
        "source_project_name": "HD1001",
        "based_on_model_id": "MODEL-HD1001-001",
        "discipline": "선체/의장 통합",
        "current_project_attributes": {"machinery": {"main_engine": "ME-GI"}},
        "model_hierarchy": [
            {"path": "PROJECT/HD9001/HULL", "type": "Discipline"},
        ],
    }

    result = build_assumed_current_project_model(model_draft)

    assert result["project_name"] == "HD9001"
    assert any(item["path"] == "PROJECT/HD9001/OUTFIT/ELECTRIC" for item in result["model_hierarchy"])


def test_build_change_scenario_returns_impacts_and_revisions() -> None:
    assumed_model = {
        "project_name": "HD9001",
        "base_model_id": "MODEL-HD1001-001",
        "model_hierarchy": [
            {"path": "PROJECT/HD9001/OUTFIT/MACHINERY/ENGINE-ROOM", "type": "Zone", "name": "Engine Room"},
            {"path": "PROJECT/HD9001/OUTFIT/ELECTRIC/MSBD-01", "type": "Equipment", "name": "Switchboard 01"},
        ],
    }

    result = build_change_scenario(
        assumed_model=assumed_model,
        pos_draft={"draft_id": "POS-DRAFT-001"},
        request_title="주기관 변경",
        request_reason="선주 요청",
        target_field="machinery.main_engine",
        before_value="ME-GI",
        after_value="X-DF 2.1",
        requester="기본설계1부",
        urgency="상",
    )

    assert result["project_name"] == "HD9001"
    assert result["impact_rows"]
    assert result["revision_rows"][0]["Rev"] == "Rev.00"


def test_design_change_repository_saves_and_lists_items(tmp_path) -> None:
    repository = DesignChangeRepository(tmp_path)
    request = {
        "project_name": "HD9001",
        "request_title": "주기관 변경",
        "request_reason": "선주 요청",
        "target_field": "machinery.main_engine",
        "before_value": "ME-GI",
        "after_value": "X-DF 2.1",
        "requester": "기본설계1부",
        "urgency": "상",
        "impact_rows": [],
        "revision_rows": [],
    }

    repository.save(request)
    items = repository.list_all()

    assert len(items) == 1
    assert items[0]["request_title"] == "주기관 변경"
