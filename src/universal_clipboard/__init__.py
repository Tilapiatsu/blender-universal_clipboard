bl_info = {
    "name": "Universal Clipboard",
    "author": "Tilapiatsu",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "description": "Allows to copy/cut and paste mesh from one object to another",
    "category": "Edit",
}

from . import operators, ui

modules = (operators, ui)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in reversed(modules):
        m.unregister()
