from dataclasses import dataclass, field


@dataclass
class SpecDocument:
    spec_id: str
    project_name: str
    ship_type: str = ""
    text: str = ""
    attributes: dict = field(default_factory=dict)
