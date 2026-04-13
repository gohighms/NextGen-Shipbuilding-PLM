def flatten_attributes(attributes: dict, prefix: str = "") -> dict:
    flattened = {}

    for key, value in attributes.items():
        field_name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_attributes(value, prefix=field_name))
            continue
        flattened[field_name] = value

    return flattened
