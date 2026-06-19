import bmesh
from dataclasses import dataclass
from typing import Any, Union

GLOBAL_CLIPBOARD = None


@dataclass
class MeshRemap:
    """
    This class is mapping the indices for each domain from source object to pasted object :
    vertex : dict[src_index] = dst_index
    edge : dict[src_index] = dst_index
    face : dict[src_index] = dst_index
    corner : dict[(src_face, local_corner)] = dst_loop_index
    """

    vertex: dict[int, int]
    edge: dict[int, int]
    face: dict[int, int]
    corner: dict[tuple[int, int], int]
    material_id: dict[int, int]

    def __init__(self) -> None:
        self.vertex = {}
        self.edge = {}
        self.face = {}
        self.corner = {}
        self.material_id = {}


@dataclass
class MeshGeometry:
    """
    This class stores the indices of the copied mesh
    """

    verts: dict
    edges: dict
    faces: dict

    def __init__(self) -> None:
        self.verts = {}
        self.edges = {}
        self.faces = {}


@dataclass
class AttributeData:
    name: str
    domain: str
    data_type: str
    data: dict

    def __init__(self, name: str, domain: str, data_type: str) -> None:
        self.name = name
        self.domain = domain
        self.data_type = data_type
        self.data = {}

    def __getitem__(self, key: Any) -> Any:
        if key not in self.data.keys():
            return None

        return self.data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.data[key] = value

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()


@dataclass
class ClipboardData:
    object_type: str
    geometry: MeshGeometry
    vertex_groups: dict
    shape_keys: dict
    materials: dict
    attributes: dict[str, AttributeData]
    remap: Union[None, MeshRemap] = None

    def init_mesh_remap(self) -> None:
        self.remap = MeshRemap()

    def init_mesh_geometry(self) -> None:
        self.geometry = MeshGeometry()
