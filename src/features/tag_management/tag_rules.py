SECTION_CODES = {
    "basic_info": "BAS",
    "principal_dimensions": "DIM",
    "machinery": "MAC",
    "cargo_system": "CGO",
}


FIELD_CODES = {
    "basic_info.ship_type_hint": "SHIPTYPE",
    "basic_info.ship_type": "SHIPTYPE",
    "basic_info.yard": "YARD",
    "basic_info.cargo_tank_count": "TANKCNT",
    "basic_info.bay_plan_type": "BAYPLAN",
    "principal_dimensions.loa_m": "LOA",
    "principal_dimensions.breadth_m": "BREADTH",
    "principal_dimensions.draft_m": "DRAFT",
    "machinery.main_engine": "MENG",
    "machinery.propulsion_type": "PROP",
    "cargo_system.cargo_capacity_m3": "CAPA",
    "cargo_system.capacity_teu": "TEU",
    "cargo_system.cargo_tank_system": "TANKSYS",
    "cargo_system.deadweight_ton": "DWT",
}


TAGGABLE_FIELDS = {
    "basic_info.ship_type_hint",
    "basic_info.ship_type",
    "basic_info.yard",
    "basic_info.cargo_tank_count",
    "basic_info.bay_plan_type",
    "principal_dimensions.loa_m",
    "principal_dimensions.breadth_m",
    "principal_dimensions.draft_m",
    "machinery.main_engine",
    "machinery.propulsion_type",
    "cargo_system.cargo_capacity_m3",
    "cargo_system.capacity_teu",
    "cargo_system.cargo_tank_system",
    "cargo_system.deadweight_ton",
}


def build_tag_name(field_name: str, value) -> str:
    section_name = field_name.split(".", 1)[0]
    section_code = SECTION_CODES.get(section_name, "GEN")
    field_code = FIELD_CODES.get(field_name, field_name.split(".")[-1].upper())
    normalized_value = normalize_tag_value(value)
    return f"SB-{section_code}-{field_code}-{normalized_value}"


def is_taggable_field(field_name: str) -> bool:
    return field_name in TAGGABLE_FIELDS


def normalize_tag_value(value) -> str:
    if isinstance(value, float):
        value = f"{value:.1f}"
    value_text = str(value).upper()
    sanitized = []
    for char in value_text:
        if char.isalnum():
            sanitized.append(char)
        elif char in {".", "-", "_", " "}:
            sanitized.append("-")

    normalized = "".join(sanitized).strip("-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized or "UNKNOWN"
