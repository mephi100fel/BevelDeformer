import bpy
from bpy.props import EnumProperty, IntProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup
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


def create_lattice_multi(
    targets: list[bpy.types.Object],
    *,
    base_resolution: int,
    locked_axis_resolution: int,
    interpolation: str,
) -> int:
    if not targets:
        return 0

    bpy.context.view_layer.update()

    created_lattices = []
    bpy.ops.object.select_all(action='DESELECT')

    base_res = int(max(2, base_resolution))
    locked_res = int(max(2, locked_axis_resolution))
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

            rot_mat = obj.matrix_world.to_3x3().normalized()
            world_x = Vector((1, 0, 0))

            scores = [
                abs(rot_mat.col[0].dot(world_x)),
                abs(rot_mat.col[1].dot(world_x)),
                abs(rot_mat.col[2].dot(world_x)),
            ]
            locked_idx = scores.index(max(scores))

            d_list = [local_size.x, local_size.y, local_size.z]
            resolutions = [2, 2, 2]

            active_dims = [d_list[i] for i in range(3) if i != locked_idx]
            min_dim = min(active_dims) if active_dims else 1.0

            for i in range(3):
                if i == locked_idx:
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

            bpy.context.collection.objects.link(lat_obj)

            mat_trans = Matrix.Translation(local_center)
            mat_scale = Matrix.Diagonal(local_size.to_4d())
            mat_scale[3][3] = 1.0

            lat_obj.matrix_world = obj.matrix_world @ mat_trans @ mat_scale

            lat_obj.parent = obj
            lat_obj.matrix_parent_inverse = obj.matrix_world.inverted()

            mod = obj.modifiers.new(name="AutoLattice", type='LATTICE')
            mod.object = lat_obj

            created_lattices.append(lat_obj)

        except Exception as e:
            print(f"Failed for {obj.name}: {e}")

    for lat in created_lattices:
        lat.select_set(True)
    if created_lattices:
        bpy.context.view_layer.objects.active = created_lattices[-1]

    return len(created_lattices)


class BD_LatticeSettings(PropertyGroup):
    base_resolution: IntProperty(
        name="Base Resolution",
        description="Resolution used for the smallest active dimension (even numbers will be used)",
        default=6,
        min=2,
        soft_max=64,
    )
    locked_axis_resolution: IntProperty(
        name="Locked Axis Resolution",
        description="Resolution used for the axis most aligned with World X",
        default=2,
        min=2,
        soft_max=64,
    )
    interpolation: EnumProperty(
        name="Interpolation",
        description="Lattice interpolation type",
        items=[
            ("KEY_LINEAR", "Linear", "Linear interpolation"),
            ("KEY_CARDINAL", "Cardinal", "Cardinal interpolation"),
            ("KEY_CATMULL_ROM", "Catmull-Rom", "Catmull-Rom interpolation"),
            ("KEY_BSPLINE", "B-Spline", "B-Spline interpolation"),
        ],
        default="KEY_BSPLINE",
    )


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
            base_resolution=int(settings.base_resolution),
            locked_axis_resolution=int(settings.locked_axis_resolution),
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
                print(f"Failed to delete lattice {getattr(lat_obj, 'name', '<unknown>')}: {e}")

        self.report({'INFO'}, f"Deleted {deleted} lattice(s)")
        return {'FINISHED'}


class BD_PT_lattice_panel(Panel):
    bl_label = "Bevel Deformer (Lattice)"
    bl_idname = "BD_PT_lattice_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bevel'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.bd_lattice_settings

        layout.prop(settings, "base_resolution")
        layout.prop(settings, "locked_axis_resolution")
        layout.prop(settings, "interpolation")
        layout.operator(BD_OT_create_lattice_multi.bl_idname)
        layout.separator()
        layout.operator(BD_OT_delete_lattice.bl_idname)


_classes = (
    BD_LatticeSettings,
    BD_OT_create_lattice_multi,
    BD_OT_delete_lattice,
    BD_PT_lattice_panel,
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
    bpy.types.Scene.bd_lattice_settings = PointerProperty(type=BD_LatticeSettings)


def unregister():
    if getattr(bpy.app, "is_readonly", False):
        return
    if hasattr(bpy.types.Scene, "bd_lattice_settings"):
        del bpy.types.Scene.bd_lattice_settings
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