import bpy
from maya_shape_keys import operators

# Cleaning
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create Armature
amt = bpy.data.armatures.new("TestArm")
obj = bpy.data.objects.new("TestRig", amt)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj

bpy.ops.object.mode_set(mode='EDIT')
driver_b = amt.edit_bones.new("Driver")
driver_b.head = (0,0,0)
driver_b.tail = (1,0,0)

driven_b = amt.edit_bones.new("Driven")
driven_b.head = (0,2,0)
driven_b.tail = (0,3,0)
bpy.ops.object.mode_set(mode='POSE')

# Set Props
props = bpy.context.scene.maya_shape_keys
props.driver_target = obj
props.driver_bone = "Driver"
props.driver_data_path = "location[0]"
props.driven_object = obj
props.driven_type = 'POSE'
props.drive_location = True

# Select Driven Bone
bpy.ops.pose.select_all(action='DESELECT')
obj.pose.bones["Driven"].bone.select = True
obj.data.bones.active = obj.pose.bones["Driven"].bone

# Call Operator (Mocking or calling direct method?)
# We can call the method directly to test logic if we instantiate the operator class, 
# but easier to run the operator if registered.
# assuming add-on is registered. If not, we instantiate class.

op = operators.BSETUP_OT_AddDriverKey()

# Mock context
class MockContext:
    def __init__(self):
        self.scene = bpy.context.scene
        self.active_object = obj
        self.selected_pose_bones = [obj.pose.bones["Driven"]]
        self.view_layer = bpy.context.view_layer
        self.object = obj
        
ctx = MockContext()

# We need to simulate the "Values Map" and "Driver Val"
# The operator usually gathers these.
# Let's call _setup_action_driver directly.

driven_pb = obj.pose.bones["Driven"]
driver_pb = obj.pose.bones["Driver"]

values = {
    ("location", 0): 5.0, # Target value
    ("location", 1): 0.0,
    ("location", 2): 0.0
}

# Run setup
# _setup_action_driver(self, driven_obj, driven_pb, driver_obj, props, driver_id, driver_val, values_map)
op._setup_action_driver(obj, driven_pb, obj, props, "TestDriverID", 1.0, values)

# VERIFY
const = driven_pb.constraints.get("SDK_TestDriverID")
if not const:
    print("FAIL: Constraint not created")
else:
    print(f"Constraint: {const.name}")
    print(f"  Frame Start: {const.frame_start} (Exp: 0)")
    print(f"  Frame End: {const.frame_end} (Exp: 3)")
    print(f"  Eval Time: {const.eval_time} (Exp: 3.0)")
    
    # Check Drivers
    d_eval = const.driver_add("eval_time").driver # Should NOT exist or be empty/default? 
    # Actually we removed it. If we access it, it might create a new one?
    # driven_pb.constraints["Name"].driver_add creates it.
    # Check if animation data exists for it.
    
    # Check Influence Driver
    fcurve_inf = None
    if driven_pb.animation_data and driven_pb.animation_data.drivers:
        for fc in driven_pb.animation_data.drivers:
            if "influence" in fc.data_path and const.name in fc.data_path:
                fcurve_inf = fc
                break
    
    if fcurve_inf:
        print("PASS: Influence Driver Found")
        
        if is_scale:
             print(f"  Extrapolation: {fcurve_inf.extrapolation} (Exp: CONSTANT)")
        else:
             print(f"  Extrapolation: {fcurve_inf.extrapolation} (Exp: LINEAR)")
             
        # Check Keys
        print(f"  Keyframes: {len(fcurve_inf.keyframe_points)} (Exp: {exp_keys})")
        
        kps = fcurve_inf.keyframe_points
        if len(kps) >= 2:
             print(f"  KP 0: {kps[0].co[:]} (Exp: Rest -> 0.0)")
             print(f"  KP 1: {kps[1].co[:]} (Exp: Target -> 1.0)")
        if len(kps) >= 3 and is_scale:
             print(f"  KP 2: {kps[2].co[:]} (Exp: Falloff -> 0.0)")
        if not is_scale and len(kps) > 2:
             print("  [WARNING] Loc/Rot has >2 keys? Should be Clamped.")
    else:
        print("FAIL: Influence Driver NOT found")

# Test 2: Scale
print("\n--- Test 2: Scale Driver ---")
# Reset
# props.driver_data_path = "scale[0]" # We need to re-run setup
# We can just call setup again with different path
values_scale = { ("scale", 0): 2.0, ("scale", 1): 1.0, ("scale", 2): 1.0 }
props.driver_data_path = "scale[0]"
op._setup_action_driver(obj, driven_pb, obj, props, "TestScaleID", 2.0, values_scale)

# Verify Scale
const_scale = driven_pb.constraints.get("SDK_TestScaleID")
if const_scale:
    fcurve_inf = None
    for fc in driven_pb.animation_data.drivers:
        if "influence" in fc.data_path and const_scale.name in fc.data_path:
            fcurve_inf = fc
            break
            
    if fcurve_inf:
        print(f"Scale Driver Keyframes: {len(fcurve_inf.keyframe_points)} (Exp: 3)")
    else:
        print("FAIL: Scale Driver missing")

    # Check Action
    action = const.action
    if action:
        print(f"Action: {action.name}")
        # Check frames
        frames = set()
        for fc in action.fcurves:
             for kp in fc.keyframe_points:
                 frames.add(kp.co[0])
        print(f"  Keyframes at: {sorted(list(frames))} (Exp: [0.0, 3.0])")
    else:
        print("FAIL: Action not assigned")
