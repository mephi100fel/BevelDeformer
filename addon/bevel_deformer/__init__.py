bl_info = {
    "name": "Bevel Deformer",
    "author": "",
    "version": (0, 1, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Bevel",
    "description": "Create lattices for selected meshes and apply lattice deform helpers.",
    "category": "Object",
    "icon": "MOD_LATTICE",
}

import bpy
import os

import bpy.utils.previews
from bpy.props import StringProperty
from bpy.types import AddonPreferences


if "settings" in locals():
    import importlib

    importlib.reload(settings)
    importlib.reload(lattice_ops)
    importlib.reload(deform_ops)
    importlib.reload(ui)
    importlib.reload(updater)
else:
    from . import deform_ops, lattice_ops, settings, ui, updater


_modules = (
    settings,
    lattice_ops,
    deform_ops,
    ui,
    updater,
)


_preview_collections: dict[str, bpy.utils.previews.ImagePreviewCollection] = {}


def _load_previews() -> None:
    if "main" in _preview_collections:
        return

    pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    logo_path = os.path.join(icons_dir, "logo.png")
    if os.path.exists(logo_path):
        pcoll.load("bd_logo", logo_path, 'IMAGE')
    _preview_collections["main"] = pcoll


def _unload_previews() -> None:
    pcoll = _preview_collections.pop("main", None)
    if pcoll is not None:
        bpy.utils.previews.remove(pcoll)


class BD_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    github_repo: StringProperty(
        name="GitHub Repo",
        description="owner/repo for update checks",
        default="mephi100fel/BevelDeformer",
    )
    github_token: StringProperty(
        name="GitHub Token",
        description="Optional for public repos. Required for private repos. Use a fine-grained PAT with Contents: Read access.",
        subtype='PASSWORD',
        default="",
    )

    def draw(self, context):
        layout = self.layout

        pcoll = _preview_collections.get("main")
        if pcoll is not None and "bd_logo" in pcoll:
            layout.template_icon(icon_value=pcoll["bd_logo"].icon_id, scale=8.0)
            layout.label(text="Bevel Deformer")
        else:
            layout.label(text="Bevel Deformer")

        layout.separator()
        layout.label(text="UI settings are in View3D > Sidebar > Bevel")

        layout.separator()
        layout.label(text="Updates")
        layout.prop(self, "github_repo")
        layout.prop(self, "github_token")

        row = layout.row(align=True)
        row.operator("bd.check_updates", text="Check")
        row.operator("bd.install_update", text="Install")


def register() -> None:
    registered = []
    prefs_registered = False
    try:
        _load_previews()
        bpy.utils.register_class(BD_AddonPreferences)
        prefs_registered = True

        for module in _modules:
            module.register()
            registered.append(module)
    except Exception as e:
        message = str(e)
        is_readonly = isinstance(e, RuntimeError) and "readonly state" in message.lower()
        if is_readonly:
            print(
                "BevelDeformer: Blender is running in a readonly state; cannot register UI classes. "
                "Save the file under a new name or open it in a compatible Blender version."
            )

        for module in reversed(registered):
            try:
                module.unregister()
            except Exception:
                pass

        if prefs_registered:
            try:
                bpy.utils.unregister_class(BD_AddonPreferences)
            except Exception:
                pass
        _unload_previews()

        if is_readonly:
            return
        raise


def unregister() -> None:
    for module in reversed(_modules):
        try:
            module.unregister()
        except Exception:
            pass

    try:
        bpy.utils.unregister_class(BD_AddonPreferences)
    except Exception:
        pass
    _unload_previews()
