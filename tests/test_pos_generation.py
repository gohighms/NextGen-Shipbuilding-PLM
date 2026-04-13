from src.features.pos_generation.draft_repository import PosDraftRepository
from src.features.pos_generation.service import build_pos_document_text, build_pos_draft, recommend_pos_documents


def test_recommend_pos_documents_prefers_more_matching_tags() -> None:
    registry_item = {
        "tags": [
            {"tag_name": "SB-BAS-SHIPTYPE-LNGC"},
            {"tag_name": "SB-DIM-LOA-299-0"},
            {"tag_name": "SB-MAC-MENG-ME-GI"},
        ]
    }
    pos_items = [
        {
            "pos_id": "POS-1",
            "title": "A",
            "department": "기본설계팀",
            "tags": ["SB-BAS-SHIPTYPE-LNGC", "SB-DIM-LOA-299-0", "SB-MAC-MENG-ME-GI"],
            "sections": [],
        },
        {
            "pos_id": "POS-2",
            "title": "B",
            "department": "기본설계팀",
            "tags": ["SB-BAS-SHIPTYPE-LNGC"],
            "sections": [],
        },
    ]

    result = recommend_pos_documents(registry_item, pos_items, top_k=2)

    assert result[0]["pos_id"] == "POS-1"
    assert result[0]["score"] == 3


def test_build_pos_draft_copies_core_fields() -> None:
    registry_item = {"registry_id": "TAG-001", "source_name": "LNGC 241K"}
    pos_item = {
        "pos_id": "POS-001",
        "title": "기존 POS",
        "department": "기본설계팀",
        "sections": [{"section": "기관", "content": "기존 내용"}],
    }

    draft = build_pos_draft(registry_item, pos_item)

    assert draft["new_pos_id"] == "TAG-001-POS-DRAFT"
    assert draft["based_on_pos_id"] == "POS-001"
    assert draft["title"] == "기존 POS - 수정 초안"


def test_pos_draft_repository_saves_and_lists_items(tmp_path) -> None:
    repository = PosDraftRepository(tmp_path)
    draft = {
        "new_pos_id": "TAG-001-POS-DRAFT",
        "source_registry_id": "TAG-001",
        "source_name": "LNGC 241K",
        "based_on_pos_id": "POS-001",
        "title": "기존 POS - 수정 초안",
        "department": "기본설계팀",
        "tags": [],
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
            "pos_id": "POS-001",
            "title": "기존 POS",
            "department": "기본설계팀",
            "sections": [
                {"section": "기관", "content": "기관 내용"},
                {"section": "화물시스템", "content": "화물 내용"},
            ],
        },
        change_note="변경 메모",
    )

    assert "PURCHASE ORDER SPECIFICATION" in text
    assert "Document ID : POS-001" in text
    assert "기관" in text
    assert "Change Note" in text
