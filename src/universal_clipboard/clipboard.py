from dataclasses import dataclass

GLOBAL_CLIPBOARD = None


@dataclass
class ClipboardData:
    object_type: str
    mesh_data: dict
    vertex_groups: dict
    shape_keys: dict
