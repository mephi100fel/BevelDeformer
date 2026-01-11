import bpy
from bpy.types import Operator
from mathutils import Matrix, Vector


def _safe_dim(value: float, eps: float = 1e-4) -> float:
    return value if abs(value) > eps else eps


def _existing_lattice_for_mesh(mesh_obj: bpy.types.Object) -> bpy.types.Object | None:
    expected_name = f"Lattice_{mesh_obj.name}"
    lat_obj = bpy.data.objects.get(expected_name)
    if lat_obj is None:
        return None
    if lat_obj.type != 'LATTICE':
        return None
    if lat_obj.parent != mesh_obj:
        return None
    return lat_obj


def _remove_existing_lattice(mesh_obj: bpy.types.Object) -> bool:
    lat_obj = _existing_lattice_for_mesh(mesh_obj)
    if lat_obj is None:
        return False

    for mod in list(mesh_obj.modifiers):
        if mod.type != 'LATTICE':
            continue
        if mod.object != lat_obj:
            continue
        mesh_obj.modifiers.remove(mod)

    lat_data = lat_obj.data
    bpy.data.objects.remove(lat_obj, do_unlink=True)
    if lat_data is not None and getattr(lat_data, "users", 0) == 0:
        bpy.data.lattices.remove(lat_data)
    return True


def _remove_lattice_references(lat_obj: bpy.types.Object) -> int:
    removed = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for mod in list(obj.modifiers):
            if mod.type != 'LATTICE':
                continue
            if mod.object != lat_obj:
                continue
            obj.modifiers.remove(mod)
            removed += 1
    return removed


def _delete_lattice_object(lat_obj: bpy.types.Object) -> bool:
    if lat_obj is None or lat_obj.type != 'LATTICE':
        return False

    _remove_lattice_references(lat_obj)
    lat_data = lat_obj.data
    bpy.data.objects.remove(lat_obj, do_unlink=True)
    if lat_data is not None and getattr(lat_data, "users", 0) == 0:
        bpy.data.lattices.remove(lat_data)
    return True


def _iter_lattice_modifiers(
    mesh_obj: bpy.types.Object, *, lattice_obj: bpy.types.Object | None = None
):
    for mod in list(mesh_obj.modifiers):
        if mod.type != 'LATTICE':
            continue
        if lattice_obj is not None and mod.object != lattice_obj:
            continue
        yield mod


def _find_meshes_using_lattice(lat_obj: bpy.types.Object) -> list[bpy.types.Object]:
    meshes: list[bpy.types.Object] = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for mod in obj.modifiers:
            if mod.type == 'LATTICE' and mod.object == lat_obj:
                meshes.append(obj)
                break
    return meshes


def create_lattice_multi(
    targets: list[bpy.types.Object],
    *,
    locked_axis_enabled: bool,
    base_resolution: int,
    locked_world_axis: str,
    interpolation: str,
) -> int:
    if not targets:
        return 0

    bpy.context.view_layer.update()

    prev_selected = list(bpy.context.selected_objects)
    prev_active = bpy.context.view_layer.objects.active

    created_lattices = []

    base_res = int(max(2, base_resolution))
    locked_enabled = bool(locked_axis_enabled)
    locked_res = 2
    if base_res % 2 == 1:
        base_res += 1

    for obj in targets:
        try:
            bbox = [Vector(v) for v in obj.bound_box]
            min_v = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
            max_v = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))

            local_center = (min_v + max_v) / 2
            local_size = max_v - min_v
            local_size = Vector((_safe_dim(local_size.x), _safe_dim(local_size.y), _safe_dim(local_size.z)))

            locked_idx: int | None = None
            if locked_enabled:
                rot_mat = obj.matrix_world.to_3x3().normalized()
                axis = str(locked_world_axis).upper()
                world_axis_map = {
                    "X": Vector((1, 0, 0)),
                    "Y": Vector((0, 1, 0)),
                    "Z": Vector((0, 0, 1)),
                }
                world_axis = world_axis_map.get(axis, Vector((1, 0, 0)))

                scores = [
                    abs(rot_mat.col[0].dot(world_axis)),
                    abs(rot_mat.col[1].dot(world_axis)),
                    abs(rot_mat.col[2].dot(world_axis)),
                ]
                locked_idx = int(scores.index(max(scores)))

            d_list = [local_size.x, local_size.y, local_size.z]
            resolutions = [2, 2, 2]

            if locked_enabled and locked_idx is not None:
                active_dims = [d_list[i] for i in range(3) if i != locked_idx]
                min_dim = min(active_dims) if active_dims else 1.0
            else:
                locked_idx = None
                min_dim = min(d_list) if d_list else 1.0

            for i in range(3):
                if locked_idx is not None and i == locked_idx:
                    resolutions[i] = locked_res
                else:
                    dim = d_list[i]
                    if abs(dim - min_dim) < 0.001:
                        resolutions[i] = base_res
                    else:
                        ratio = dim / min_dim if min_dim > 1e-8 else 1.0
                        target = ratio * base_res
                        even_res = round(target / 2) * 2
                        resolutions[i] = int(max(2, even_res))

            lat_name = f"Lattice_{obj.name}"
            lat_data = bpy.data.lattices.new(lat_name + "_Data")
            lat_obj = bpy.data.objects.new(lat_name, lat_data)

            lat_data.points_u = resolutions[0]
            lat_data.points_v = resolutions[1]
            lat_data.points_w = resolutions[2]

            lat_data.interpolation_type_u = interpolation
            lat_data.interpolation_type_v = interpolation
            lat_data.interpolation_type_w = interpolation

            target_collection = None
            if getattr(obj, "users_collection", None):
                if len(obj.users_collection) > 0:
                    target_collection = obj.users_collection[0]
            if target_collection is None:
                target_collection = bpy.context.collection
            target_collection.objects.link(lat_obj)

            mat_trans = Matrix.Translation(local_center)
            mat_scale = Matrix.Diagonal(local_size.to_4d())
            mat_scale[3][3] = 1.0

            lat_obj.matrix_world = obj.matrix_world @ mat_trans @ mat_scale

            lat_obj.parent = obj
            lat_obj.matrix_parent_inverse = obj.matrix_world.inverted()

            # Persist per-lattice lock metadata so later operations can respect it
            # even if scene settings change.
            lat_obj["bd_locked_axis_enabled"] = bool(locked_enabled)
            lat_obj["bd_locked_axis_idx"] = int(locked_idx) if locked_idx is not None else -1
            lat_obj["bd_locked_world_axis"] = str(locked_world_axis)

            mod = obj.modifiers.new(name="AutoLattice", type='LATTICE')
            mod.object = lat_obj

            created_lattices.append(lat_obj)

        except Exception as e:
            print(f"BevelDeformer: failed for {obj.name}: {e}")

    for lat in created_lattices:
        lat.select_set(True)
    if created_lattices:
        bpy.context.view_layer.objects.active = created_lattices[-1]

    if created_lattices:
        for obj in prev_selected:
            try:
                obj.select_set(False)
            except Exception:
                pass
        for lat in created_lattices:
            try:
                lat.select_set(True)
            except Exception:
                pass
        try:
            bpy.context.view_layer.objects.active = created_lattices[-1]
        except Exception:
            pass
    else:
        try:
            bpy.context.view_layer.objects.active = prev_active
        except Exception:
            pass

    return len(created_lattices)


class BD_OT_create_lattice_multi(Operator):
    bl_idname = "bd.create_lattice_multi"
    bl_label = "Create Lattice (Per Mesh)"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        targets = [o for o in context.selected_objects if o.type == 'MESH']
        if not targets:
            return self.execute(context)

        existing = [o for o in targets if _existing_lattice_for_mesh(o) is not None]
        if existing:
            self.report(
                {'WARNING'},
                f"Existing lattices detected for {len(existing)} mesh(es). Confirm to overwrite.",
            )
            return context.window_manager.invoke_confirm(self, event)

        return self.execute(context)

    def execute(self, context):
        settings = context.scene.bd_lattice_settings
        targets = [o for o in context.selected_objects if o.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        overwritten = 0
        for obj in targets:
            if _remove_existing_lattice(obj):
                overwritten += 1

        count = create_lattice_multi(
            targets,
            locked_axis_enabled=bool(getattr(settings, "locked_axis_enabled", True)),
            base_resolution=int(settings.base_resolution),
            locked_world_axis=str(settings.locked_world_axis),
            interpolation=str(settings.interpolation),
        )

        if overwritten > 0:
            self.report({'INFO'}, f"Overwritten {overwritten} existing lattice(s)")

        self.report({'INFO'}, f"Created {count} lattice(s)")
        return {'FINISHED'}


class BD_OT_delete_lattice(Operator):
    bl_idname = "bd.delete_lattice"
    bl_label = "Delete Lattice"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selected = list(context.selected_objects)
        if not selected:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        lattices_to_delete = set()
        for obj in selected:
            if obj.type == 'MESH':
                existing = _existing_lattice_for_mesh(obj)
                if existing is not None:
                    lattices_to_delete.add(existing)
            elif obj.type == 'LATTICE':
                lattices_to_delete.add(obj)

        if not lattices_to_delete:
            self.report({'WARNING'}, "No lattices found for selected objects")
            return {'CANCELLED'}

        deleted = 0
        for lat_obj in list(lattices_to_delete):
            try:
                if _delete_lattice_object(lat_obj):
                    deleted += 1
            except Exception as e:
                print(
                    f"BevelDeformer: failed to delete lattice {getattr(lat_obj, 'name', '<unknown>')}: {e}"
                )

        self.report({'INFO'}, f"Deleted {deleted} lattice(s)")
        return {'FINISHED'}


class BD_OT_apply_lattice_interpolation(Operator):
    bl_idname = "bd.apply_lattice_interpolation"
    bl_label = "Apply Interpolation to Selected"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.bd_lattice_settings
        interpolation = str(settings.interpolation)

        selected = list(context.selected_objects)
        if not selected:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        lattices: set[bpy.types.Object] = set()
        for obj in selected:
            if obj.type == 'LATTICE':
                lattices.add(obj)
            elif obj.type == 'MESH':
                existing = _existing_lattice_for_mesh(obj)
                if existing is not None:
                    lattices.add(existing)

        if not lattices:
            self.report({'WARNING'}, "No lattices found for selected objects")
            return {'CANCELLED'}

        changed = 0
        for lat_obj in lattices:
            try:
                lat_data = lat_obj.data
                lat_data.interpolation_type_u = interpolation
                lat_data.interpolation_type_v = interpolation
                lat_data.interpolation_type_w = interpolation
                changed += 1
            except Exception as e:
                print(f"BevelDeformer: failed to set interpolation for {getattr(lat_obj, 'name', '<unknown>')}: {e}")

        self.report({'INFO'}, f"Applied interpolation to {changed} lattice(s)")
        return {'FINISHED'}


class BD_OT_apply_lattice(Operator):
    bl_idname = "bd.apply_lattice"
    bl_label = "Apply Lattice"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selected = list(context.selected_objects)
        if not selected:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        prev_selected = list(context.selected_objects)
        prev_active = context.view_layer.objects.active

        try:
            if context.mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass

            meshes: set[bpy.types.Object] = set()
            lattices: set[bpy.types.Object] = set()

            for obj in selected:
                if obj.type == 'MESH':
                    meshes.add(obj)
                    for mod in obj.modifiers:
                        if mod.type == 'LATTICE' and mod.object is not None:
                            lattices.add(mod.object)
                elif obj.type == 'LATTICE':
                    lattices.add(obj)

            if lattices and not meshes:
                for lat in list(lattices):
                    for m in _find_meshes_using_lattice(lat):
                        meshes.add(m)

            if not meshes:
                self.report({'WARNING'}, "No mesh objects found to apply")
                return {'CANCELLED'}

            applied_mods = 0
            for mesh_obj in meshes:
                if mesh_obj.type != 'MESH':
                    continue

                try:
                    for obj in context.selected_objects:
                        obj.select_set(False)
                except Exception:
                    pass

                try:
                    mesh_obj.select_set(True)
                    context.view_layer.objects.active = mesh_obj
                except Exception:
                    continue

                for mod in list(_iter_lattice_modifiers(mesh_obj)):
                    lat_obj = mod.object
                    if lat_obj is None:
                        continue

                    if lattices and lat_obj not in lattices:
                        continue

                    try:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                        applied_mods += 1
                    except Exception as e:
                        print(
                            "BevelDeformer: failed to apply modifier "
                            f"{mod.name} on {getattr(mesh_obj, 'name', '<unknown>')}: {e}"
                        )

            deleted_lattices = 0
            skipped_lattices = 0
            for lat_obj in list(lattices):
                try:
                    still_used = False
                    for m in _find_meshes_using_lattice(lat_obj):
                        still_used = True
                        break

                    if still_used:
                        skipped_lattices += 1
                        continue

                    if _delete_lattice_object(lat_obj):
                        deleted_lattices += 1
                except Exception as e:
                    print(
                        "BevelDeformer: failed to delete lattice "
                        f"{getattr(lat_obj, 'name', '<unknown>')}: {e}"
                    )

            self.report(
                {'INFO'},
                f"Applied {applied_mods} modifier(s), deleted {deleted_lattices} lattice(s)"
                + (f", skipped {skipped_lattices} (still used)" if skipped_lattices else ""),
            )
            return {'FINISHED'}

        finally:
            try:
                for obj in context.selected_objects:
                    obj.select_set(False)
            except Exception:
                pass
            for obj in prev_selected:
                try:
                    obj.select_set(True)
                except Exception:
                    pass
            try:
                context.view_layer.objects.active = prev_active
            except Exception:
                pass


_classes = (
    BD_OT_create_lattice_multi,
    BD_OT_delete_lattice,
    BD_OT_apply_lattice_interpolation,
    BD_OT_apply_lattice,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
