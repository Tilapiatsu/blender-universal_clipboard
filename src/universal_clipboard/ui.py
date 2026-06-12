import bpy


class VIEW3D_PT_clipboard(bpy.types.Panel):
    bl_label = "Geometry Clipboard"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Clipboard"

    def draw(self, context):

        layout = self.layout

        layout.operator("uclipboard.copy")
        layout.operator("uclipboard.cut")
        layout.operator("uclipboard.paste")


classes = (VIEW3D_PT_clipboard,)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
