from pathlib import Path

from src.features.spec_search.attribute_utils import flatten_attributes
from src.features.spec_search.compare import compare_spec_attributes
from src.features.spec_search.models import SpecDocument
from src.features.spec_search.query_parser import extract_attributes_from_text
from src.features.spec_search.repository import SpecRepository
from src.features.spec_search.service import SpecSearchService


def test_compare_spec_attributes_returns_expected_groups() -> None:
    current = SpecDocument(
        spec_id="NEW-001",
        project_name="NEW",
        attributes={
            "principal_dimensions": {"loa_m": 300.0},
            "machinery": {"main_engine": "ME-GI"},
            "performance": {"service_speed_kn": 19.5},
        },
    )
    baseline = SpecDocument(
        spec_id="OLD-001",
        project_name="OLD",
        attributes={
            "principal_dimensions": {"loa_m": 299.0},
            "machinery": {"main_engine": "ME-GI"},
            "cargo_system": {"cargo_capacity_m3": 174000},
        },
    )

    result = compare_spec_attributes(current, baseline)

    assert result["shared_fields"] == [
        "machinery.main_engine",
        "principal_dimensions.loa_m",
    ]
    assert result["only_in_current"] == ["performance.service_speed_kn"]
    assert result["only_in_baseline"] == ["cargo_system.cargo_capacity_m3"]
    assert result["changed_fields"] == [
        {
            "field": "principal_dimensions.loa_m",
            "current": 300.0,
            "baseline": 299.0,
        }
    ]


def test_spec_search_service_finds_sample_data() -> None:
    repository = SpecRepository(Path("data/processed"))
    service = SpecSearchService(repository)

    result = service.search(
        project_name="TEST-001",
        spec_text=(
            "LNG carrier, cargo capacity 241,000 cbm, "
            "main engine ME-GI, service speed 19.5 knots, "
            "LOA 299.0 m, Breadth 46.4 m, Draft 11.5 m."
        ),
        top_k=1,
    )

    assert result["results"]
    assert result["results"][0]["spec_id"] == "LNGC-241K-001"


def test_extract_attributes_from_text_reads_major_fields() -> None:
    result = extract_attributes_from_text(
        "LNG carrier, cargo capacity 241,000 cbm, main engine ME-GI, "
        "service speed 19.5 knots, LOA 299.0 m, Breadth 46.4 m, Draft 11.5 m."
    )

    assert result == {
        "basic_info": {
            "ship_type_hint": "LNGC",
        },
        "principal_dimensions": {
            "loa_m": 299.0,
            "breadth_m": 46.4,
            "draft_m": 11.5,
        },
        "performance": {
            "service_speed_kn": 19.5,
        },
        "cargo_system": {
            "cargo_capacity_m3": 241000,
        },
        "machinery": {
            "main_engine": "ME-GI",
        },
    }


def test_flatten_attributes_supports_nested_sections() -> None:
    result = flatten_attributes(
        {
            "principal_dimensions": {"loa_m": 299.0},
            "machinery": {"main_engine": "ME-GI"},
        }
    )

    assert result == {
        "principal_dimensions.loa_m": 299.0,
        "machinery.main_engine": "ME-GI",
    }


def test_extract_attributes_from_korean_text_reads_major_fields() -> None:
    result = extract_attributes_from_text(
        "LNG 운반선, 화물창 용적 241,000 cbm, 주기관 ME-GI, "
        "서비스 속력 19.5 knots, 전장 299.0 m, 선폭 46.4 m, 만재흘수 11.5 m."
    )

    assert result == {
        "basic_info": {
            "ship_type_hint": "LNGC",
        },
        "principal_dimensions": {
            "loa_m": 299.0,
            "breadth_m": 46.4,
            "draft_m": 11.5,
        },
        "performance": {
            "service_speed_kn": 19.5,
        },
        "cargo_system": {
            "cargo_capacity_m3": 241000,
        },
        "machinery": {
            "main_engine": "ME-GI",
        },
    }
