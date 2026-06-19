import bpy
import bmesh

from ..clipboard import ClipboardData, AttributeData, MeshGeometry

ATTRIBUTE_FIELDS = {
    "FLOAT": "value",
    "INT": "value",
    "INT8": "value",
    "INT16_2D": "value",
    "INT32_2D": "value",
    "BOOLEAN": "value",
    "FLOAT_VECTOR": "vector",
    "FLOAT_COLOR": "color",
    "BYTE_COLOR": "color",
    "FLOAT2": "vector",
    "STRING": "value",
    "QUATERNION": "value",
    "FLOAT4X4": "vector",
}


class Serializer:
    @classmethod
    def serialize_geometry(cls, bm: bmesh.types.BMesh, selected_verts: set[int]) -> MeshGeometry:
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()

        mg = MeshGeometry()

        vert_indices = {v: i for i, v in enumerate(bm.verts) if i in selected_verts}
        edges_verts = [e for e in bm.edges if set([e.verts[0].index, e.verts[1].index]).issubset(selected_verts)]
        faces_verts = [f for f in bm.faces if set([v.index for v in f.verts]).issubset(selected_verts)]

        mg.verts = {v.index: tuple(v.co) for v in bm.verts if v.index in selected_verts}
        mg.edges = {e.index: (vert_indices[e.verts[0]], vert_indices[e.verts[1]], e.index) for e in edges_verts}
        mg.faces = [[vert_indices[v] for v in f.verts] for f in faces_verts]

        return mg

    @classmethod
    def serialize_attributes(cls, obj: bpy.types.Object, selected_verts: set[int]) -> dict:
        mesh = obj.data
        result = {}
        selected_edges = cls._get_selected_domain(mesh, selected_verts, "EDGE")
        selected_faces = cls._get_selected_domain(mesh, selected_verts, "FACE")
        selected_corners = {}

        for poly in mesh.polygons:
            if poly.index not in selected_faces:
                continue

            for local_corner, loop_idx in enumerate(range(poly.loop_start, poly.loop_start + poly.loop_total)):
                selected_corners[(poly.index, local_corner)] = loop_idx

        for attr in mesh.attributes:
            if attr.name.startswith(".") or attr.name in ["position"]:
                continue
            attribute_data = AttributeData(name=attr.name, domain=attr.domain, data_type=attr.data_type)
            cls._serialize_attribute(
                attr, attribute_data, selected_verts, selected_edges, selected_faces, selected_corners
            )
            result[attr.name] = attribute_data

        return result

    @classmethod
    def _serialize_attribute(
        cls,
        attr,
        attribute_data: AttributeData,
        selected_verts: set[int],
        selected_edges: set[int],
        selected_faces: set[int],
        selected_corners: dict,
    ):
        field = ATTRIBUTE_FIELDS[attr.data_type]

        selected = {"POINT": selected_verts, "EDGE": selected_edges, "FACE": selected_faces, "CORNER": selected_corners}

        # print(attr.name, attr.domain, attr.data_type, selected[attr.domain])

        if attr.domain == "CORNER":
            for key, idx in selected[attr.domain].items():
                value = cls._serialize_attribute_value(attr.data[idx])
                attribute_data[key] = value
        else:
            for idx in selected[attr.domain]:
                value = cls._serialize_attribute_value(attr.data[idx])
                attribute_data[idx] = value

    @staticmethod
    def _serialize_attribute_value(elem):
        result = {}

        for prop in elem.bl_rna.properties:
            if prop.identifier == "rna_type":
                continue

            try:
                value = getattr(elem, prop.identifier)

                if hasattr(value, "__iter__") and not isinstance(value, str):
                    value = tuple(value)

                result = value

            except Exception:
                pass

        return result

    @classmethod
    def serialize_shape_keys(cls, obj: bpy.types.Object, selected_verts: set[int]) -> dict:
        result = {}
        keys = obj.data.shape_keys
        if not keys:
            return result

        for block in keys.key_blocks:
            result[block.name] = {src_idx: tuple(block.data[src_idx].co) for src_idx in selected_verts}

        return result

    @classmethod
    def serialize_vertex_groups(cls, obj: bpy.types.Object, selected_verts: set[int]):
        result = {}
        for vg in obj.vertex_groups:
            weights = {}

            for idx in selected_verts:
                try:
                    weights[idx] = vg.weight(idx)
                except RuntimeError:
                    pass

            if weights:
                result[vg.name] = weights

        return result

    @classmethod
    def serialize_materials(cls, obj: bpy.types.Object, selected_verts: set[int]):
        # materials = [mat.name if mat else None for mat in obj.data.materials]
        # face_materials = [poly.material_index for poly in obj.data.polygons]

        materials = {}
        face_materials = {}

        sel_verts = set(selected_verts)

        if not len(obj.data.materials):
            return {}

        for i, poly in enumerate(obj.data.polygons):
            if not set(poly.vertices).issubset(sel_verts):
                continue
            mat_index = poly.material_index
            face_materials[i] = mat_index

            if mat_index not in materials.keys():
                materials[mat_index] = obj.data.materials[mat_index].name

        result = {"materials": materials, "face_materials": face_materials}

        return result

    @classmethod
    def _get_selected_domain(cls, mesh: bpy.types.Mesh, selected_verts: set[int], domain: str) -> set[int]:
        match domain:
            case "POINT":
                return selected_verts
            case "EDGE":
                selected = set({})
                for e in mesh.edges:
                    verts = [v for v in e.vertices]
                    if not set(verts).issubset(selected_verts):
                        continue

                    selected.update([e.index])

                return selected
            case "FACE":
                selected = set({})
                for f in mesh.polygons:
                    face = [v for v in f.vertices]
                    if not set(face).issubset(selected_verts):
                        continue
                    selected.update([f.index])

                return selected
            case "CORNER":
                return selected_verts
            case _:
                return selected_verts


class Deserializer:
    @classmethod
    def deserialize_geometry(cls, bm: bmesh.types.BMesh, clipboard: ClipboardData) -> bmesh.types.BMesh:
        verts = {}
        data = clipboard.geometry

        remap_data = clipboard.remap

        if not remap_data:
            return

        for i, co in data.verts.items():
            verts[i] = bm.verts.new(co)

        bm.verts.ensure_lookup_table()
        bm.verts.index_update()

        for src_idx, v in verts.items():
            remap_data.vertex[src_idx] = v.index

        created_faces = []
        for face in data.faces:
            try:
                new_face = bm.faces.new([verts[i] for i in face])
                created_faces.append(new_face)
            except:
                pass

        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        bm.edges.ensure_lookup_table()
        bm.edges.index_update()

        for src_idx, f in enumerate(created_faces):
            remap_data.face[src_idx] = f.index
            for corner_idx, loop in enumerate(f.loops):
                remap_data.corner[(f.index, corner_idx)] = loop.index

        edges_of_created_face = {}

        for f in created_faces:
            for e in f.edges:
                if e in edges_of_created_face.values():
                    continue
                edges_of_created_face[(e.verts[0], e.verts[1])] = e

        created_edges = {}
        for src_idx, edge in data.edges.items():
            edge_verts = (verts[edge[0]], verts[edge[1]])
            try:
                new_edge = bm.edges.new(edge_verts)
                created_edges[src_idx] = new_edge
            except:
                if edge_verts in edges_of_created_face.keys():
                    created_edges[src_idx] = edges_of_created_face[edge_verts]
                elif tuple(reversed(edge_verts)) in edges_of_created_face.keys():
                    created_edges[src_idx] = edges_of_created_face[tuple(reversed(edge_verts))]
                else:
                    print("edge not found")

        bm.edges.ensure_lookup_table()
        bm.edges.index_update()

        for src_idx, e in created_edges.items():
            remap_data.edge[src_idx] = e.index

        bm.free()

    @classmethod
    def deserialize_attributes(cls, obj: bpy.types.Object, clipboard: ClipboardData):
        src_attributes = clipboard.attributes
        dst_attributes = obj.data.attributes
        assert clipboard.remap

        # print([a.name for a in dst_attributes])

        bpy.ops.object.mode_set(mode="OBJECT")
        for name, a in src_attributes.items():
            if (
                name not in dst_attributes.keys()
                or dst_attributes[name].domain != a.domain
                or dst_attributes[name].data_type != a.data_type
            ):
                cls.ensure_attributes_on_object(obj, clipboard)
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.object.mode_set(mode="OBJECT")

            field = ATTRIBUTE_FIELDS[a.data_type]
            src_keys = src_attributes[name].data.keys()
            # print(src_attributes[name].data)
            match a.domain:
                case "POINT":
                    for src_idx, dst_idx in clipboard.remap.vertex.items():
                        if src_idx not in src_keys:
                            continue
                        setattr(dst_attributes[name].data[dst_idx], field, src_attributes[name].data[src_idx])

                case "EDGE":
                    for src_idx, dst_idx in clipboard.remap.edge.items():
                        if src_idx not in src_keys:
                            continue

                        # print(f"set attribute {name} : {src_idx} -> {dst_idx}={src_attributes[name].data[src_idx]}")
                        setattr(dst_attributes[name].data[dst_idx], field, src_attributes[name].data[src_idx])

                case "FACE":
                    pass
                case "CORNER":
                    pass
                case _:
                    pass

        bpy.ops.object.mode_set(mode="EDIT")

    @classmethod
    def deserialize_shape_keys(cls, obj: bpy.types.Object, clipboard: ClipboardData):
        pass

    @classmethod
    def deserialize_vertex_groups(cls, obj: bpy.types.Object, clipboard: ClipboardData):
        pass

    @classmethod
    def deserialize_materials(cls, obj: bpy.types.Object, clipboard: ClipboardData):
        pass

    @classmethod
    def ensure_attributes_on_object(cls, obj: bpy.types.Object, clipboard: ClipboardData):
        attributes = clipboard.attributes

        bpy.ops.object.mode_set(mode="OBJECT")

        for name, a in attributes.items():
            if name not in obj.data.attributes.keys():
                print(f"creating attribute {name}")
                obj.data.attributes.new(name=name, type=a.data_type, domain=a.domain)
                if not len(obj.data.attributes[name].data):
                    continue
                if name in ["sharp_edge", "uv_seam"]:
                    setattr(obj.data.attributes[name].data[0], "value", True)
                if name in ["material_index"]:
                    setattr(obj.data.attributes[name].data[0], "value", 0)
                continue

            if obj.data.attributes[name].data_type != a.data_type or obj.data.attributes[name].domain != a.domain:
                obj.data.attributes.new(name=f"{name}_pasted", type=a.data_type, domain=a.domain)

        obj.data.update()
        bpy.ops.object.mode_set(mode="EDIT")

    @classmethod
    def ensure_attributes_on_bmesh(cls, bm: bmesh.types.BMesh, clipboard: ClipboardData):
        attributes = clipboard.attributes
        for name, a in attributes.items():
            domain = getattr(bm, cls._get_bmesh_domain(a.domain))
            if not domain:
                continue

            match a.data_type:
                case "FLOAT":
                    attr = domain.layers.float.get(name)
                    if not attr:
                        domain.layers.float.new(name)

                case "INT":
                    attr = domain.layers.int.get(name)
                    if not attr:
                        domain.layers.int.new(name)

                case "BOOLEAN":
                    attr = domain.layers.bool.get(name)
                    if not attr:
                        domain.layers.bool.new(name)

                case "FLOAT_VECTOR":
                    attr = domain.layers.float_vector.get(name)
                    if not attr:
                        domain.layers.float_vector.new(name)

                case "FLOAT_COLOR":
                    attr = domain.layers.float_color.get(name)
                    if not attr:
                        domain.layers.float_color.new(name)

                case "QUATERNION":
                    pass

                case "FLOAT4X4":
                    pass

                case "STRING":
                    attr = domain.layers.string.get(name)
                    if not attr:
                        domain.layers.string.new(name)

                case "INT8":
                    attr = domain.layers.int.get(name)
                    if not attr:
                        domain.layers.int.new(name)

                case "INT16_2D":
                    attr = domain.layers.int.get(name)
                    if not attr:
                        domain.layers.int.new(name)

                case "INT32_2D":
                    attr = domain.layers.int.get(name)
                    if not attr:
                        domain.layers.int.new(name)

                case "FLOAT2":
                    attr = domain.layers.float.get(name)
                    if not attr:
                        domain.layers.float.new(name)

                case "BYTE_COLOR":
                    attr = domain.layers.color.get(name)
                    if not attr:
                        domain.layers.color.new(name)
                case _:
                    pass

    @classmethod
    def _get_bmesh_domain(cls, domain_name: str) -> str:
        match domain_name:
            case "POINT":
                return "verts"
            case "EDGE":
                return "edges"
            case "FACE":
                return "faces"
            case "CORNER":
                return "loops"
            case "CURVE":
                return "curves"
            case "INSTANCE":
                return "instance"
            case "LAYER":
                return "layer"
            case _:
                return ""

    @classmethod
    def _get_edge_from_verts(cls, bm: bmesh.types.BMesh, edge_verts: tuple[int, int]):
        for e in bm.edges:
            if set(edge_verts).issubset(e.verts):
                return e

        return None
