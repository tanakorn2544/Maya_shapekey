import bpy

# Setup
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

amt = bpy.data.armatures.new("TestArm")
obj = bpy.data.objects.new("TestRig", amt)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj

bpy.ops.object.mode_set(mode='EDIT')
b = amt.edit_bones.new("Bone")
b.head = (0,0,0)
b.tail = (0,0,1)
bpy.ops.object.mode_set(mode='POSE')

pb = obj.pose.bones["Bone"]

# Test 1: Full Path Action
act_full = bpy.data.actions.new("ActFull")
fc = act_full.fcurves.new(f'pose.bones["Bone"].location', index=0)
fc.keyframe_points.insert(1, 1.0) # Frame 1, Value 1

# Apply Constraint
const = pb.constraints.new('ACTION')
const.target = obj # Self drive for test (or any object)
const.transform_channel = 'LOCATION_X'
const.target_space = 'LOCAL'
const.mix_mode = 'AFTER'
const.action = act_full
const.min = 0
const.max = 2
const.frame_start = 0
const.frame_end = 2

# Force update
bpy.context.view_layer.update()

print(f"Full Path Test: Bone Loc X = {pb.location[0]}")
# Expect: If working, should be ~0.5 (if driver is 0?) No wait.
# Driver is 'obj'. Obj Rotation/Loc is 0?
# Set obj location
obj.location[0] = 1.0 
bpy.context.view_layer.update()
# Driver=1. Frame=1. Value=1.
print(f"Full Path Test (Driver=1): Bone Loc X = {pb.location[0]}")


# Test 2: Local Path Action
const.action = None # Clear

act_local = bpy.data.actions.new("ActLocal")
fc = act_local.fcurves.new('location', index=0) # Local path
fc.keyframe_points.insert(1, 2.0) # Frame 1, Value 2

const.action = act_local
bpy.context.view_layer.update()

print(f"Local Path Test (Driver=1): Bone Loc X = {pb.location[0]}")
