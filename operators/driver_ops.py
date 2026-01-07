import bpy
from .utils import flip_name, mirror_shape_driver_logic

class BSETUP_OT_LoadDriver(bpy.types.Operator):
    """Load the selected object/bone as the driver"""
    bl_idname = "bsetup.load_driver"
    bl_label = "Load Driver"

    def execute(self, context):
        props = context.scene.maya_shape_keys
        obj = context.active_object
        
        if not obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}
            
        props.driver_target = obj
        
        if obj.type == 'ARMATURE':
            # Try to get active bone
            if context.active_bone:
                props.driver_bone = context.active_bone.name
            elif obj.data.bones.active:
                props.driver_bone = obj.data.bones.active.name
        
        # Reset path as it might not be valid for new object
        # props.driver_data_path = "" # Keep previous path or clear? Clearing is safer.
        
        return {'FINISHED'}

class BSETUP_OT_UpdateDriverValue(bpy.types.Operator):
    """Fetch the current value from the driver target"""
    bl_idname = "bsetup.update_driver_val"
    bl_label = "Get Val"
    bl_icon = 'FILE_REFRESH'

    def execute(self, context):
        props = context.scene.maya_shape_keys
        obj = props.driver_target
        
        if not obj: return {'CANCELLED'}
        
        try:
            val = 0.0
            if obj.type == 'ARMATURE' and props.driver_bone:
                 # Resolve path on the Pose Bone
                 pb = obj.pose.bones.get(props.driver_bone)
                 if pb:
                     try:
                         val = pb.path_resolve(props.driver_data_path)
                     except:
                         # Fallback to Object if path invalid on bone
                         val = obj.path_resolve(props.driver_data_path)
                 else:
                     val = obj.path_resolve(props.driver_data_path)
            else:
                 val = obj.path_resolve(props.driver_data_path)
            
            if isinstance(val, (int, float)):
                props.driver_value = float(val)
            else:
                self.report({'WARNING'}, "Property is not a number")
                
        except:
             self.report({'WARNING'}, "Invalid Data Path")
             
        return {'FINISHED'}

class BSETUP_OT_SnapDriverToValue(bpy.types.Operator):
    """Snap the driver object to the current 'Driver Value'"""
    bl_idname = "bsetup.snap_driver_val"
    bl_label = "Snap Driver"
    bl_icon = 'IMPORT'
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        val = props.driver_value
        obj = props.driver_target
        
        if not obj: return {'CANCELLED'}
        
        target = obj
        if obj.type == 'ARMATURE' and props.driver_bone:
             pb = obj.pose.bones.get(props.driver_bone)
             if pb: target = pb
        
        path = props.driver_data_path
        
        try:
            if "[" in path and path.endswith("]"):
                # Handle Array/Vector access: location[0], rotation_euler[1]
                # Split at last '[' to handle nested arrays if ever needed (though rare here)
                base, idx_s = path.rsplit("[", 1)
                idx = int(idx_s.replace("]", ""))
                
                # Resolve base property (e.g. 'location' -> Vector object)
                # path_resolve works relative to target
                vec = target.path_resolve(base)
                vec[idx] = val
            else:
                # Handle Attributes or Custom Props
                try:
                    # Check if standard attribute
                    # But path_resolve is safer for nested attributes e.g. 'sub.attr'
                    # Setting via setattr(target, path, val) only works for direct attributes
                    # For a generic 'Snap back', we assume simple paths mostly.
                    # But let's try the key access for Custom Props first as fallback
                    if hasattr(target, path):
                         setattr(target, path, val)
                    else:
                         target[path] = val
                         
                    # For more complex nested paths (game_settings.sub_prop) not fully handled 
                    # efficiently here without resolving parent, but this covers user request 
                    # for transforms/custom props.
                except:
                     # Fallback for things that look like attributes but behave like props
                     target[path] = val
                     
            # Force update
            obj.update_tag()
            self.report({'INFO'}, f"Snapped {path} to {val:.3f}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to snap: {e}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class BSETUP_OT_LoadDriven(bpy.types.Operator):
    """Load the selected object shape key as the driven"""
    bl_idname = "bsetup.load_driven"
    bl_label = "Load Driven"
    
    key_name: bpy.props.StringProperty()

    def execute(self, context):
        props = context.scene.maya_shape_keys
        obj = context.active_object

        if not obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        props.driven_object = obj
        
        # Use provided key name or fallback to active
        target_key_name = self.key_name if self.key_name else (obj.active_shape_key.name if obj.active_shape_key else "")
        
        if target_key_name:
            props.driven_key = target_key_name
            # Fetch value
            if obj.data.shape_keys and target_key_name in obj.data.shape_keys.key_blocks:
                 props.driven_value = obj.data.shape_keys.key_blocks[target_key_name].value
            
        return {'FINISHED'}

class BSETUP_OT_AddDriverKey(bpy.types.Operator):
    """Set a keyframe for the driver relationship"""
    bl_idname = "bsetup.add_driver_key"
    bl_label = "Key"
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        
        driver_obj = props.driver_target
        driven_obj = props.driven_object
        
        if not driver_obj or not driven_obj:
            self.report({'ERROR'}, "Driver or Driven object missing")
            return {'CANCELLED'}
        
        if driver_obj.type == 'ARMATURE' and props.driver_bone:
             if props.driver_bone not in driver_obj.pose.bones:
                 self.report({'ERROR'}, f"Bone '{props.driver_bone}' not found")
                 return {'CANCELLED'}

        # --- PREPARE DRIVER INFO ---
        raw_path = props.driver_data_path
        if not raw_path:
             self.report({'ERROR'}, "Driver Data Path is empty")
             return {'CANCELLED'}

        # Smart Transform Detection (for the INPUT/DRIVER side)
        target_transform_type = None 
        target_component = 0
        is_transform = False
        
        if raw_path.startswith("location"):
            is_transform = True
            if "[0]" in raw_path: target_transform_type = 'LOC_X'; target_component = 0
            elif "[1]" in raw_path: target_transform_type = 'LOC_Y'; target_component = 1
            elif "[2]" in raw_path: target_transform_type = 'LOC_Z'; target_component = 2
            
        elif raw_path.startswith("rotation"): # rotation_euler / rotation_quaternion checking
            is_transform = True
            if "[0]" in raw_path: target_transform_type = 'ROT_X'; target_component = 0
            elif "[1]" in raw_path: target_transform_type = 'ROT_Y'; target_component = 1
            elif "[2]" in raw_path: target_transform_type = 'ROT_Z'; target_component = 2
            
        elif raw_path.startswith("scale"):
            is_transform = True
            if "[0]" in raw_path: target_transform_type = 'SCALE_X'; target_component = 0
            elif "[1]" in raw_path: target_transform_type = 'SCALE_Y'; target_component = 1
            elif "[2]" in raw_path: target_transform_type = 'SCALE_Z'; target_component = 2

        # 1. FETCH DRIVER VALUE
        current_driver_val = 0.0
        
        if is_transform and target_transform_type:
            matrix = None
            rot_mode = 'XYZ' 
            
            if driver_obj.type == 'ARMATURE' and props.driver_bone:
                pb = driver_obj.pose.bones.get(props.driver_bone)
                if pb:
                    matrix = pb.matrix_basis 
                    rot_mode = pb.rotation_mode
            else:
                matrix = driver_obj.matrix_basis
                rot_mode = driver_obj.rotation_mode
            
            if matrix:
                if "LOC" in target_transform_type:
                    current_driver_val = matrix.to_translation()[target_component]
                elif "ROT" in target_transform_type:
                    safe_mode = rot_mode if rot_mode in {'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX'} else 'XYZ'
                    euls = matrix.to_euler(safe_mode)
                    current_driver_val = euls[target_component]
                elif "SCALE" in target_transform_type:
                    current_driver_val = matrix.to_scale()[target_component]
        else:
            # Fallback
            try:
                if driver_obj.type == 'ARMATURE' and props.driver_bone:
                    pb = driver_obj.pose.bones.get(props.driver_bone)
                    if pb:
                        try:
                            current_driver_val = pb.path_resolve(raw_path)
                        except:
                            current_driver_val = driver_obj.path_resolve(raw_path) # Fallback to Obj if bone fails
                    else:
                        current_driver_val = driver_obj.path_resolve(raw_path)
                else:
                    current_driver_val = driver_obj.path_resolve(raw_path)
            except:
                 self.report({'ERROR'}, f"Could not resolve path: {raw_path}")
                 return {'CANCELLED'}
        
        props.driver_value = float(current_driver_val)

        # --- BRANCH BASED ON DRIVEN TYPE ---

        if props.driven_type == 'KEY':
            # --- SHAPE KEY LOGIC (Unchanged) ---
            if not props.driven_key:
                 self.report({'ERROR'}, "No Driven Shape Key selected")
                 return {'CANCELLED'}
                 
            key_block = driven_obj.data.shape_keys.key_blocks.get(props.driven_key)
            if not key_block:
                 self.report({'ERROR'}, "Shape Key not found")
                 return {'CANCELLED'}
                 
            current_driven_val = key_block.value
            props.driven_value = float(current_driven_val)
            
            # Setup Driver
            key_data = driven_obj.data.shape_keys
            data_path = f'key_blocks["{props.driven_key}"].value'
            
            self._setup_single_driver(driver_obj, key_data, data_path, current_driver_val, current_driven_val, props, is_transform, target_transform_type, raw_path)
            
            self.report({'INFO'}, f"Keyed {props.driven_key} at {current_driven_val:.2f} (Driver: {current_driver_val:.2f})")

        elif props.driven_type == 'POSE':
            # --- POSE LOGIC (ACTION CONSTRAINT) ---
            if driven_obj.type != 'ARMATURE':
                 self.report({'ERROR'}, "Driven Object must be an Armature for Pose mode")
                 return {'CANCELLED'}
                 
            selected_bones = context.selected_pose_bones
            if not selected_bones:
                 self.report({'ERROR'}, "No bones selected to drive")
                 return {'CANCELLED'}

            # Collect active driven channels
            drive_loc = props.drive_location
            drive_rot = props.drive_rotation
            drive_scale = props.drive_scale
            
            if not (drive_loc or drive_rot or drive_scale):
                 self.report({'WARNING'}, "No channels selected (Loc/Rot/Scale)")
                 return {'CANCELLED'}

            count = 0
            
            # Prepare Driver ID
            driver_id = self.get_driver_id_string(driver_obj, props)
            
            for pb in selected_bones:
                # Capture current values to key into the Action
                values = {} # data_path -> value
                
                # Loc
                if drive_loc:
                    path = "location" # CORRECT: Relative path for Action Constraint on Bone
                    values[path, 0] = pb.location[0]
                    values[path, 1] = pb.location[1]
                    values[path, 2] = pb.location[2]
                
                # Scale
                if drive_scale:
                    path = "scale" # CORRECT: Relative path
                    values[path, 0] = pb.scale[0]
                    values[path, 1] = pb.scale[1]
                    values[path, 2] = pb.scale[2]
                    
                # Rot
                if drive_rot:
                    # Support Euler primarily for now
                    if pb.rotation_mode == 'QUATERNION':
                         path = "rotation_quaternion"
                         for i in range(4): values[path, i] = pb.rotation_quaternion[i]
                    elif pb.rotation_mode == 'AXIS_ANGLE':
                         path = "rotation_axis_angle"
                         for i in range(4): values[path, i] = pb.rotation_axis_angle[i]
                    else: # Euler
                        path = "rotation_euler"
                        for i in range(3): values[path, i] = pb.rotation_euler[i]

                # Setup Action Constraint
                self._setup_action_driver(driven_obj, pb, driver_obj, props, driver_id, current_driver_val, values)
                
                # RESET BONE BASE TRANSFORMS
                # This transfers the "Pose" from the Base Transform into the Action
                if drive_loc: pb.location = (0,0,0)
                if drive_scale: pb.scale = (1,1,1)
                if drive_rot:
                    if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = (1,0,0,0)
                    elif pb.rotation_mode == 'AXIS_ANGLE': pb.rotation_axis_angle = (0,0,1,0)
                    else: pb.rotation_euler = (0,0,0)
                
                count += 1
            
            self.report({'INFO'}, f"Keyed {count} Pose Bones (Action Stack Manual)")
            
            # Force update
            driven_obj.update_tag()
            if driver_obj: driver_obj.update_tag()
            context.view_layer.update()

        return {'FINISHED'}

    def get_driver_id_string(self, driver_obj, props):
        """Generate a unique ID for the driver source"""
        # Sanitization Helper
        def clean(s):
            return "".join([c if c.isalnum() else "_" for c in s])
            
        d_name = clean(driver_obj.name)
        d_sub = clean(props.driver_bone) if (driver_obj.type == 'ARMATURE' and props.driver_bone) else ""
        d_path = clean(props.driver_data_path)
        
        import re
        full = f"{d_name}_{d_sub}_{d_path}"
        return re.sub(r'_+', '_', full).strip('_')

    def _setup_action_driver(self, driven_obj, driven_pb, driver_obj, props, driver_id, driver_val, values_map):
        """Create Action, Constraint, and Keys"""
        
        # 1. Naming - Use custom name if provided, otherwise auto-generate
        custom_name = props.pose_action_name.strip() if hasattr(props, "pose_action_name") else ""
        
        if custom_name:
            constraint_name = f"SDK_{custom_name}"
            action_name = f"SDK_ACT_{custom_name}"
        else:
            constraint_name = f"SDK_{driver_id}"
            action_name = f"SDK_ACT_{driven_pb.name}_{driver_id}"
        
        print(f"[DEBUG] Starting Action Setup. Action Name: {action_name}")
        
        # 2. CREATE ACTION BY RECORDING (Robust Method)
        # Instead of manually creating fcurves which might have wrong paths,
        # we will keyframe the bone directly and let Blender create the action.
        
        # Ensure we are in Pose Mode
        if bpy.context.object.mode != 'POSE':
             bpy.ops.object.mode_set(mode='POSE')
             
        # Save current time and action
        old_frame = bpy.context.scene.frame_current
        old_action = driven_obj.animation_data.action if driven_obj.animation_data else None
        
        # Clear current action on object to start fresh
        if driven_obj.animation_data:
            driven_obj.animation_data.action = None
            
        # Create a new temporary action by keying
        # We need to set the value and insert key
        
        try:
            # 2a. Keyframe REST Pose (Frame 0)
            bpy.context.scene.frame_set(0)
            
            # Apply identity values
            for (path, idx), val in values_map.items():
                # Determine Identity Value
                identity_val = 0.0
                if "scale" in path: identity_val = 1.0
                if "quaternion" in path and idx == 0: identity_val = 1.0
                
                # Set value on bone
                # path is like "location", "scale", etc.
                # structure: driven_pb.location[0] = ...
                if hasattr(driven_pb, path):
                    prop = getattr(driven_pb, path)
                    try:
                        prop[idx] = identity_val
                    except:
                        # Maybe it's not a vector/array?
                         setattr(driven_pb, path, identity_val)
                
                # Insert Keyframe
                driven_pb.keyframe_insert(data_path=path, index=idx)

            # 2b. Keyframe POSE Pose (Frame = 3.0 for Influence Driving)
            # We used to use driver_val as frame, but now we standardize on Frame 3.
            # Influence 0 = Frame 0 (Rest), Influence 1 = Frame 3 (Pose)
            # This allows Evaluation Time to be fixed at 3.0 and we drive Influence 0..1
            frame_target = 3.0
            bpy.context.scene.frame_set(int(frame_target)) 
            
            # Set target values
            for (path, idx), val in values_map.items():
                 if hasattr(driven_pb, path):
                    prop = getattr(driven_pb, path)
                    try:
                        prop[idx] = val
                    except:
                         setattr(driven_pb, path, val)
                 driven_pb.keyframe_insert(data_path=path, index=idx)

            # 2c. Retrieve the created Action
            if driven_obj.animation_data and driven_obj.animation_data.action:
                action = driven_obj.animation_data.action
                action.name = action_name
                action.use_fake_user = True
                
                # Unlink from object (so it doesn't play on the rig anymore)
                driven_obj.animation_data.action = old_action
            else:
                print("[ERROR] No action created by keyframing!")
                return
                
            # Set interpolation
            for fc in action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = props.driver_interpolation
                    
            print(f"[DEBUG] Recorded Action: {action.name}, FCurves: {len(action.fcurves)}")
            
        except Exception as e:
            print(f"[ERROR] Recording Action Failed: {e}")
            import traceback
            traceback.print_exc()
            # Restore
            bpy.context.scene.frame_set(old_frame)
            if driven_obj.animation_data: driven_obj.animation_data.action = old_action
            return

        # Restore frame
        bpy.context.scene.frame_set(old_frame)
        
        # 3. Constraint - Get or Create
        
        # 3. Constraint - Get or Create
        const = driven_pb.constraints.get(constraint_name)
        if const and const.type != 'ACTION':
            driven_pb.constraints.remove(const)
            const = None

        is_new_constraint = const is None
        
        if is_new_constraint:
             # USE OPERATOR TO CREATE CONSTRAINT (Safety fix)
             # This ensures Blender initializes it correctly
            try:
                # Ensure context is correct
                bpy.context.view_layer.objects.active = driven_obj
                if bpy.context.object.mode != 'POSE':
                    bpy.ops.object.mode_set(mode='POSE')
                
                # Select bone
                bpy.ops.pose.select_all(action='DESELECT')
                driven_pb.bone.select = True
                driven_obj.data.bones.active = driven_pb.bone
                
                # Add constraint
                bpy.ops.pose.constraint_add(type='ACTION')
                const = driven_pb.constraints[-1]
                const.name = constraint_name
                print(f"[DEBUG] Constraint created via Operator: {const.name}")
            except Exception as e:
                print(f"[ERROR] Operator constraint creation failed: {e}")
                # Fallback
                const = driven_pb.constraints.new('ACTION')
                const.name = constraint_name
            
        # 4. Configure constraint (always update these)
        const.target = driver_obj
        if driver_obj.type == 'ARMATURE' and props.driver_bone:
            const.subtarget = props.driver_bone
            
        # Configure Mapping - Unused for Influence Drive but good for safety
        const.min = -1000.0
        const.max = 1000.0
        
        # FIXED FRAME RANGE for Influence Driving
        const.frame_start = 0
        const.frame_end = 3
        
        # Channel Map - Still needed? 
        # Actually, for Influence Driving, the constraint doesn't need to map Target Channel to Action Time.
        # It just needs to map Target Channel to Influence (via Driver).
        # Wait, the "Action Constraint" itself usually maps Target Channel -> Action Time.
        # But we are hijacking it. We want Action Time = 3 (Fixed) and Influence = Driver.
        # So the "Target Channel" on the constraint is partially irrelevant IF we ignore it,
        # BUT the constraint needs a valid channel to not error out.
        # AND we are driving Influence manually.
        
        # However, to be clean, let's keep the channel setup but it won't drive time.
        
        path = props.driver_data_path
        channel = 'LOCATION_X' 
        if "location" in path:
            if "[0]" in path: channel = 'LOCATION_X'
            elif "[1]" in path: channel = 'LOCATION_Y'
            elif "[2]" in path: channel = 'LOCATION_Z'
        elif "rotation" in path:
            if "[0]" in path: channel = 'ROTATION_X'
            elif "[1]" in path: channel = 'ROTATION_Y'
            elif "[2]" in path: channel = 'ROTATION_Z'
        elif "scale" in path:
            if "[0]" in path: channel = 'SCALE_X'
            elif "[1]" in path: channel = 'SCALE_Y'
            elif "[2]" in path: channel = 'SCALE_Z'
        
        const.transform_channel = channel # Keep it valid
        const.target_space = 'LOCAL'
        const.mix_mode = 'AFTER' # Additive
        
        # 5. CRITICAL: Assign action using Context Override / Operator if direct assignment fails
        if hasattr(const, "use_bone_object_action"):
            const.use_bone_object_action = False
            
        print(f"[DEBUG] Assigning action to constraint...")
        const.action = action # Try direct first
        
        if const.action != action:
            print(f"[WARNING] Direct assignment failed. Attempting Context Override Workaround...")
            
            # Save current selection
            old_active = bpy.context.view_layer.objects.active
            old_mode = bpy.context.object.mode
            
            try:
                # Ensure we are in POSE mode
                if bpy.context.object.mode != 'POSE':
                    bpy.ops.object.mode_set(mode='POSE')
                
                # Deselect all bones
                bpy.ops.pose.select_all(action='DESELECT')
                
                # Select ONLY the driven bone
                driven_pb.bone.select = True
                driven_obj.data.bones.active = driven_pb.bone
                
                pass 
                
            except Exception as e:
                print(f"[ERROR] Workaround failed: {e}")
            finally:
                # Restore state
                if bpy.context.view_layer.objects.active != old_active:
                     bpy.context.view_layer.objects.active = old_active
                if bpy.context.object.mode != old_mode:
                     bpy.ops.object.mode_set(mode=old_mode)

        print(f"  - const.action AFTER: {const.action}")
        
        # Blender 4.4+ Action Slots
        if hasattr(action, "slots") and hasattr(const, "action_slot"):
            slot = None
            for s in action.slots:
                if s.name == driven_pb.name:
                    slot = s
                    break
            if slot is None:
                try:
                    slot = action.slots.new(for_id=driven_obj)
                except:
                    try:
                        slot = action.slots.new()
                    except:
                        pass
            if slot:
                const.action_slot = slot
        
        # 6. DRIVER SETUP FOR INFLUENCE
        # We want Evaluation Time to be FIXED at the MAX FRAME (3.0)
        # And we drive Influence 0..1
        # UPDATE: We use Keyframed Driver (AVERAGE) to allow Clamping and Curve Editing
        
        const.use_eval_time = True
        const.eval_time = 3.0
        
        # Remove old Eval Time driver if exists
        const.driver_remove("eval_time")
        
        # Setup Influence Driver
        d_fc = const.driver_add("influence")
        drv = d_fc.driver
        drv.type = 'SCRIPTED' # Switched to SCRIPTED for robustness, using 'var'
        drv.expression = "var"
        
        # Check if variable exists, reuse or recreate
        var = None
        if len(drv.variables) > 0:
            var = drv.variables[0]
            var.name = "var"
        else:
            var = drv.variables.new()
            var.name = "var"
        
        # Helper to determine transform type from string path
        # Reuse logic from AddDriverKey if possible, or re-parse
        t_type = 'SCALE_Y' # fallback
        t_component = 1
        is_loc = "location" in props.driver_data_path
        is_rot = "rotation" in props.driver_data_path
        is_scale = "scale" in props.driver_data_path
        
        idx = 0
        if "[1]" in props.driver_data_path: idx = 1
        elif "[2]" in props.driver_data_path: idx = 2
        
        if is_loc:
            t_type = ['LOC_X', 'LOC_Y', 'LOC_Z'][idx]
        elif is_rot:
            t_type = ['ROT_X', 'ROT_Y', 'ROT_Z'][idx]
        elif is_scale:
            t_type = ['SCALE_X', 'SCALE_Y', 'SCALE_Z'][idx]
            
        if is_loc or is_rot or is_scale:
            var.type = 'TRANSFORMS'
            
            # Verify target exists
            target = var.targets[0]
            target.id = props.driver_target
            if props.driver_target.type == 'ARMATURE' and props.driver_bone:
                 target.bone_target = props.driver_bone
                 target.transform_space = 'LOCAL_SPACE'
            else:
                 target.transform_space = 'LOCAL_SPACE'
                 
            target.transform_type = t_type
        else:
            # Fallback for Custom Properties
            if props.driver_target.type == 'ARMATURE' and props.driver_bone:
                 var.type = 'SINGLE_PROP'
                 var.targets[0].id = props.driver_target
                 var.targets[0].data_path = f'pose.bones["{props.driver_bone}"].{props.driver_data_path}'
            else:
                 var.type = 'SINGLE_PROP'
                 var.targets[0].id = props.driver_target
                 var.targets[0].data_path = props.driver_data_path

        # --- KEYFRAME MAPPING & CLAMPING ---
        # 1. Determine Rest Value of Driver
        # If Scale -> 1.0. If Loc/Rot -> 0.0.
        driver_rest = 0.0
        if "scale" in props.driver_data_path: driver_rest = 1.0
        
        # 2. Determine Target Value
        driver_target = driver_val
        
        # 3. Setup Influence Driver with Expression
        # We use a mathematical expression for all drivers (Loc/Rot/Scale)
        # Expression: clamp((var - Rest) / (Target - Rest), 0, 1)
        
        # Calculate Denominator (Target - Rest)
        denom = driver_target - driver_rest
        
        # Safety: Avoid division by zero
        # If target and rest are too close, default to 1 unit distance to avoid error
        if abs(denom) < 0.0001:
             denom = 1.0
             
        # Generate Expression
        # We use f-string to embed constants. "var" is the dynamic input.
        # Format: clamp((var - 0.0) / 1.0, 0, 1)
        expr = f"clamp((var - {driver_rest:.3f}) / {denom:.4f}, 0, 1)"
        drv.expression = expr
        
        # Clear any keyframes (Expression controls it fully)
        # We enforce NO keyframes for this logical setup
        while len(d_fc.keyframe_points) > 0:
             d_fc.keyframe_points.remove(d_fc.keyframe_points[0])
            
        # 5. Handle Types (No longer needed for empty curves, but keeping for safety if switched back)
        # We don't need to set handle types if there are no keyframes.


    def _setup_single_driver(self, driver_obj, id_data_owner, data_path, driver_val, driven_val, props, is_transform, target_transform_type, raw_path, array_index=-1):
        """Helper to create/update a driver on a specific path"""
        
        # Decide where to add driver
        # If id_data_owner is Object/Key, check animation_data
        # If PoseBone, check id_data.animation_data
        
        anim_data_obj = id_data_owner
        if hasattr(id_data_owner, "id_data"):
            anim_data_obj = id_data_owner.id_data
            
        if not anim_data_obj.animation_data:
            anim_data_obj.animation_data_create()
            
        # Find or create fcurve
        fcurve = None
        # Should we search? driver_add usually finds or creates.
        # But we need to be careful not to create duplicates if we can avoid it, 
        # though driver_add acts as "get or create".
        
        if array_index >= 0:
            fcurve = id_data_owner.driver_add(data_path, array_index)
        else:
            fcurve = id_data_owner.driver_add(data_path)
            
        drv = fcurve.driver
        # If new or refreshing, ensure Type
        if drv.type != 'SCRIPTED': # Only reset if not scripted? standardizing
             drv.type = 'SCRIPTED'
        drv.expression = "var" # Default
        
        # Setup Variable (if not exists or force update?)
        # Let's clean and recreate to ensure it matches current settings
        # BUT: preserve existing curve points!
        
        # Check if "var" exists
        var = None
        for v in drv.variables:
            if v.name == "var": 
                var = v
                break
        
        if not var:
            var = drv.variables.new()
            var.name = "var"
        
        # Setup Target
        # Determine Default/Rest Value for Auto-Keying (0 for Loc/Rot, 1 for Scale)
        default_rest_val = 1.0 if (target_transform_type and "SCALE" in target_transform_type) else 0.0
        
        if is_transform and target_transform_type:
            var.type = 'TRANSFORMS'
            target = var.targets[0]
            target.id = driver_obj
            if driver_obj.type == 'ARMATURE' and props.driver_bone:
                target.bone_target = props.driver_bone
            
            target.transform_type = target_transform_type
            target.transform_space = 'LOCAL_SPACE'
        else:
            var.type = 'SINGLE_PROP'
            target = var.targets[0]
            target.id = driver_obj
            if driver_obj.type == 'ARMATURE' and props.driver_bone:
                 target.bone_target = props.driver_bone
                 target.data_path = raw_path
            else:
                 target.data_path = raw_path
                 
        # Auto-insert Rest Key if needed (only if "new" - practically hard to detect "new" perfectly per curve)
        # We can check if curve has points.
        if len(fcurve.keyframe_points) == 0:
             # Just add rest pose?
             # Only if current pose is different from rest?
             if abs(driver_val - default_rest_val) > 0.001:
                  fcurve.keyframe_points.insert(default_rest_val, 0.0) # Assume Default Driven Value is 0 ? 
                  # WAIT: Default Driven Value for BONES might not be 0.
                  # For Shape Keys, 0 is default.
                  # For Bones: Loc/Rot is 0 (usually). Scale is 1.
                  # If we drive Bone SCALING, the 'rest' driven value is 1.
                  
                  # We should match 'Rest' of Driven to 'Rest' of Driver.
                  # For simplicity, we assume Driven Rest is 0 for Loc/Rot, 1 for Scale.
                  # We can infer from data_path?
                  
                  driven_rest = 0.0
                  if "scale" in data_path: driven_rest = 1.0
                  if "quaternion" in data_path and array_index == 0: driven_rest = 1.0 # W component
                  
                  fcurve.keyframe_points.insert(default_rest_val, driven_rest)

        # Remove Modifiers
        for mod in fcurve.modifiers:
            fcurve.modifiers.remove(mod)
            
        # Create Key
        kp = fcurve.keyframe_points.insert(driver_val, driven_val)
        
        # Interpolation
        kp.interpolation = props.driver_interpolation
        if props.driver_interpolation == 'BEZIER':
            kp.handle_left_type = 'AUTO_CLAMPED'
            kp.handle_right_type = 'AUTO_CLAMPED'
            
        fcurve.update()


class BSETUP_OT_SetChannel(bpy.types.Operator):
    """Set the driver data path to a specific channel"""
    bl_idname = "bsetup.set_channel"
    bl_label = "Set Channel"
    
    path: bpy.props.StringProperty()
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        props.driver_data_path = self.path
        return {'FINISHED'}


class BSETUP_OT_MirrorDriver(bpy.types.Operator):
    """Mirror the current driver setup to the opposite side (L<->R)"""
    bl_idname = "bsetup.mirror_driver"
    bl_label = "Mirror Driver"
    bl_options = {'REGISTER', 'UNDO'}
    
    invert_values: bpy.props.BoolProperty(
        name="Invert Values",
        description="Negate the X-axis values (Driver values) for the mirrored curve",
        default=False
    )
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        
        driver_obj = props.driver_target
        driven_obj = props.driven_object
        
        if not driver_obj or not driven_obj:
            self.report({'ERROR'}, "Driver or Driven object missing")
            return {'CANCELLED'}

        if props.driven_type == 'POSE':
             return bpy.ops.bsetup.mirror_pose_driver('INVOKE_DEFAULT', invert_driver=self.invert_values)
            
        if not props.driven_key:
            self.report({'ERROR'}, "No Driven Shape Key selected")
            return {'CANCELLED'}
            
        # Get current driver curve
        key_data = driven_obj.data.shape_keys
        if not key_data or not key_data.animation_data:
            self.report({'ERROR'}, "No driver found on current shape key")
            return {'CANCELLED'}
            
        source_path = f'key_blocks["{props.driven_key}"].value'
        source_fcurve = None
        for fc in key_data.animation_data.drivers:
            if fc.data_path == source_path:
                source_fcurve = fc
                break
                
        if not source_fcurve:
            self.report({'ERROR'}, f"No driver on {props.driven_key}")
            return {'CANCELLED'}
            
        # Flip names
        flipped_bone = flip_name(props.driver_bone) if props.driver_bone else None
        flipped_key = flip_name(props.driven_key)
        
        if not flipped_key:
            self.report({'ERROR'}, f"Could not find mirror name for '{props.driven_key}'")
            return {'CANCELLED'}
        
        # Check existence before logic
        if flipped_key not in key_data.key_blocks:
             self.report({'ERROR'}, f"Mirrored shape key '{flipped_key}' not found. Use 'Mirror Shape & Driver' to create it.")
             return {'CANCELLED'}

        if driver_obj.type == 'ARMATURE' and props.driver_bone:
            if not flipped_bone:
                self.report({'ERROR'}, f"Could not find mirror name for bone '{props.driver_bone}'")
                return {'CANCELLED'}
            if flipped_bone not in driver_obj.pose.bones:
                self.report({'ERROR'}, f"Mirrored bone '{flipped_bone}' not found")
                return {'CANCELLED'}

        success, msg = mirror_shape_driver_logic(self, context, driver_obj, driven_obj, props.driven_key, flipped_key, self.invert_values)
        
        if not success:
             self.report({'ERROR'}, msg)
             return {'CANCELLED'}
        
        self.report({'INFO'}, f"Mirrored driver to '{flipped_key}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
