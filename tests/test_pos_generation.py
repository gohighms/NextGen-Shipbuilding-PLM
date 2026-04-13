from src.features.pos_generation.draft_repository import PosDraftRepository
from src.features.pos_generation.service import (
    build_pos_document_text,
    build_pos_draft,
    find_pos_documents_for_project,
)


def test_find_pos_documents_for_project_filters_by_selected_project() -> None:
    selected_project = {"spec_id": "LNGC-241K-001"}
    pos_items = [
        {"pos_id": "POS-1", "source_spec_id": "LNGC-241K-001"},
        {"pos_id": "POS-2", "source_spec_id": "LNGC-174K-001"},
    ]

    result = find_pos_documents_for_project(selected_project, pos_items)

    assert [item["pos_id"] for item in result] == ["POS-1"]


def test_build_pos_draft_copies_core_fields() -> None:
    current_spec = {
        "project_name": "HD9001",
        "attributes": {"machinery": {"main_engine": "ME-GI"}},
    }
    selected_project = {
        "spec_id": "LNGC-241K-001",
        "project_name": "HD1001",
    }
    pos_item = {
        "pos_id": "POS-001",
        "title": "기존 POS",
        "department": "영업설계팀",
        "sections": [{"section": "기관", "content": "기존 내용"}],
    }

    draft = build_pos_draft(current_spec, selected_project, pos_item)

    assert draft["new_pos_id"] == "POS-HD9001-001"
    assert draft["based_on_pos_id"] == "POS-001"
    assert draft["title"] == "HD9001 POS 편집 초안"
    assert draft["current_project_attributes"] == {"machinery": {"main_engine": "ME-GI"}}


def test_pos_draft_repository_saves_and_lists_items(tmp_path) -> None:
    repository = PosDraftRepository(tmp_path)
    draft = {
        "new_pos_id": "POS-HD9001-001",
        "source_project_spec_id": "LNGC-241K-001",
        "source_project_name": "HD1001",
        "current_project_name": "HD9001",
        "based_on_pos_id": "POS-001",
        "title": "HD9001 POS 편집 초안",
        "department": "영업설계팀",
        "sections": [{"section": "기관", "content": "기존 내용"}],
    }

    repository.save(draft, change_note="기관부 내용 수정 예정")
    items = repository.list_all()

    assert len(items) == 1
    assert items[0]["based_on_pos_id"] == "POS-001"
    assert items[0]["change_note"] == "기관부 내용 수정 예정"


def test_build_pos_document_text_includes_document_shape() -> None:
    text = build_pos_document_text(
        {
            "new_pos_id": "POS-001",
            "title": "기존 POS",
            "department": "영업설계팀",
            "sections": [
                {"section": "기관", "content": "기관 내용"},
                {"section": "화물시스템", "content": "화물 내용"},
            ],
            "_force_regenerate": True,
        },
        change_note="변경 메모",
    )

    assert "PURCHASE ORDER SPECIFICATION" in text
    assert "Document ID : POS-001" in text
    assert "기관" in text
    assert "Change Note" in text
