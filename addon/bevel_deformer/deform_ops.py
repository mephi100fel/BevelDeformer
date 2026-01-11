import bpy
from bpy.types import Operator
from mathutils import Vector


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


_classes = (
    BD_OT_deform_selected_lattices,
    BD_OT_reset_selected_lattices,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
