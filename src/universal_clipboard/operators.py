import bpy
from .handlers import curve, grease_pencil, mesh, pointcloud


class UCLIPBOARD_OT_copy(bpy.types.Operator):
    """
    Copy selected elements in clipboard
    """

    bl_idname = "view3d.ucopy"
    bl_label = "Copy Selection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        mesh.ClipboardHandler.copy(context)

        return {"FINISHED"}


class UCLIPBOARD_OT_cut(bpy.types.Operator):
    """
    Cut selected elements in clipboard
    """

    bl_idname = "view3d.ucut"
    bl_label = "Cut Selection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        mesh.ClipboardHandler.cut(context)

        return {"FINISHED"}


class UCLIPBOARD_OT_paste(bpy.types.Operator):
    """
    Paste elements from clipboard
    """

    bl_idname = "view3d.upaste"
    bl_label = "Paste Selection"
    bl_options = {"REGISTER", "UNDO"}

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
