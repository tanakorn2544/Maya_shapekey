import bpy

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
