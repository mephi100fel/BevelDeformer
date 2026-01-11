import bpy
from bpy.types import Operator
from mathutils import Vector


_LIVE_UPDATE_INTERVAL_SEC = 0.15
_live_update_timer_running = False
_live_update_pending = False


def _gather_target_lattices(selected_objects) -> list[bpy.types.Object]:
    lattices: set[bpy.types.Object] = set()
    for obj in list(selected_objects or []):
        try:
            if obj is None:
                continue
            if obj.type == 'LATTICE':
                lattices.add(obj)
                continue
            if obj.type != 'MESH':
                continue

            for mod in getattr(obj, "modifiers", []):
                try:
                    if mod.type == 'LATTICE' and mod.object is not None and mod.object.type == 'LATTICE':
                        lattices.add(mod.object)
                except Exception:
                    pass

            # Fallback to the addon's naming convention
            candidate = bpy.data.objects.get(f"Lattice_{obj.name}")
            if (
                candidate is not None
                and getattr(candidate, "type", None) == 'LATTICE'
                and getattr(candidate, "parent", None) == obj
            ):
                lattices.add(candidate)
        except Exception:
            continue

    return list(lattices)


def _is_timer_registered() -> bool:
    try:
        is_registered = getattr(bpy.app.timers, "is_registered", None)
        if callable(is_registered):
            return bool(is_registered(_live_update_timer))
    except Exception:
        pass
    return False


def _ensure_timer_registered() -> bool:
    try:
        if _is_timer_registered():
            return True
        bpy.app.timers.register(_live_update_timer, first_interval=_LIVE_UPDATE_INTERVAL_SEC)
        return True
    except Exception as e:
        print(f"BevelDeformer: failed to register live update timer: {e}")
        return False


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


def _get_lattice_locked_axis(lat_obj) -> tuple[bool, int | None]:
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

    # Backward-compat inference for lattices created before metadata existed:
    # if exactly one axis has resolution 2 and at least one other axis > 2,
    # assume that axis is locked.
    try:
        lat = lat_obj.data
        points = [int(lat.points_u), int(lat.points_v), int(lat.points_w)]
        candidates = [i for i, p in enumerate(points) if p == 2]
        if len(candidates) == 1 and max(points) > 2:
            return True, candidates[0]
    except Exception:
        pass

    return False, None


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

    try:
        if not _live_update_pending:
            _live_update_timer_running = False
            return None

        _live_update_pending = False
        _apply_live_update()

        if _live_update_pending:
            return _LIVE_UPDATE_INTERVAL_SEC

        _live_update_timer_running = False
        return None

    except Exception as e:
        # If the timer callback errors, Blender silently stops calling it.
        # Reset flags so scheduling can recover on the next property change.
        _live_update_timer_running = False
        _live_update_pending = False
        print(f"BevelDeformer: live update timer crashed: {e}")
        return None


def schedule_live_update(context) -> None:
    global _live_update_timer_running
    global _live_update_pending

    _live_update_pending = True
    if _live_update_timer_running and _is_timer_registered():
        return

    if not _ensure_timer_registered():
        _live_update_timer_running = False
        return

    _live_update_timer_running = True


def reset_selected_lattices_to_uniform() -> int:
    selected_lattices = _gather_target_lattices(bpy.context.selected_objects)
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
    try:
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

    selected_lattices = _gather_target_lattices(bpy.context.selected_objects)
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
            locked_enabled, locked_idx = _get_lattice_locked_axis(obj)
            fx = [_offset_ramp_factor(i, u_res) for i in range(u_res)]
            fy = [_offset_ramp_factor(i, v_res) for i in range(v_res)]
            fz = [_offset_ramp_factor(i, w_res) for i in range(w_res)]

            for w in range(w_res):
                dz = float(offset_z) * float(fz[w])
                for v in range(v_res):
                    dy = float(offset_y) * float(fy[v])
                    for u in range(u_res):
                        dx = float(offset_x) * float(fx[u])

                        if locked_enabled and locked_idx is not None:
                            if locked_idx == 0:
                                dx = 0.0
                            elif locked_idx == 1:
                                dy = 0.0
                            elif locked_idx == 2:
                                dz = 0.0

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
            self.report({'WARNING'}, "No lattices found for selected objects")
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
            self.report({'WARNING'}, "No lattices found for selected objects (sliders reset)")
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
