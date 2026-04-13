from src.features.spec_search.attribute_utils import flatten_attributes
from src.features.spec_search.query_parser import extract_attributes_from_text
from src.features.tag_management.tag_rules import build_tag_name, is_taggable_field


def generate_tags_from_text(spec_text: str) -> dict:
    attributes = extract_attributes_from_text(spec_text)
    return generate_tags_from_attributes(attributes)


def generate_tags_from_attributes(attributes: dict) -> dict:
    flat_attributes = flatten_attributes(attributes)
    tags = []

    for field_name, value in flat_attributes.items():
        if not is_taggable_field(field_name):
            continue
        tags.append(
            {
                "section": field_name.split(".", 1)[0],
                "field_name": field_name,
                "value": value,
                "tag_name": build_tag_name(field_name, value),
            }
        )

    tags.sort(key=lambda item: item["tag_name"])
    return {
        "attributes": attributes,
        "flat_attributes": flat_attributes,
        "tags": tags,
    }
