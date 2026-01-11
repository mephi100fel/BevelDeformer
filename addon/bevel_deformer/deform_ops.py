import bpy
from bpy.types import Operator
from mathutils import Vector


_LIVE_UPDATE_INTERVAL_SEC = 0.15
_live_update_timer_running = False
_live_update_pending = False


def _shift_and_relax_line(coords: list[Vector], shift_factor: float) -> None:
    count = len(coords)
    if count < 4:
        return

    sf = float(shift_factor)
    if abs(sf) < 1e-8:
        return

    if sf >= 0.0:
        coords[1] = coords[1].lerp(coords[0], sf)
        coords[count - 2] = coords[count - 2].lerp(coords[count - 1], sf)
    else:
        t = abs(sf)
        if count > 2:
            coords[1] = coords[1].lerp(coords[2], t)
        if count - 3 >= 0:
            coords[count - 2] = coords[count - 2].lerp(coords[count - 3], t)

    if count <= 4:
        return

    start_anchor = coords[1].copy()
    end_anchor = coords[count - 2].copy()
    total_steps = (count - 2) - 1
    if total_steps <= 0:
        return

    for k in range(2, count - 2):
        t = (k - 1) / total_steps
        coords[k] = start_anchor.lerp(end_anchor, t)


def _offset_ramp_factor(index: int, resolution: int) -> float:
    if resolution < 4:
        return 0.0
    if index <= 1:
        return 0.0
    if index >= resolution - 2:
        return 1.0
    return (index - 1) / (resolution - 3)


def _apply_live_update() -> bool:
    try:
        scene = bpy.context.scene
        settings = scene.bd_deform_settings
    except Exception:
        return False

    try:
        process_lattice_smart_scale(
            scale_factor=float(settings.scale_factor),
            shift_factor=float(settings.shift_factor),
            offset_x=float(getattr(settings, "offset_x", 0.0)),
            offset_y=float(getattr(settings, "offset_y", 0.0)),
            offset_z=float(getattr(settings, "offset_z", 0.0)),
            reset_to_uniform=bool(settings.reset_to_uniform),
        )
    except Exception as e:
        print(f"BevelDeformer: live update failed: {e}")
        return False

    return True


def _live_update_timer() -> float | None:
    global _live_update_timer_running
    global _live_update_pending

    if not _live_update_pending:
        _live_update_timer_running = False
        return None

    _live_update_pending = False
    _apply_live_update()

    if _live_update_pending:
        return _LIVE_UPDATE_INTERVAL_SEC

    _live_update_timer_running = False
    return None


def schedule_live_update(context) -> None:
    global _live_update_timer_running
    global _live_update_pending

    _live_update_pending = True
    if _live_update_timer_running:
        return

    _live_update_timer_running = True
    bpy.app.timers.register(_live_update_timer, first_interval=_LIVE_UPDATE_INTERVAL_SEC)


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


def process_lattice_smart_scale(
    *,
    scale_factor: float,
    shift_factor: float,
    offset_x: float,
    offset_y: float,
    offset_z: float,
    reset_to_uniform: bool,
) -> int:
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

        do_shift = abs(float(shift_factor)) > 1e-8

        if do_shift and u_res >= 4:
            shifted_u = True
            for w in range(w_res):
                for v in range(v_res):
                    coords = [lat.points[get_idx(u, v, w)].co_deform.copy() for u in range(u_res)]
                    _shift_and_relax_line(coords, float(shift_factor))
                    for u in range(u_res):
                        lat.points[get_idx(u, v, w)].co_deform = coords[u]

        if do_shift and v_res >= 4:
            shifted_v = True
            for w in range(w_res):
                for u in range(u_res):
                    coords = [lat.points[get_idx(u, v, w)].co_deform.copy() for v in range(v_res)]
                    _shift_and_relax_line(coords, float(shift_factor))
                    for v in range(v_res):
                        lat.points[get_idx(u, v, w)].co_deform = coords[v]

        if do_shift and w_res >= 4:
            shifted_w = True
            for v in range(v_res):
                for u in range(u_res):
                    coords = [lat.points[get_idx(u, v, w)].co_deform.copy() for w in range(w_res)]
                    _shift_and_relax_line(coords, float(shift_factor))
                    for w in range(w_res):
                        lat.points[get_idx(u, v, w)].co_deform = coords[w]

        do_offset = (
            abs(float(offset_x)) > 1e-8
            or abs(float(offset_y)) > 1e-8
            or abs(float(offset_z)) > 1e-8
        )
        if do_offset:
            fx = [_offset_ramp_factor(i, u_res) for i in range(u_res)]
            fy = [_offset_ramp_factor(i, v_res) for i in range(v_res)]
            fz = [_offset_ramp_factor(i, w_res) for i in range(w_res)]

            for w in range(w_res):
                dz = float(offset_z) * float(fz[w])
                for v in range(v_res):
                    dy = float(offset_y) * float(fy[v])
                    for u in range(u_res):
                        dx = float(offset_x) * float(fx[u])
                        idx = get_idx(u, v, w)
                        p = lat.points[idx].co_deform
                        lat.points[idx].co_deform = Vector((p[0] + dx, p[1] + dy, p[2] + dz))

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
            offset_x=float(getattr(settings, "offset_x", 0.0)),
            offset_y=float(getattr(settings, "offset_y", 0.0)),
            offset_z=float(getattr(settings, "offset_z", 0.0)),
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

        try:
            settings = context.scene.bd_deform_settings
            settings.scale_factor = 1.0
            settings.shift_factor = 0.0
            if hasattr(settings, "offset_x"):
                settings.offset_x = 0.0
            if hasattr(settings, "offset_y"):
                settings.offset_y = 0.0
            if hasattr(settings, "offset_z"):
                settings.offset_z = 0.0
        except Exception as e:
            print(f"BevelDeformer: failed to reset UI sliders: {e}")

        if count == 0:
            self.report({'WARNING'}, "No lattice objects selected (sliders reset)")
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
