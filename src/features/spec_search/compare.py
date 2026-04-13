from src.features.spec_search.models import SpecDocument
from src.features.spec_search.attribute_utils import flatten_attributes


def compare_spec_attributes(current: SpecDocument, baseline: SpecDocument) -> dict:
    current_attributes = flatten_attributes(current.attributes)
    baseline_attributes = flatten_attributes(baseline.attributes)

    current_keys = set(current_attributes)
    baseline_keys = set(baseline_attributes)

    shared_fields = sorted(current_keys & baseline_keys)
    only_in_current = sorted(current_keys - baseline_keys)
    only_in_baseline = sorted(baseline_keys - current_keys)

    changed_fields = []
    for field_name in shared_fields:
        current_value = current_attributes[field_name]
        baseline_value = baseline_attributes[field_name]
        if current_value != baseline_value:
            changed_fields.append(
                {
                    "field": field_name,
                    "current": current_value,
                    "baseline": baseline_value,
                }
            )

    return {
        "shared_fields": shared_fields,
        "only_in_current": only_in_current,
        "only_in_baseline": only_in_baseline,
        "changed_fields": changed_fields,
    }
