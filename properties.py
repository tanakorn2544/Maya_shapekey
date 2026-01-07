
import bpy


def update_hud(self, context):
    try:
        from . import hud
        hud.toggle_hud_update(self, context)
    except ImportError:
        pass

class DriverToolSettings(bpy.types.PropertyGroup):
    # Driver Side
    driver_target: bpy.props.PointerProperty(
        name="Driver Object",
        type=bpy.types.Object,
        description="Object that drives the shape key"
    )
    driver_bone: bpy.props.StringProperty(
        name="Driver Bone",
        description="Bone name if the driver is an armature"
    )
    driver_data_path: bpy.props.StringProperty(
        name="Data Path",
        description="RNA Path to the driving property"
    )
    
    # Driven Side
    driven_object: bpy.props.PointerProperty(
        name="Driven Object",
        type=bpy.types.Object,
        description="Object containing the shape keys"
    )
    driven_key: bpy.props.StringProperty(
        name="Driven Shape Key",
        description="Name of the shape key to drive"
    )

    driven_type: bpy.props.EnumProperty(
        name="Driven Type",
        items=[
            ('KEY', "Shape Key", "Drive a Shape Key Value"),
            ('POSE', "Pose", "Drive Bone Transforms"),
        ],
        default='KEY'
    )
    
    # Pose Driving Channels
    drive_location: bpy.props.BoolProperty(name="Location", default=False)
    drive_rotation: bpy.props.BoolProperty(name="Rotation", default=True)
    drive_scale: bpy.props.BoolProperty(name="Scale", default=False)
    
    # Pose Action Naming
    pose_action_name: bpy.props.StringProperty(
        name="Action Name",
        description="Custom name for the Action Constraint. Leave empty for auto-naming",
        default=""
    )

    # Values for "Set Key"
    driver_value: bpy.props.FloatProperty(name="Driver Value", default=0.0)
    driven_value: bpy.props.FloatProperty(name="Driven Value", default=0.0)

    # Combo / Corrective Shape Tool
    combo_shape_a: bpy.props.StringProperty(name="Shape A", description="First shape key")
    combo_shape_b: bpy.props.StringProperty(name="Shape B", description="Second shape key")
    combo_name: bpy.props.StringProperty(name="New Shape Name", description="Name of the corrective shape", default="Corrective")
    
    # Creation Tool
    new_shape_name: bpy.props.StringProperty(name="New Shape Name", description="Name for the new shape key")

    # In-Between Tool
    ib_source: bpy.props.StringProperty(name="Parent Shape", description="Shape key to add in-between for")
    ib_value: bpy.props.FloatProperty(name="Trigger Value", default=0.5, min=0.0, max=1.0)

    # Asymmetry Tool
    asym_shape_name: bpy.props.StringProperty(name="Asym Shape Name", description="Name for the asymmetrical shape key")

    driver_interpolation: bpy.props.EnumProperty(
        name="Interpolation",
        items=[
            ('LINEAR', "Linear", "Straight lines (Linear)", 'IPO_LINEAR', 0),
            ('BEZIER', "Smooth", "Smooth falloff (Bezier)", 'IPO_BEZIER', 1),
            ('CONSTANT', "Step", "Instant change (Constant)", 'IPO_CONSTANT', 2),
        ],
        default='LINEAR'
    )

    show_hud: bpy.props.BoolProperty(
        name="Show Info HUD",
        description="Display the addon status on the left of the viewport",
        default=False,
        update=update_hud
    )
    
    hud_font_size: bpy.props.IntProperty(
        name="HUD Font Size",
        default=16,
        min=10,
        max=72,
        description="Font size for the Viewport HUD overlay",
        update=update_hud
    )
    
    hud_line_width: bpy.props.FloatProperty(
        name="HUD Line Width",
        default=3.0,
        min=1.0,
        max=10.0,
        description="Line thickness for the HUD bone highlights",
        update=update_hud
    )
    
    # Visualization Colors
    highlight_color_driver: bpy.props.FloatVectorProperty(
        name="Driver Color",
        subtype='COLOR',
        default=(0.0, 1.0, 1.0), # Cyan
        min=0.0, max=1.0,
        description="Color for the Driver highlight (Bone/Object)"
    )
    

    highlight_color_driven: bpy.props.FloatVectorProperty(
        name="Driven Color",
        subtype='COLOR',
        default=(1.0, 0.5, 0.0), # Orange
        min=0.0, max=1.0,
        description="Color for the Driven Shape highlight"
    )

    use_scale_fix: bpy.props.BoolProperty(
        name="Smart Scale Fix",
        description="Auto-apply normalization formula for Scale drivers (clamp((var-1)/(tgt-1))...) globally",
        default=False
    )

def register():
    # Handle re-registration (reload scripts)
    try:
        bpy.utils.register_class(DriverToolSettings)
    except ValueError:
        bpy.utils.unregister_class(DriverToolSettings)
        bpy.utils.register_class(DriverToolSettings)
        
    bpy.types.Scene.maya_shape_keys = bpy.props.PointerProperty(type=DriverToolSettings)

def unregister():
    if hasattr(bpy.types.Scene, "maya_shape_keys"):
        del bpy.types.Scene.maya_shape_keys
    
    try:
        bpy.utils.unregister_class(DriverToolSettings)
    except RuntimeError:
        pass
