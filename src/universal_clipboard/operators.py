import bpy
from .handlers import curve, grease_pencil, mesh, pointcloud


class UCLIPBOARD_OT_copy(bpy.types.Operator):
    bl_idname = "uclipboard.copy"
    bl_label = "Copy Selection"

    def execute(self, context):

        mesh.ClipboardHandler.copy(context)

        return {"FINISHED"}


class UCLIPBOARD_OT_cut(bpy.types.Operator):
    bl_idname = "uclipboard.cut"
    bl_label = "Cut Selection"

    def execute(self, context):

        mesh.ClipboardHandler.cut(context)

        return {"FINISHED"}


class UCLIPBOARD_OT_paste(bpy.types.Operator):
    bl_idname = "uclipboard.paste"
    bl_label = "Paste Selection"

    def execute(self, context):

        mesh.ClipboardHandler.paste(context)

        return {"FINISHED"}


classes = (UCLIPBOARD_OT_copy, UCLIPBOARD_OT_cut, UCLIPBOARD_OT_paste)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
