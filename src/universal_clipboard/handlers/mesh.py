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
        geometry = Serializer.serialize_geometry(bm, selected)

        bpy.ops.object.mode_set(mode="OBJECT")

        GLOBAL_CLIPBOARD = ClipboardData(
            object_type="MESH",
            geometry=geometry,
            vertex_groups=Serializer.serialize_vertex_groups(obj, selected),
            shape_keys=Serializer.serialize_shape_keys(obj, selected),
            materials=Serializer.serialize_materials(obj, selected),
            attributes=Serializer.serialize_attributes(obj, selected),
        )

        bpy.ops.object.mode_set(mode="EDIT")

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

        GLOBAL_CLIPBOARD.init_mesh_remap()
        Deserializer.ensure_attributes_on_object(obj, GLOBAL_CLIPBOARD)
        bm = bmesh.from_edit_mesh(obj.data)
        # TODO : Need to modify deserialize_geometry to also write the attributes at the same time ? need to remap the
        # source and target mesh properly
        Deserializer.deserialize_geometry(bm, GLOBAL_CLIPBOARD)

        bmesh.update_edit_mesh(obj.data)

        bpy.ops.object.mode_set(mode="OBJECT")
        Deserializer.deserialize_attributes(obj, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_shape_keys(obj, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_vertex_groups(obj, GLOBAL_CLIPBOARD)
        Deserializer.deserialize_materials(obj, GLOBAL_CLIPBOARD)
        bpy.ops.object.mode_set(mode="EDIT")

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
