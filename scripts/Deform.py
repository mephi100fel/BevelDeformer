import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Vector


def process_lattice_smart_scale(*, scale_factor: float, shift_factor: float, reset_to_uniform: bool) -> int:
    selected_lattices = [o for o in bpy.context.selected_objects if o.type == 'LATTICE']
    if not selected_lattices:
        return 0

    bpy.context.view_layer.update()

    for obj in selected_lattices:
        lat = obj.data
        u_res = lat.points_u
        v_res = lat.points_v
        w_res = lat.points_w

        def get_idx(u, v, w):
            return w * (u_res * v_res) + v * u_res + u

        if reset_to_uniform:
            for w in range(w_res):
                z_pos = -0.5 + (w / (w_res - 1)) if w_res > 1 else 0.0
                for v in range(v_res):
                    y_pos = -0.5 + (v / (v_res - 1)) if v_res > 1 else 0.0
                    for u in range(u_res):
                        x_pos = -0.5 + (u / (u_res - 1)) if u_res > 1 else 0.0
                        idx = get_idx(u, v, w)
                        lat.points[idx].co_deform = Vector((x_pos, y_pos, z_pos))

        shifted_u = False
        shifted_v = False
        shifted_w = False

        if u_res > 4:
            shifted_u = True
            for w in range(w_res):
                for v in range(v_res):
                    idx_0 = get_idx(0, v, w)
                    idx_1 = get_idx(1, v, w)
                    idx_last = get_idx(u_res - 1, v, w)
                    idx_pre = get_idx(u_res - 2, v, w)

                    p1 = lat.points[idx_1].co_deform
                    p0 = lat.points[idx_0].co_deform
                    lat.points[idx_1].co_deform = p1.lerp(p0, shift_factor)

                    p_pre = lat.points[idx_pre].co_deform
                    p_last = lat.points[idx_last].co_deform
                    lat.points[idx_pre].co_deform = p_pre.lerp(p_last, shift_factor)

        if v_res > 4:
            shifted_v = True
            for w in range(w_res):
                for u in range(u_res):
                    idx_0 = get_idx(u, 0, w)
                    idx_1 = get_idx(u, 1, w)
                    idx_last = get_idx(u, v_res - 1, w)
                    idx_pre = get_idx(u, v_res - 2, w)

                    p1 = lat.points[idx_1].co_deform
                    p0 = lat.points[idx_0].co_deform
                    lat.points[idx_1].co_deform = p1.lerp(p0, shift_factor)

                    p_pre = lat.points[idx_pre].co_deform
                    p_last = lat.points[idx_last].co_deform
                    lat.points[idx_pre].co_deform = p_pre.lerp(p_last, shift_factor)

        if w_res > 4:
            shifted_w = True
            for v in range(v_res):
                for u in range(u_res):
                    idx_0 = get_idx(u, v, 0)
                    idx_1 = get_idx(u, v, 1)
                    idx_last = get_idx(u, v, w_res - 1)
                    idx_pre = get_idx(u, v, w_res - 2)

                    p1 = lat.points[idx_1].co_deform
                    p0 = lat.points[idx_0].co_deform
                    lat.points[idx_1].co_deform = p1.lerp(p0, shift_factor)

                    p_pre = lat.points[idx_pre].co_deform
                    p_last = lat.points[idx_last].co_deform
                    lat.points[idx_pre].co_deform = p_pre.lerp(p_last, shift_factor)

        scale_u = scale_factor if shifted_u else 1.0
        scale_v = scale_factor if shifted_v else 1.0
        scale_w = scale_factor if shifted_w else 1.0

        if scale_u != 1.0 or scale_v != 1.0 or scale_w != 1.0:
            for point in lat.points:
                point.co_deform[0] *= scale_u
                point.co_deform[1] *= scale_v
                point.co_deform[2] *= scale_w

    return len(selected_lattices)


def reset_selected_lattices_to_uniform() -> int:
    selected_lattices = [o for o in bpy.context.selected_objects if o.type == 'LATTICE']
    if not selected_lattices:
        return 0

    bpy.context.view_layer.update()

    for obj in selected_lattices:
        lat = obj.data
        u_res = lat.points_u
        v_res = lat.points_v
        w_res = lat.points_w

        def get_idx(u, v, w):
            return w * (u_res * v_res) + v * u_res + u

        for w in range(w_res):
            z_pos = -0.5 + (w / (w_res - 1)) if w_res > 1 else 0.0
            for v in range(v_res):
                y_pos = -0.5 + (v / (v_res - 1)) if v_res > 1 else 0.0
                for u in range(u_res):
                    x_pos = -0.5 + (u / (u_res - 1)) if u_res > 1 else 0.0
                    idx = get_idx(u, v, w)
                    lat.points[idx].co_deform = Vector((x_pos, y_pos, z_pos))

    return len(selected_lattices)


class BD_DeformSettings(PropertyGroup):
    scale_factor: FloatProperty(
        name="Scale Factor",
        description="Multiplier applied only on axes where shift was performed",
        default=0.95,
        min=0.0,
        soft_max=2.0,
    )
    shift_factor: FloatProperty(
        name="Shift Factor",
        description="0.0 = no shift, 1.0 = collapse into boundary row",
        default=0.5,
        min=0.0,
        max=1.0,
    )
    reset_to_uniform: BoolProperty(
        name="Reset To Uniform",
        description="Reset lattice points to a uniform grid before modifications",
        default=True,
    )


class BD_OT_deform_selected_lattices(Operator):
    bl_idname = "bd.deform_selected_lattices"
    bl_label = "Deform Selected Lattices"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.bd_deform_settings
        count = process_lattice_smart_scale(
            scale_factor=float(settings.scale_factor),
            shift_factor=float(settings.shift_factor),
            reset_to_uniform=bool(settings.reset_to_uniform),
        )

        if count == 0:
            self.report({'WARNING'}, "No lattice objects selected")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Processed {count} lattice(s)")
        return {'FINISHED'}


class BD_OT_reset_selected_lattices(Operator):
    bl_idname = "bd.reset_selected_lattices"
    bl_label = "Reset Selected Lattices"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = reset_selected_lattices_to_uniform()
        if count == 0:
            self.report({'WARNING'}, "No lattice objects selected")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Reset {count} lattice(s) to uniform")
        return {'FINISHED'}


class BD_PT_deform_panel(Panel):
    bl_label = "Bevel Deformer (Deform)"
    bl_idname = "BD_PT_deform_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bevel'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bd_deform_settings

        layout.prop(settings, "reset_to_uniform")
        layout.prop(settings, "shift_factor")
        layout.prop(settings, "scale_factor")
        layout.operator(BD_OT_deform_selected_lattices.bl_idname)
        layout.separator()
        layout.operator(BD_OT_reset_selected_lattices.bl_idname)


_classes = (
    BD_DeformSettings,
    BD_OT_deform_selected_lattices,
    BD_OT_reset_selected_lattices,
    BD_PT_deform_panel,
)


def register():
    if getattr(bpy.app, "is_readonly", False):
        print(
            "BevelDeformer: Blender is running in read-only state. "
            "UI registration is disabled. Open the .blend with a Blender version "
            "that is the same or newer than the version that saved it (or disable read-only), "
            "then run this script again."
        )
        return
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bd_deform_settings = PointerProperty(type=BD_DeformSettings)


def unregister():
    if getattr(bpy.app, "is_readonly", False):
        return
    if hasattr(bpy.types.Scene, "bd_deform_settings"):
        del bpy.types.Scene.bd_deform_settings
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    if getattr(bpy.app, "is_readonly", False):
        print(
            "BevelDeformer: Blender is running in read-only state. "
            "UI registration is disabled. Open the .blend with a Blender version "
            "that is the same or newer than the version that saved it (or disable read-only), "
            "then run this script again."
        )
    else:
        try:
            unregister()
        except Exception:
            pass
        register()