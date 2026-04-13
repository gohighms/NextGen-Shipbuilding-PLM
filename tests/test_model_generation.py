from src.features.model_generation.draft_repository import ModelDraftRepository
from src.features.model_generation.service import (
    build_model_document_text,
    build_model_draft,
    recommend_models,
)


def test_recommend_models_prefers_more_matching_tags() -> None:
    pos_draft_item = {
        "tags": [
            {"tag_name": "SB-BAS-SHIPTYPE-LNGC"},
            {"tag_name": "SB-MAC-MENG-ME-GI"},
            {"tag_name": "SB-CGO-CAPA-241000"},
        ]
    }
    model_items = [
        {
            "model_id": "MODEL-1",
            "title": "A",
            "discipline": "통합",
            "tags": ["SB-BAS-SHIPTYPE-LNGC", "SB-MAC-MENG-ME-GI", "SB-CGO-CAPA-241000"],
            "ebom_items": [],
            "model_notes": [],
        },
        {
            "model_id": "MODEL-2",
            "title": "B",
            "discipline": "통합",
            "tags": ["SB-BAS-SHIPTYPE-LNGC"],
            "ebom_items": [],
            "model_notes": [],
        },
    ]

    result = recommend_models(pos_draft_item, model_items, top_k=2)

    assert result[0]["model_id"] == "MODEL-1"
    assert result[0]["score"] == 3


def test_build_model_draft_copies_core_fields() -> None:
    pos_draft_item = {"draft_id": "POS-DRAFT-001", "title": "POS 초안", "tags": []}
    model_item = {
        "model_id": "MODEL-001",
        "title": "기존 모델",
        "discipline": "통합",
        "ebom_items": [],
        "model_notes": [],
    }

    draft = build_model_draft(pos_draft_item, model_item)

    assert draft["new_model_id"] == "POS-DRAFT-001-MODEL-DRAFT"
    assert draft["based_on_model_id"] == "MODEL-001"
    assert draft["title"] == "기존 모델 - 편집설계 초안"


def test_build_model_document_text_has_document_shape() -> None:
    text = build_model_document_text(
        {
            "model_id": "MODEL-001",
            "title": "기존 모델",
            "discipline": "통합",
            "ebom_items": [{"item_code": "A", "description": "Hull block assembly", "quantity": 2}],
            "model_notes": ["기존 실적선 기준"],
        },
        change_note="편집설계 메모",
    )

    assert "EDIT DESIGN MODEL / EBOM SUMMARY" in text
    assert "Model ID   : MODEL-001" in text
    assert "Change Note" in text


def test_model_draft_repository_saves_and_lists_items(tmp_path) -> None:
    repository = ModelDraftRepository(tmp_path)
    draft = {
        "new_model_id": "POS-DRAFT-001-MODEL-DRAFT",
        "source_pos_draft_id": "POS-DRAFT-001",
        "source_name": "POS 초안",
        "based_on_model_id": "MODEL-001",
        "title": "기존 모델 - 편집설계 초안",
        "discipline": "통합",
        "tags": [],
        "ebom_items": [],
        "model_notes": [],
    }

    repository.save(draft, change_note="편집설계 메모")
    items = repository.list_all()

    assert len(items) == 1
    assert items[0]["based_on_model_id"] == "MODEL-001"
