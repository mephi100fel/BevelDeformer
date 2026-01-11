import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import PropertyGroup


def _schedule_live_deform_update(self, context) -> None:
    if not getattr(self, "live_preview", False):
        return

    try:
        from . import deform_ops

        deform_ops.schedule_live_update(context)
    except Exception as e:
        print(f"BevelDeformer: live update scheduling failed: {e}")


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
        description="Resolution used for the axis most aligned with the chosen World Axis",
        default=2,
        min=2,
        soft_max=64,
    )
    locked_world_axis: EnumProperty(
        name="World Axis",
        description="Choose which world axis defines the locked lattice direction",
        items=[
            ("X", "X", "Lock to World X"),
            ("Y", "Y", "Lock to World Y"),
            ("Z", "Z", "Lock to World Z"),
        ],
        default="X",
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


class BD_DeformSettings(PropertyGroup):
    live_preview: BoolProperty(
        name="Live Preview",
        description="Automatically apply deform when changing sliders",
        default=True,
    )
    scale_factor: FloatProperty(
        name="Scale Factor",
        description="Multiplier applied only on axes where shift was performed",
        default=1.0,
        min=0.0,
        soft_max=2.0,
        update=_schedule_live_deform_update,
    )
    offset_x: FloatProperty(
        name="Offset X",
        description="Additive offset along lattice X with a ramp (first 2 rows fixed, last 2 full)",
        default=0.0,
        soft_min=-5.0,
        soft_max=5.0,
        update=_schedule_live_deform_update,
    )
    offset_y: FloatProperty(
        name="Offset Y",
        description="Additive offset along lattice Y with a ramp (first 2 rows fixed, last 2 full)",
        default=0.0,
        soft_min=-5.0,
        soft_max=5.0,
        update=_schedule_live_deform_update,
    )
    offset_z: FloatProperty(
        name="Offset Z",
        description="Additive offset along lattice Z with a ramp (first 2 rows fixed, last 2 full)",
        default=0.0,
        soft_min=-5.0,
        soft_max=5.0,
        update=_schedule_live_deform_update,
    )
    shift_factor: FloatProperty(
        name="Shift Factor",
        description="-1.0..1.0 shift strength (0.0 = no shift, 1.0 = collapse into boundary row)",
        default=0.0,
        min=-1.0,
        max=1.0,
        update=_schedule_live_deform_update,
    )
    reset_to_uniform: BoolProperty(
        name="Reset To Uniform",
        description="Reset lattice points to a uniform grid before modifications",
        default=True,
    )


_classes = (
    BD_LatticeSettings,
    BD_DeformSettings,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.bd_lattice_settings = PointerProperty(type=BD_LatticeSettings)
    bpy.types.Scene.bd_deform_settings = PointerProperty(type=BD_DeformSettings)


def unregister() -> None:
    if hasattr(bpy.types.Scene, "bd_lattice_settings"):
        del bpy.types.Scene.bd_lattice_settings
    if hasattr(bpy.types.Scene, "bd_deform_settings"):
        del bpy.types.Scene.bd_deform_settings

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
