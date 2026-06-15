from dataclasses import dataclass, field
from typing import Any, Union

GLOBAL_CLIPBOARD = None


@dataclass
class MeshRemap:
    vertex: dict
    edge: dict
    face: dict
    corner: dict

    def __init__(self) -> None:
        self.vertex = {}
        self.edge = {}
        self.face = {}
        self.corner = {}


@dataclass
class AttributeData:
    name: str
    domain: str
    data_type: str
    value: dict

    def __init__(self, name: str, domain: str, data_type: str) -> None:
        self.name = name
        self.domain = domain
        self.data_type = data_type
        self.value = {}

    def __getitem__(self, key: Any) -> Any:
        if key not in self.value.keys():
            return None

        return self.value[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.value[key] = value

    def keys(self):
        return self.value.keys()

    def values(self):
        return self.value.values()

    def items(self):
        return self.value.items()


@dataclass
class ClipboardData:
    object_type: str
    geometry: dict
    vertex_groups: dict
    shape_keys: dict
    materials: dict
    attributes: dict[str, AttributeData]
    remap: Union[None, MeshRemap] = None

    def init_mesh_remap(self) -> None:
        self.remap = MeshRemap()
