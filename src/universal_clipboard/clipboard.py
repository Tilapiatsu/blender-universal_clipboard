from dataclasses import dataclass

GLOBAL_CLIPBOARD = None


@dataclass
class ClipboardData:
    object_type: str
    geometry: dict
    vertex_groups: dict
    shape_keys: dict
    materials: dict
    attributes: dict
