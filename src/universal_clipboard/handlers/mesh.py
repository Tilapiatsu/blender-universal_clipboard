import bpy
import bmesh

from .base import P_ClipboardHandler
from ..clipboard import ClipboardData, GLOBAL_CLIPBOARD


class ClipboardHandler(P_ClipboardHandler):
    @classmethod
    def copy(cls, context):

        global GLOBAL_CLIPBOARD

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        selected = {v.index for v in bm.verts if v.select}
        fragment = extract_selected_bmesh(bm)

        GLOBAL_CLIPBOARD = ClipboardData(
            object_type="MESH",
            mesh_data=serialize_bmesh(fragment),
            vertex_groups=copy_vertex_groups(obj, selected),
            shape_keys=copy_shape_keys(obj, selected),
        )

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
        bm = bmesh.from_edit_mesh(obj.data)
        src = rebuild_bmesh(GLOBAL_CLIPBOARD.mesh_data)
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

        src.free()

        bmesh.update_edit_mesh(obj.data)


def rebuild_bmesh(data):

    bm = bmesh.new()

    verts = []

    for co in data["verts"]:
        verts.append(bm.verts.new(co))

    bm.verts.ensure_lookup_table()

    for face in data["faces"]:
        print(face)
        try:
            bm.faces.new([verts[i] for i in face])
        except:
            pass

    for v1, v2 in data["edges"]:
        print(v1, v2)
        try:
            bm.edges.new((verts[v1], verts[v2]))
        except:
            pass

    return bm


def extract_selected_bmesh(src_bm):

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


def serialize_bmesh(bm):

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

    print(result)

    return result


def copy_shape_keys(obj, selected_verts):

    result = {}

    if obj.data.shape_keys is None:
        return result

    for key in obj.data.shape_keys.key_blocks:
        result[key.name] = {idx: tuple(key.data[idx].co) for idx in selected_verts}

    return result


def copy_vertex_groups(obj, selected_verts):

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
