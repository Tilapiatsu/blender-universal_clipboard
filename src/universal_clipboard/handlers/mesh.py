import bpy
import bmesh

from typing import Union
from .base import P_ClipboardHandler
from ..clipboard import ClipboardData, GLOBAL_CLIPBOARD
from ..serializer.mesh import Serializer, Deserializer


class ClipboardHandler(P_ClipboardHandler):
    @classmethod
    def copy(cls, context) -> tuple[int, str]:

        global GLOBAL_CLIPBOARD

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        selected: set[int] = {v.index for v in bm.verts if v.select}
        geometry = Serializer.serialize_geometry(bm, selected)

        bpy.ops.object.mode_set(mode="OBJECT")

        GLOBAL_CLIPBOARD = ClipboardData(
            object_type="MESH",
            obj=obj,
            geometry=geometry,
            vertex_groups=Serializer.serialize_vertex_groups(obj, selected),
            shape_keys=Serializer.serialize_shape_keys(obj, selected),
            materials=Serializer.serialize_materials(obj, selected),
            attributes=Serializer.serialize_attributes(obj, selected),
        )

        bpy.ops.object.mode_set(mode="EDIT")

        return 0, f"{len(selected)} elements copied"

    @classmethod
    def cut(cls, context) -> tuple[int, str]:
        msg = cls.copy(context)
        if msg[0] == -1:
            return msg
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        geom = [v for v in bm.verts if v.select] + [e for e in bm.edges if e.select] + [f for f in bm.faces if f.select]
        bmesh.ops.delete(bm, geom=geom, context="FACES")
        bmesh.update_edit_mesh(obj.data)

        return 0, msg[1].replace("copied", "cuted")

    @classmethod
    def paste(cls, context) -> tuple[int, str]:

        global GLOBAL_CLIPBOARD

        if GLOBAL_CLIPBOARD is None:
            return -1, "Clipboard is Empty"

        obj = context.edit_object
        if not obj:
            return -1, "Need to be in edit mode"

        bpy.ops.mesh.select_all(action="DESELECT")

        GLOBAL_CLIPBOARD.init_mesh_remap()
        Deserializer.ensure_attributes_on_object(obj, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_geometry(obj, GLOBAL_CLIPBOARD)

        bpy.ops.object.mode_set(mode="OBJECT")
        Deserializer.deserialize_materials(obj, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_shape_keys(obj, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_vertex_groups(obj, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_attributes(obj, GLOBAL_CLIPBOARD)
        bpy.ops.object.mode_set(mode="EDIT")

        return 0, f"{len(GLOBAL_CLIPBOARD.geometry.verts)} elements pasted"

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
    def _create_object_from_bmesh(cls, bmesh):
        mesh = bpy.data.meshes.new("UCB_clipboard_mesh")
        bmesh.normal_update()
        bmesh.to_mesh(mesh)
        clipboard = bpy.data.objects.new("UCB_clipboard", mesh)
        bpy.context.scene.collection.objects.link(clipboard)
