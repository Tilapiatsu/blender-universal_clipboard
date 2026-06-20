import bpy


class VIEW3D_MT_clipboard(bpy.types.Menu):
    bl_label = "Clipboard"

    def draw(self, context):

        layout = self.layout

        layout.operator("view3d.ucopy")
        layout.operator("view3d.ucut")
        layout.operator("view3d.upaste")


def menu_draw(self, context):
    layout = self.layout
    layout.separator()
    layout.menu(VIEW3D_MT_clipboard.__name__, text=VIEW3D_MT_clipboard.bl_label)


classes = (VIEW3D_MT_clipboard,)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.VIEW3D_MT_edit_mesh.append(menu_draw)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu_draw)


def unregister():
    from bpy.utils import unregister_class

    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_draw)
    bpy.types.VIEW3D_MT_edit_mesh.remove(menu_draw)

    for cls in reversed(classes):
        unregister_class(cls)
