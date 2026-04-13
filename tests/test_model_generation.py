from src.features.model_generation.draft_repository import ModelDraftRepository
from src.features.model_generation.service import (
    build_hierarchy_rows,
    build_model_draft,
    build_model_reuse_suggestions,
    find_models_for_project,
    summarize_model_similarity,
)


def test_find_models_for_project_filters_by_selected_project() -> None:
    selected_project = {"spec_id": "LNGC-241K-001"}
    model_items = [
        {"model_id": "MODEL-1", "source_spec_id": "LNGC-241K-001"},
        {"model_id": "MODEL-2", "source_spec_id": "LNGC-174K-001"},
    ]

    result = find_models_for_project(selected_project, model_items)

    assert [item["model_id"] for item in result] == ["MODEL-1"]


def test_summarize_model_similarity_scores_matching_fields() -> None:
    current_attributes = {
        "basic_info": {"ship_type": "LNGC"},
        "principal_dimensions": {"loa_m": 299.0},
        "machinery": {"main_engine": "ME-GI"},
    }
    model_item = {
        "model_profile": {
            "basic_info": {"ship_type": "LNGC"},
            "principal_dimensions": {"loa_m": 299.0},
            "machinery": {"main_engine": "ME-GI"},
        }
    }

    result = summarize_model_similarity(current_attributes, model_item)

    assert result["matched_count"] == 3
    assert result["score"] == 1.0


def test_build_model_reuse_suggestions_returns_limited_groups() -> None:
    current_attributes = {
        "principal_dimensions": {"loa_m": 299.0, "breadth_m": 46.4, "draft_m": 11.5},
        "machinery": {"main_engine": "ME-GI"},
        "cargo_system": {"cargo_capacity_m3": 241000, "cargo_tank_system": "GTT Mark III Flex"},
    }
    model_item = {
        "source_project_name": "HD1001",
        "model_profile": {
            "principal_dimensions": {"loa_m": 299.0, "breadth_m": 46.4, "draft_m": 11.5},
            "machinery": {"main_engine": "ME-GI"},
            "cargo_system": {"cargo_capacity_m3": 241000, "cargo_tank_system": "GTT Mark III Flex"},
        },
        "model_hierarchy": [
            {"path": "PROJECT/HD1001/HULL", "type": "Discipline"},
            {"path": "PROJECT/HD1001/OUTFIT/PIPING", "type": "System"},
            {"path": "PROJECT/HD1001/OUTFIT/ELECTRIC", "type": "System"},
        ],
    }

    result = build_model_reuse_suggestions(current_attributes, model_item)

    assert len(result) <= 3
    assert result[0]["review_status"] in {"재활용 추천", "조건부 검토"}


def test_build_model_draft_filters_selected_paths() -> None:
    current_spec = {"project_name": "HD9001", "attributes": {}}
    selected_project = {"spec_id": "LNGC-241K-001", "project_name": "HD1001"}
    model_item = {
        "model_id": "MODEL-001",
        "title": "기준 모델",
        "discipline": "통합",
        "ebom_items": [],
        "model_notes": [],
        "model_hierarchy": [
            {"path": "PROJECT/HD1001/HULL", "type": "Discipline"},
            {"path": "PROJECT/HD1001/HULL/BLOCK-B01", "type": "Block"},
            {"path": "PROJECT/HD1001/OUTFIT/PIPING", "type": "System"},
        ],
    }

    draft = build_model_draft(
        current_spec,
        selected_project,
        model_item,
        approved_paths=["PROJECT/HD1001/HULL"],
    )

    assert draft["new_model_id"] == "MODEL-HD9001-001"
    assert draft["model_hierarchy"][0]["path"] == "PROJECT/HD9001/HULL"
    assert all("/OUTFIT/PIPING" not in item["path"] for item in draft["model_hierarchy"])


def test_build_hierarchy_rows_adds_descriptive_columns() -> None:
    rows = build_hierarchy_rows(
        [
            {
                "path": "PROJECT/HD1001/HULL/BLOCK-B01",
                "type": "Block",
                "node_code": "BLOCK-B01",
                "name": "Fore Block",
                "organization": "선체설계부",
                "designer": "홍길동",
                "created_on": "2026-03-01",
                "revision": "R01",
            }
        ]
    )

    assert rows[0]["노드코드"] == "BLOCK-B01"
    assert rows[0]["생성조직"] == "선체설계부"
    assert rows[0]["담당설계"] == "홍길동"


def test_model_draft_repository_saves_and_lists_items(tmp_path) -> None:
    repository = ModelDraftRepository(tmp_path)
    draft = {
        "new_model_id": "MODEL-HD9001-001",
        "source_project_spec_id": "LNGC-241K-001",
        "source_project_name": "HD1001",
        "current_project_name": "HD9001",
        "source_pos_draft_id": "POS-DRAFT-001",
        "based_on_model_id": "MODEL-001",
        "title": "HD9001 모델 편집 초안",
        "discipline": "통합",
        "model_hierarchy": [],
    }

    repository.save(draft, change_note="모델 편집설계 시작")
    items = repository.list_all()

    assert len(items) == 1
    assert items[0]["based_on_model_id"] == "MODEL-001"
