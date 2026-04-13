import re


ENGINE_KEYWORDS = [
    "ME-GI",
    "X-DF",
    "DFDE",
    "WinGD",
    "MAN B&W",
]


def extract_attributes_from_text(spec_text: str) -> dict:
    text = " ".join(spec_text.split())
    principal_dimensions = {}
    performance = {}
    cargo_system = {}
    machinery = {}
    basic_info = {}

    loa = _extract_number(text, r"(?:LOA|전장)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:m|meter|meters)")
    if loa is not None:
        principal_dimensions["loa_m"] = loa

    breadth = _extract_number(text, r"(?:Breadth|선폭|폭)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:m|meter|meters)")
    if breadth is not None:
        principal_dimensions["breadth_m"] = breadth

    draft = _extract_number(text, r"(?:Draft|흘수|만재흘수)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:m|meter|meters)")
    if draft is not None:
        principal_dimensions["draft_m"] = draft

    speed = _extract_number(text, r"(?:service speed|서비스 속력|속력)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:knots|knot|kt)")
    if speed is not None:
        performance["service_speed_kn"] = speed

    cargo_capacity = _extract_number(
        text,
        r"(?:cargo capacity|화물창 용적)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:cubic meters|cbm|m3)",
    )
    if cargo_capacity is not None:
        cargo_system["cargo_capacity_m3"] = int(cargo_capacity)

    teu_capacity = _extract_number(
        text,
        r"(?:container capacity)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:TEU)?",
    )
    if teu_capacity is None:
        teu_capacity = _extract_number(text, r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*TEU")
    if teu_capacity is not None:
        cargo_system["capacity_teu"] = int(teu_capacity)

    for keyword in ENGINE_KEYWORDS:
        if keyword.lower() in text.lower():
            machinery["main_engine"] = keyword
            break
    if "주기관" in text and "main_engine" not in machinery:
        machinery["main_engine"] = "확인 필요"

    ship_type = _extract_ship_type(text)
    if ship_type:
        basic_info["ship_type_hint"] = ship_type

    attributes = {}
    if basic_info:
        attributes["basic_info"] = basic_info
    if principal_dimensions:
        attributes["principal_dimensions"] = principal_dimensions
    if performance:
        attributes["performance"] = performance
    if cargo_system:
        attributes["cargo_system"] = cargo_system
    if machinery:
        attributes["machinery"] = machinery

    return attributes


def _extract_number(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _extract_ship_type(text: str) -> str:
    lowered = text.lower()
    if "lng" in lowered:
        return "LNGC"
    if "lpg" in lowered:
        return "LPGC"
    if "container" in lowered:
        return "CONTAINER"
    if "crude oil" in lowered or "vlcc" in lowered:
        return "VLCC"
    return ""
