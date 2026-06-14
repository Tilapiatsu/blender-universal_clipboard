import bpy
import bmesh

from ..clipboard import ClipboardData

ATTRIBUTE_FIELDS = {
    "FLOAT": "value",
    "INT": "value",
    "INT8": "value",
    "INT16_2D": "vector",
    "INT32_2D": "vector",
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
    def serialize_geometry(cls, bm: bmesh.types.BMesh) -> dict:
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()

        vert_indices = {v: i for i, v in enumerate(bm.verts)}

        result = {
            "verts": [tuple(v.co) for v in bm.verts],
            "edges": [(vert_indices[e.verts[0]], vert_indices[e.verts[1]]) for e in bm.edges],
            "faces": [[vert_indices[v] for v in f.verts] for f in bm.faces],
        }

        return result

    @classmethod
    def serialize_attributes(cls, mesh: bpy.types.Mesh, selected_verts: set[int]) -> dict:
        result = {}

        for attr in mesh.attributes:
            result[attr.name] = cls._serialize_attribute(attr, selected_verts)

        return result

    @classmethod
    def _serialize_attribute(cls, attr, selected_verts: set[int]) -> dict:
        field = ATTRIBUTE_FIELDS[attr.data_type]
        values = []
        for i, elem in enumerate(attr.data):
            if i not in selected_verts:
                continue

            value = getattr(elem, field)
            if hasattr(value, "__iter__"):
                value = tuple(value)

            values.append(value)

        return {"domain": attr.domain, "data_type": attr.data_type, "values": values}

    @classmethod
    def serialize_shape_keys(cls, obj: bpy.types.Object, selected_verts: set[int]) -> dict:
        result = {}
        keys = obj.data.shape_keys
        if not keys:
            return result

        for block in keys.key_blocks:
            result[block.name] = [tuple(block.data[src_idx].co) for src_idx in selected_verts]

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
        face_materials = []

        sel_verts = set(selected_verts)
        for poly in obj.data.polygons:
            if not set(poly.vertices).issubset(sel_verts):
                continue

            mat_index = poly.material_index
            face_materials.append(mat_index)

            if mat_index not in materials.keys():
                materials[mat_index] = obj.data.materials[mat_index].name

        result = {"materials": materials, "face_materials": face_materials}

        return result


class Deserializer:
    @classmethod
    def deserialize_geometry(cls, clipboard: ClipboardData) -> bmesh.types.BMesh:
        bm = bmesh.new()
        verts = []
        data = clipboard.geometry

        for co in data["verts"]:
            verts.append(bm.verts.new(co))

        bm.verts.ensure_lookup_table()

        for face in data["faces"]:
            try:
                bm.faces.new([verts[i] for i in face])
            except:
                pass

        for edges in data["edges"]:
            try:
                bm.edges.new((verts[edges["verts"][0]], verts[edges["verts"][1]]))
            except:
                pass

        return bm

    @classmethod
    def deserialize_attributes(cls, bm: bmesh.types.BMesh, clipboard: ClipboardData):
        pass

    @classmethod
    def deserialize_shape_keys(cls, bm: bmesh.types.BMesh, clipboard: ClipboardData):
        pass

    @classmethod
    def deserialize_vertex_groups(cls, bm: bmesh.types.BMesh, clipboard: ClipboardData):
        pass

    @classmethod
    def deserialize_materials(cls, bm: bmesh.types.BMesh, clipboard: ClipboardData):
        pass
