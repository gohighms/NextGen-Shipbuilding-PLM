from src.features.tag_management.tag_generator import generate_tags_from_attributes, generate_tags_from_text
from src.features.tag_management.registry_repository import TagRegistryRepository
from src.features.tag_management.tag_rules import build_tag_name


def test_build_tag_name_uses_expected_pattern() -> None:
    assert build_tag_name("principal_dimensions.loa_m", 299.0) == "SB-DIM-LOA-299-0"


def test_generate_tags_from_attributes_creates_tag_rows() -> None:
    result = generate_tags_from_attributes(
        {
            "principal_dimensions": {"loa_m": 299.0},
            "machinery": {"main_engine": "ME-GI"},
        }
    )

    assert result["tags"] == [
        {
            "section": "machinery",
            "field_name": "machinery.main_engine",
            "value": "ME-GI",
            "tag_name": "SB-MAC-MENG-ME-GI",
        },
        {
            "section": "principal_dimensions",
            "field_name": "principal_dimensions.loa_m",
            "value": 299.0,
            "tag_name": "SB-DIM-LOA-299-0",
        },
    ]


def test_generate_tags_from_text_extracts_and_builds_tags() -> None:
    result = generate_tags_from_text(
        "LNG 운반선, 화물창 용적 241,000 cbm, 주기관 ME-GI, "
        "서비스 속력 19.5 knots, 전장 299.0 m, 선폭 46.4 m, 만재흘수 11.5 m."
    )

    tag_names = [item["tag_name"] for item in result["tags"]]
    assert "SB-BAS-SHIPTYPE-LNGC" in tag_names
    assert "SB-CGO-CAPA-241000" in tag_names
    assert "SB-MAC-MENG-ME-GI" in tag_names
    assert "SB-PRF-SSPD-19-5" not in tag_names


def test_registry_repository_saves_and_lists_items(tmp_path) -> None:
    repository = TagRegistryRepository(tmp_path)
    result = generate_tags_from_attributes(
        {
            "principal_dimensions": {"loa_m": 299.0},
            "machinery": {"main_engine": "ME-GI"},
        }
    )

    repository.save(source_type="saved_spec", source_name="Sample Spec", result=result)
    items = repository.list_all()

    assert len(items) == 1
    assert items[0]["source_name"] == "Sample Spec"
    assert items[0]["tag_count"] == 2
