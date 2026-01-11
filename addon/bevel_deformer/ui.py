import bpy
from bpy.types import Panel


class BD_PT_panel(Panel):
    bl_label = "Bevel Deformer"
    bl_idname = "BD_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bevel'

    def draw(self, context):
        layout = self.layout

        lattice_settings = context.scene.bd_lattice_settings
        deform_settings = context.scene.bd_deform_settings

        col = layout.column(align=True)
        col.label(text="Lattice")
        col.prop(lattice_settings, "base_resolution")
        col.prop(lattice_settings, "locked_world_axis")
        col.prop(lattice_settings, "locked_axis_resolution")
        col.prop(lattice_settings, "interpolation")
        col.operator("bd.create_lattice_multi")
        col.operator("bd.apply_lattice_interpolation")
        col.operator("bd.delete_lattice")

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Deform")
        col.prop(deform_settings, "live_preview")
        col.prop(deform_settings, "reset_to_uniform")
        col.prop(deform_settings, "shift_factor")
        col.prop(deform_settings, "scale_factor")
        col.operator("bd.deform_selected_lattices")
        col.operator("bd.reset_selected_lattices")


_classes = (
    BD_PT_panel,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
