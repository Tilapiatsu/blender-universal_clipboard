import bpy
import bmesh

from typing import Union
from .base import P_ClipboardHandler
from ..clipboard import ClipboardData, GLOBAL_CLIPBOARD
from ..serializer.mesh import Serializer, Deserializer


class ClipboardHandler(P_ClipboardHandler):
    @classmethod
    def copy(cls, context):

        global GLOBAL_CLIPBOARD

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        selected: set[int] = {v.index for v in bm.verts if v.select}
        fragment = cls._extract_selected_bmesh(bm)

        GLOBAL_CLIPBOARD = ClipboardData(
            object_type="MESH",
            geometry=Serializer.serialize_geometry(fragment),
            vertex_groups=Serializer.serialize_vertex_groups(obj, selected),
            shape_keys=Serializer.serialize_shape_keys(obj, selected),
            materials=Serializer.serialize_materials(obj, selected),
            attributes=Serializer.serialize_attributes(obj.data, selected),
        )

        # mesh = bpy.data.meshes.new("UCB_clipboard_mesh")
        # fragment.normal_update()
        # fragment.to_mesh(mesh)
        # clipboard = bpy.data.objects.new("UCB_clipboard", mesh)
        # context.scene.collection.objects.link(clipboard)

        fragment.free()

    @classmethod
    def cut(cls, context):
        cls.copy(context)
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        geom = [v for v in bm.verts if v.select] + [e for e in bm.edges if e.select] + [f for f in bm.faces if f.select]
        bmesh.ops.delete(bm, geom=geom, context="FACES")
        bmesh.update_edit_mesh(obj.data)

    @classmethod
    def paste(cls, context):

        global GLOBAL_CLIPBOARD

        if GLOBAL_CLIPBOARD is None:
            return

        obj = context.edit_object
        if not obj:
            "need to be in edit mode"
            return

        bm = bmesh.from_edit_mesh(obj.data)
        src = Deserializer.deserialize_geometry(GLOBAL_CLIPBOARD)
        src.verts.ensure_lookup_table()
        vert_map = {}

        for v in src.verts:
            nv = bm.verts.new(v.co)
            vert_map[v] = nv

        bm.verts.ensure_lookup_table()

        for f in src.faces:
            try:
                bm.faces.new([vert_map[v] for v in f.verts])
            except:
                pass

        for e in src.edges:
            try:
                bm.edges.new((vert_map[e.verts[0]], vert_map[e.verts[1]]))
            except:
                pass

        Deserializer.deserialize_attributes(bm, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_shape_keys(bm, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_vertex_groups(bm, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_materials(bm, GLOBAL_CLIPBOARD)

        src.free()

        bmesh.update_edit_mesh(obj.data)

    @classmethod
    def _rebuild_bmesh(cls, data: dict):

        bm = bmesh.new()

        verts = []

        for co in data["verts"]:
            verts.append(bm.verts.new(co))

        bm.verts.ensure_lookup_table()

        for face in data["faces"]:
            try:
                bm.faces.new([verts[i] for i in face])
            except:
                pass

        sharp_layer = bm.edges.layers.bool.get("sharp_edge")

        for edges in data["edges"]:
            try:
                ne = bm.edges.new((verts[edges["verts"][0]], verts[edges["verts"][1]]))
                ne[sharp_layer] = edges["sharp"]
            except:
                pass

        return bm

    @classmethod
    def _extract_selected_bmesh(cls, src_bm: bmesh.types.BMesh) -> bmesh.types.BMesh:
        dst_bm = bmesh.new()
        vert_map = {}
        selected_verts = {v for v in src_bm.verts if v.select}

        for v in src_bm.verts:
            if v.select:
                nv = dst_bm.verts.new(v.co)
                vert_map[v] = nv

        dst_bm.verts.ensure_lookup_table()

        for e in src_bm.edges:
            if all(v in selected_verts for v in e.verts):
                dst_bm.edges.new((vert_map[e.verts[0]], vert_map[e.verts[1]]))

        for f in src_bm.faces:
            if all(v in selected_verts for v in f.verts):
                try:
                    dst_bm.faces.new([vert_map[v] for v in f.verts])
                except ValueError:
                    pass

        return dst_bm

    @classmethod
    def _serialize_bmesh(cls, bm: bmesh.types.BMesh):
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()

        vert_indices = {v: i for i, v in enumerate(bm.verts)}
        sharp_layer = bm.edges.layers.bool.get("sharp_edge")
        crease_layer = bm.edges.layers.float.get("crease_edge")

        print(sharp_layer)
        print(crease_layer)

        result = {
            "verts": [tuple(v.co) for v in bm.verts],
            "edges": [
                {
                    "verts": (vert_indices[e.verts[0]], vert_indices[e.verts[1]]),
                    "seam": e.seam,
                    "sharp": e[sharp_layer] if sharp_layer else False,
                    "crease": e[crease_layer] if crease_layer else False,
                }
                for e in bm.edges
            ],
            "faces": [[vert_indices[v] for v in f.verts] for f in bm.faces],
        }

        return result

    @classmethod
    def _copy_shape_keys(cls, obj: bpy.types.Object, selected_verts):
        result = {}
        if obj.data.shape_keys is None:
            return result

        for key in obj.data.shape_keys.key_blocks:
            result[key.name] = {idx: tuple(key.data[idx].co) for idx in selected_verts}

        return result

    @classmethod
    def _ensure_attributes_on_bmesh(cls, bm: bmesh.types.BMesh, attributes: list[dict]):
        for a in attributes:
            domain = getattr(bm, cls._get_bmesh_domain(a["domain"]))
            if not domain:
                continue

            match a["data_type"]:
                case "FLOAT":
                    attr = domain.layers.float.get(a["name"])
                    if not attr:
                        domain.layers.float.new(a["name"])

                case "INT":
                    attr = domain.layers.int.get(a["name"])
                    if not attr:
                        domain.layers.int.new(a["name"])

                case "BOOLEAN":
                    attr = domain.layers.bool.get(a["name"])
                    if not attr:
                        domain.layers.bool.new(a["name"])

                case "FLOAT_VECTOR":
                    attr = domain.layers.float_vector.get(a["name"])
                    if not attr:
                        domain.layers.float_vector.new(a["name"])

                case "FLOAT_COLOR":
                    attr = domain.layers.float_color.get(a["name"])
                    if not attr:
                        domain.layers.float_color.new(a["name"])

                case "QUATERNION":
                    pass

                case "FLOAT4X4":
                    pass

                case "STRING":
                    attr = domain.layers.string.get(a["name"])
                    if not attr:
                        domain.layers.string.new(a["name"])

                case "INT8":
                    attr = domain.layers.int.get(a["name"])
                    if not attr:
                        domain.layers.int.new(a["name"])

                case "INT16_2D":
                    attr = domain.layers.int.get(a["name"])
                    if not attr:
                        domain.layers.int.new(a["name"])

                case "INT32_2D":
                    attr = domain.layers.int.get(a["name"])
                    if not attr:
                        domain.layers.int.new(a["name"])

                case "FLOAT2":
                    attr = domain.layers.float.get(a["name"])
                    if not attr:
                        domain.layers.float.new(a["name"])

                case "BYTE_COLOR":
                    attr = domain.layers.color.get(a["name"])
                    if not attr:
                        domain.layers.color.new(a["name"])
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
