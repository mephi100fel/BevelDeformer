import bpy
from bpy.types import Panel


def _get_locked_axis_for_ui(obj) -> tuple[bool, int | None]:
    if obj is None:
        return False, None

    lat_obj = None
    if getattr(obj, "type", None) == 'LATTICE':
        lat_obj = obj
    elif getattr(obj, "type", None) == 'MESH':
        for mod in getattr(obj, "modifiers", []):
            try:
                if mod.type == 'LATTICE' and mod.object is not None and mod.object.type == 'LATTICE':
                    lat_obj = mod.object
                    break
            except Exception:
                pass

        if lat_obj is None:
            name = f"Lattice_{obj.name}"
            candidate = bpy.data.objects.get(name)
            if candidate is not None and getattr(candidate, "type", None) == 'LATTICE' and candidate.parent == obj:
                lat_obj = candidate

    if lat_obj is None:
        return False, None

    try:
        enabled = lat_obj.get("bd_locked_axis_enabled")
        idx = lat_obj.get("bd_locked_axis_idx")
        if enabled is not None:
            enabled_bool = bool(enabled)
            idx_int = int(idx) if idx is not None else -1
            if enabled_bool and idx_int in (0, 1, 2):
                return True, idx_int
            return False, None
    except Exception:
        pass

    try:
        lat = lat_obj.data
        points = [int(lat.points_u), int(lat.points_v), int(lat.points_w)]
        candidates = [i for i, p in enumerate(points) if p == 2]
        if len(candidates) == 1 and max(points) > 2:
            return True, candidates[0]
    except Exception:
        pass

    return False, None


class BD_PT_panel(Panel):
    bl_label = "Bevel Deformer"
    bl_idname = "BD_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bevel_Deform'

    def draw(self, context):
        layout = self.layout

        lattice_settings = context.scene.bd_lattice_settings
        deform_settings = context.scene.bd_deform_settings

        col = layout.column(align=True)
        col.label(text="Lattice")
        col.prop(lattice_settings, "locked_axis_enabled")
        col.prop(lattice_settings, "base_resolution")
        if bool(getattr(lattice_settings, "locked_axis_enabled", True)):
            col.prop(lattice_settings, "locked_world_axis")
            col.label(text="Locked axis resolution is fixed to 2")
        col.prop(lattice_settings, "interpolation")
        col.operator("bd.create_lattice_multi")
        col.operator("bd.apply_lattice_interpolation")
        row = col.row(align=True)
        row.operator("bd.apply_lattice")
        row.operator("bd.delete_lattice")

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Deform")
        col.prop(deform_settings, "live_preview")
        col.prop(deform_settings, "reset_to_uniform")
        col.prop(deform_settings, "shift_factor")
        col.prop(deform_settings, "scale_factor")
        col.separator(factor=0.5)
        col.label(text="Dimensions")
        locked_enabled, locked_idx = _get_locked_axis_for_ui(context.view_layer.objects.active)

        row = col.row(align=True)
        row.enabled = not (locked_enabled and locked_idx == 0)
        row.prop(deform_settings, "offset_x")

        row = col.row(align=True)
        row.enabled = not (locked_enabled and locked_idx == 1)
        row.prop(deform_settings, "offset_y")

        row = col.row(align=True)
        row.enabled = not (locked_enabled and locked_idx == 2)
        row.prop(deform_settings, "offset_z")
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
