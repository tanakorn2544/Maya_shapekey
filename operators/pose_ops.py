import bpy
from .utils import flip_name, copy_driver_to_fcurve

class BSETUP_OT_MirrorPoseDriver(bpy.types.Operator):
    """Mirror drivers from selected bones to their symmetrical counterparts"""
    bl_idname = "bsetup.mirror_pose_driver"
    bl_label = "Mirror Pose Driver"
    bl_options = {'REGISTER', 'UNDO'}
    
    invert_driver: bpy.props.BoolProperty(
        name="Invert Driver",
        description="Invert the driver input values (e.g. if the mirror bone moves in opposite direction)",
        default=False
    )
    
    mirror_axis_values: bpy.props.BoolProperty(
         name="Mirror Component Values",
         description="Flip values for X-Location, Y-Rotation, and Z-Rotation on the target action (Standard Rig Behavior)",
         default=True
    )

    driver_expression: bpy.props.StringProperty(
        name="Driver Expression",
        description="Override the mathematical expression for the driver (Default: 'var'). Use '-var' to invert, or complex logic.",
        default="var"
    )
    
    use_scale_fix: bpy.props.BoolProperty(
        name="Smart Scale Fix",
        description="Auto-apply normalization formula for Scale drivers (clamp((var-1)/(tgt-1))...)",
        default=False
    )
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        
        if props.driven_type != 'POSE':
             self.report({'WARNING'}, "Not in Pose Mode")
             return {'CANCELLED'}
             
        selected_bones = context.selected_pose_bones
        if not selected_bones:
             self.report({'WARNING'}, "No bones selected")
             return {'CANCELLED'}
             
        count = 0
        
        for pb in selected_bones:
            # 1. Find Mirror Bone
            mirror_name = flip_name(pb.name)
            if not mirror_name:
                 continue 
                 
            armature = pb.id_data
            if mirror_name not in armature.pose.bones:
                 continue
            
            mirror_pb = armature.pose.bones[mirror_name]
                 
            # 2. Iterate Constraints on Source
            for const in pb.constraints:
                if const.type == 'ACTION' and const.name.startswith("SDK_"):
                    # Found a driver constraint
                    src_action = const.action
                    if not src_action: continue
                    
                    # 3. Determine Constraint Target Info
                    target_obj = const.target
                    target_bone_name = const.subtarget
                    
                    # Flip target bone
                    if target_bone_name:
                        target_bone_name = flip_name(target_bone_name) or target_bone_name
                    
                    # Flip target object (rare)
                    if target_obj and flip_name(target_obj.name) and flip_name(target_obj.name) in bpy.data.objects:
                        target_obj = bpy.data.objects[flip_name(target_obj.name)]
                        
                    # 4. Create/Get Target Constraint
                    new_const_name = flip_name(const.name)
                    if not new_const_name: new_const_name = const.name
                    
                    tgt_const = mirror_pb.constraints.get(new_const_name)
                    if tgt_const:
                        # Force remove to ensure clean state (Fixes assignment bugs)
                        mirror_pb.constraints.remove(tgt_const)
                        
                    tgt_const = mirror_pb.constraints.new('ACTION')
                    tgt_const.name = new_const_name
                        
                    # Copy Settings
                    tgt_const.target = target_obj
                    tgt_const.subtarget = target_bone_name
                    tgt_const.min = const.min
                    tgt_const.max = const.max
                    tgt_const.frame_start = const.frame_start
                    tgt_const.frame_end = const.frame_end
                    tgt_const.transform_channel = const.transform_channel
                    tgt_const.target_space = const.target_space
                    tgt_const.mix_mode = const.mix_mode # Important: Copy AFTER/ADD
                    
                    # Copy Evaluation Time Settings (Critical for this setup)
                    if hasattr(const, "use_eval_time"):
                        tgt_const.use_eval_time = const.use_eval_time
                        tgt_const.eval_time = const.eval_time
                        
                        # SAFETY: If we detect an influence driver on source, we almost certainly want this ON
                        # because that's how this addon works (Fixed Action Time, Driven Influence)
                        # We don't check for driver here, but we can assume if use_eval_time is True, it's True.
                        if const.use_eval_time:
                             tgt_const.use_eval_time = True # Force set explicit
                    
                    # 5. Mirror Action
                    # Ensure name is FLIPPED.
                    new_action_name = flip_name(src_action.name)
                    
                    if not new_action_name: 
                         # Try manual replacement if flip failed (e.g. name didn't have L/R but bone did?)
                         new_action_name = src_action.name.replace(pb.name, mirror_name)
                    
                    # SAFETY: If name is still same (e.g. "MyAction" -> "MyAction"), we get a collision.
                    if new_action_name == src_action.name:
                        new_action_name = f"{src_action.name}_Mirrored"
                    
                    # 5b. COPY SOURCE ACTION (Preserves metadata/groups)
                    if new_action_name in bpy.data.actions:
                        # If exists, we should probably start fresh to ensure clean state? 
                        # Or update it? For mirroring, we usually want to Overwrite.
                        # Easiest way: Remove old, copy new.
                        bpy.data.actions.remove(bpy.data.actions[new_action_name])
                    
                    tgt_action = src_action.copy()
                    tgt_action.name = new_action_name
                    tgt_action.use_fake_user = True
                    
                    # Robust Action Assignment
                    if hasattr(tgt_const, "use_bone_object_action"):
                        tgt_const.use_bone_object_action = False
                    
                    print(f"[DEBUG] Assigning Action '{tgt_action.name}' to Constraint '{tgt_const.name}' on '{mirror_pb.name}'")
                    tgt_const.action = tgt_action
                    
                    # Workaround if direct assignment failed (sometimes happens in 4.0+)
                    if tgt_const.action != tgt_action:
                        print(f"[WARNING] Direct assignment failed. Attempting Context Override Workaround...")
                        try:
                            # Preferred method for Blender 3.2+
                            if hasattr(context, "temp_override"):
                                with context.temp_override(active_object=armature, object=armature):
                                    bpy.ops.object.mode_set(mode='POSE')
                                    bpy.ops.pose.select_all(action='DESELECT')
                                    mirror_pb.bone.select = True
                                    armature.data.bones.active = mirror_pb.bone
                                    tgt_const.action = tgt_action
                        except Exception as e:
                            print(f"[ERROR] Assignment Workaround Exception: {e}")
                            
                    # FINAL CHECK
                    if tgt_const.action != tgt_action:
                         self.report({'ERROR'}, f"Failed to assign Action '{tgt_action.name}' to mirrored bone '{mirror_pb.name}'")
                    else:
                         print(f"[SUCCESS] Action assigned successfully.")
                         
                         # --- APPLY PROPERTIES AFTER ACTION ASSIGNMENT (Fixes Reset/Override Issues) ---
                         try:
                             tgt_const.target = target_obj
                             tgt_const.subtarget = target_bone_name
                             tgt_const.min = const.min
                             tgt_const.max = const.max
                             tgt_const.frame_start = const.frame_start
                             tgt_const.frame_end = const.frame_end
                             tgt_const.transform_channel = const.transform_channel
                             tgt_const.target_space = const.target_space
                             tgt_const.mix_mode = const.mix_mode
                             
                             if hasattr(const, "use_eval_time"):
                                 tgt_const.use_eval_time = const.use_eval_time
                                 tgt_const.eval_time = const.eval_time
                         except Exception as e:
                             print(f"[WARNING] property sync error: {e}")




                    
                    # 6. MODIFY KEYS IN PLACE (Since we copied)
                    
                    # We need to iterate curves and FLIP PATHS and VALUES
                    # NOTE: Modifying data_path while iterating might be risky if we rely on it?
                    # FCurves are list.
                    
                    for fc in tgt_action.fcurves:
                        # Path: pose.bones["Bone.L"].location
                        # We need to construct path for Mirror Bone: pose.bones["Bone.R"].location
                        
                        original_path = fc.data_path
                        new_path = original_path.replace(pb.name, mirror_name)
                        
                        # Apply new path
                        fc.data_path = new_path
                        
                        # Update Group name if it matches bone name
                        if fc.group and fc.group.name == pb.name:
                             # We can't rename group easily if it's shared? 
                             # But in a mirrored action, the group SHOULD be the mirror bone.
                             # Check if group exists?
                             pass # Blender handles groups loosely.
                             # Better: Set group explicitly
                             # fc.group = tgt_action.groups.new(mirror_pb.name) # Might fail if exists.
                             # Usually we don't need to stress groups for functionality.
                        
                        # Flip Logic for Values
                        flip_mult = 1.0
                        
                        if self.mirror_axis_values:
                             if "location" in new_path and fc.array_index == 0: flip_mult = -1.0
                             if "rotation_euler" in new_path and fc.array_index in {1,2}: flip_mult = -1.0
                             
                             # Quaternion Flipping for X-Mirror
                             # Quaternions are (W, X, Y, Z). 
                             # Standard X-Mirror usually flips Y and Z components (i.e. 180 deg rot around X).
                             # W (0) -> Keep
                             # X (1) -> Keep
                             # Y (2) -> Flip
                             # Z (3) -> Flip
                             if "rotation_quaternion" in new_path and fc.array_index in {2,3}: flip_mult = -1.0
                             
                             # Axis Angle (W, X, Y, Z) - W is Angle. XYZ is Axis.
                             # Flip Y and Z of Axis.
                             if "rotation_axis_angle" in new_path and fc.array_index in {2,3}: flip_mult = -1.0
                        
                        if flip_mult != 1.0:
                             for kp in fc.keyframe_points:
                                  kp.co[1] *= flip_mult
                                  kp.handle_left[1] *= flip_mult
                                  kp.handle_right[1] *= flip_mult
                             
                    # 7. Mirror Influence Driver
                    # The source constraint has a driver on "influence"
                    # We need to copy it to tgt_const
                    
                    src_drv = None
                    # Find driver on source constraint
                    # Constraints drivers are on the Object/Bone ID_Data?
                    # No, usually on the Object/Armature data block or Object block?
                    # Armature -> pose.bones["Bone"].constraints["Name"].influence
                    
                    # We need to find the fcurve
                    anim_data = armature.animation_data
                    if anim_data and anim_data.drivers:
                        path_check = f'pose.bones["{pb.name}"].constraints["{const.name}"].influence'
                        for fc in anim_data.drivers:
                             if fc.data_path == path_check:
                                 src_drv = fc
                                 break
                    
                    if src_drv:
                        # Drive proper target path
                        tgt_path = f'pose.bones["{mirror_pb.name}"].constraints["{tgt_const.name}"].influence'
                        
                        # Remove existing
                        try: armature.driver_remove(tgt_path)
                        except: pass
                        
                        tgt_drv_fc = armature.driver_add(tgt_path)
                        
                        # Auto-Detect Inversion Logic
                        # If the driver relies on LOC_X, ROT_Y, ROT_Z -> These flip signs in mirror.
                        # We must invert the driver curve inputs.
                        auto_invert = False
                        if src_drv.driver.type == 'SCRIPTED' or src_drv.driver.type == 'AVERAGE':
                             for v in src_drv.driver.variables:
                                 if v.type == 'TRANSFORMS':
                                     # Check transform type
                                     tt = v.targets[0].transform_type
                                     if tt in {'LOC_X', 'ROT_Y', 'ROT_Z', 'ROT_W'}: # Quats are complex but often flip W or specific axes
                                          # Note: Rot Y/Z in Euler flips.
                                          auto_invert = True
                                          break
                        
                        final_invert = self.invert_driver or auto_invert
                        if auto_invert:
                             print(f"[DEBUG] Auto-Inverting Driver Curve for {mirror_pb.name} (Detected {tt})")
                        
                        # Copy logic
                        # If the user provided a custom expression, we apply it AFTER copying

                        
                        # --- MIRROR LOGIC UPDATE for Expression-based Drivers (e.g. Scale) ---
                        # If the source driver has NO keyframes (because it uses pure expression),
                        # copy_driver_to_fcurve might not work perfectly or we need special handling.
                        
                        is_expression_only = len(src_drv.keyframe_points) == 0
                        
                        if is_expression_only:
                            print(f"[DEBUG] Mirroring Expression-Only Driver (Scale Fix?)")
                            
                            # 1. Copy Driver Properties Manually
                            tgt_drv_fc.driver.type = src_drv.driver.type
                            tgt_drv_fc.driver.expression = src_drv.driver.expression
                            
                            # 2. Recreate Variables
                            for src_var in src_drv.driver.variables:
                                new_var = tgt_drv_fc.driver.variables.new()
                                new_var.name = src_var.name
                                new_var.type = src_var.type
                                
                                # Copy Targets
                                for i, src_tgt in enumerate(src_var.targets):
                                    tgt = new_var.targets[i]
                                    tgt.id = src_tgt.id # Start with same ID
                                    
                                    # Handle ID Flipping (Object)
                                    if src_tgt.id and hasattr(src_tgt.id, "name"):
                                        flipped_id_name = flip_name(src_tgt.id.name)
                                        if flipped_id_name and flipped_id_name in bpy.data.objects:
                                             tgt.id = bpy.data.objects[flipped_id_name]
                                    
                                    # Handle TRANSFORMS
                                    if src_var.type == 'TRANSFORMS':
                                        tgt.transform_type = src_tgt.transform_type
                                        tgt.transform_space = src_tgt.transform_space
                                        
                                        # FLIP BONE TARGET
                                        if src_tgt.bone_target:
                                            # Try logic flip
                                            flipped_bone = flip_name(src_tgt.bone_target)
                                            print(f"[DEBUG] Flipping Var Target: '{src_tgt.bone_target}' -> '{flipped_bone}'")
                                            
                                            if flipped_bone:
                                                 tgt.bone_target = flipped_bone
                                                 print(f"[DEBUG] SUCCESS: Flipped Bone Target to '{tgt.bone_target}'")
                                            else:
                                                 # Fallback: Try simple replace if flip_name failed
                                                 bt = src_tgt.bone_target
                                                 print(f"[DEBUG] FAIL: flip_name returned None for '{bt}'. Trying Fallback...")
                                                 
                                                 # New Logic: Try standard replacements without regex overkill first
                                                 if ".L" in bt: tgt.bone_target = bt.replace(".L", ".R")
                                                 elif ".R" in bt: tgt.bone_target = bt.replace(".R", ".L")
                                                 elif "_L" in bt: tgt.bone_target = bt.replace("_L", "_R")
                                                 elif "_R" in bt: tgt.bone_target = bt.replace("_R", "_L")
                                                 else:
                                                     # Try Regex for cases like Bone_L.001
                                                     import re
                                                     if re.search(r'(_[Ll])\.', bt):
                                                         tgt.bone_target = re.sub(r'(_[Ll])\.', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + ".", bt)
                                                     elif re.search(r'(\.[Ll])\.', bt):
                                                         tgt.bone_target = re.sub(r'(\.[Ll])\.', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + ".", bt)
                                                     else:
                                                         tgt.bone_target = src_tgt.bone_target
                                                         print(f"[WARNING] Could not flip bone target '{src_tgt.bone_target}'")
                                                 
                                                 print(f"[DEBUG] Fallback Result: '{tgt.bone_target}'")
                                    else:
                                        # Single Prop
                                        tgt.data_path = src_tgt.data_path
                                        # Try flipping path (e.g. pose.bones["Bone.L"])
                                        # This is complex but usually handled by flip_name if simple string
                                        pass

                            # 3. Apply Expression
                            # Handle Auto-Invert (e.g. Loc X needs to be flipped)
                            # Expression is typically: clamp((var - Rest) / Denom, ...)
                            if auto_invert:
                                 # We wrap 'var' with '(-var)'
                                 # This is a safe heuristic for our specific generated expressions.
                                 if "var" in tgt_drv_fc.driver.expression:
                                      tgt_drv_fc.driver.expression = tgt_drv_fc.driver.expression.replace("var", "(-var)")
                                      print(f"[DEBUG] Inverted Expression var: {tgt_drv_fc.driver.expression}")
                            
                            tgt_drv_fc.update()
                            
                        else:
                             # Standard Keyframe-based Copy
                             if self.driver_expression != "var" or self.use_scale_fix:
                                  # We copy first to get variables, then override expression
                                  copy_driver_to_fcurve(src_drv, tgt_drv_fc, False)
                                  tgt_drv_fc.driver.type = 'SCRIPTED'
                                  
                                  # Expression Logic
                                  final_expr = self.driver_expression
                                  
                                  # Auto-Override if Scale Fix is requested
                                  if self.use_scale_fix:
                                      final_expr = "clamp((var - 1) / (<TARGET> - 1), 0, 1)"
                                  
                                  # Token Substitution: <TARGET>
                                  target_val = 1.0
                                  if len(src_drv.keyframe_points) >= 2:
                                      target_val = src_drv.keyframe_points[1].co[0]
                                  
                                  if "<TARGET>" in final_expr:
                                      final_expr = final_expr.replace("<TARGET>", f"{target_val:.4f}")
                                      
                                  tgt_drv_fc.driver.expression = final_expr
                                  
                                  # Remove keyframes for custom expression
                                  for k in tgt_drv_fc.keyframe_points:
                                       tgt_drv_fc.keyframe_points.remove(k)
                                       
                                  tgt_drv_fc.update()
                             else:
                                  # Standard Auto Logic
                                  copy_driver_to_fcurve(src_drv, tgt_drv_fc, final_invert)
                        
                        # Fixup Variable Targets - GUIDED SAFETY CHECK
                        # We iterate variables and check if they are still pointing to the SOURCE bone.
                        # If so, we attempt to flip them.
                        # This catches cases where upstream logic failed (e.g. reload issues) but avoids double-flipping valid changes.
                        
                        try:
                            # Iterate Target Variables
                            for i, var in enumerate(tgt_drv_fc.driver.variables):
                                for j, tgt in enumerate(var.targets):
                                    if not (hasattr(tgt, "bone_target") and tgt.bone_target):
                                        continue
                                        
                                    # Get Source Equivalent for Comparison
                                    # (Assumes 1:1 mapping preserved from copy)
                                    src_bone_target = None
                                    if i < len(src_drv.driver.variables):
                                        s_var = src_drv.driver.variables[i]
                                        if j < len(s_var.targets):
                                            src_bone_target = s_var.targets[j].bone_target
                                    
                                    # CRITICAL GUARD: Only flip if Target == Source (Unchanged)
                                    # This prevents double-flipping if upstream already worked.
                                    if src_bone_target and tgt.bone_target == src_bone_target:
                                        print(f"[DEBUG] Detected Unflipped Target '{tgt.bone_target}'. Attempting Force Flip...")
                                        
                                        flipped_bone = flip_name(tgt.bone_target)
                                        
                                        # Fallback Manual
                                        if not flipped_bone or flipped_bone == tgt.bone_target:
                                             import re
                                             bt = tgt.bone_target
                                             if ".L" in bt: flipped_bone = bt.replace(".L", ".R")
                                             elif ".R" in bt: flipped_bone = bt.replace(".R", ".L")
                                             elif "_L" in bt: flipped_bone = bt.replace("_L", "_R")
                                             elif "_R" in bt: flipped_bone = bt.replace("_R", "_L")
                                             else:
                                                 if re.search(r'(_[Ll])\.', bt):
                                                     flipped_bone = re.sub(r'(_[Ll])\.', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + ".", bt)
                                                 elif re.search(r'(\.[Ll])\.', bt):
                                                     flipped_bone = re.sub(r'(\.[Ll])\.', lambda m: m.group(1).replace('l', 'r').replace('L', 'R') + ".", bt)
                                        
                                        if flipped_bone and flipped_bone != tgt.bone_target:
                                             tgt.bone_target = flipped_bone
                                             print(f"[DEBUG] Force Flip Success: -> {tgt.bone_target}")
                                    
                        except Exception as e:
                            print(f"[ERROR] Safety Check Exception: {e}")
                        
                        count += 1
         
        # Force updates to ensure UI and Depsgraph catch up
        if selected_bones:
            id_data = selected_bones[0].id_data
            if id_data: id_data.update_tag()
            
        context.view_layer.update()
        
        self.report({'INFO'}, f"Mirrored {count} SDK Actions")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class BSETUP_OT_RemovePoseDriver(bpy.types.Operator):
    """Remove drivers from selected bones based on active channels (Loc/Rot/Scale)"""
    bl_idname = "bsetup.remove_pose_driver"
    bl_label = "Remove Driver"
    bl_label = "Remove Driver"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Optional property for targeted removal via UI List
    target_name: bpy.props.StringProperty(name="Target Name", default="")
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        
        # Check if Pose Mode
        if props.driven_type != 'POSE':
             self.report({'WARNING'}, "Not in Pose Mode")
             return {'CANCELLED'}
             
        # Check Selection
        # Robust retrieval of selected bones
        selected_bones = []
        arm_obj = None
        
        # 1. Try to find the Armature from inputs
        if props.driven_object and props.driven_object.type == 'ARMATURE':
            arm_obj = props.driven_object
        elif context.active_object and context.active_object.type == 'ARMATURE':
            arm_obj = context.active_object
            
        # 2. If found, check its pose bones
        if arm_obj:
             # Ensure we can access pose
             if arm_obj.mode == 'POSE' or (arm_obj.pose is not None):
                 for pb in arm_obj.pose.bones:
                     if pb.bone.select:
                         selected_bones.append(pb)
                         
        if not selected_bones:
             # Fallback to context if simple
             selected_bones = context.selected_pose_bones
             
        if not selected_bones:
             self.report({'WARNING'}, "No bones selected. Select a bone in Pose Mode.")
             return {'CANCELLED'}
             
        self.report({'INFO'}, f"Processing {len(selected_bones)} bones from armature '{arm_obj.name if arm_obj else 'Context'}'")
             
        # What to remove?
        rm_loc = props.drive_location
        rm_rot = props.drive_rotation
        rm_scale = props.drive_scale
        
        # If none selected, assume ALL (User convenience)
        if not (rm_loc or rm_rot or rm_scale):
             rm_loc = True
             rm_rot = True
             rm_scale = True
             # self.report({'WARNING'}, "No channels selected (Loc/Rot/Scale)")
             # return {'CANCELLED'}
             
        count = 0
        actions_removed = 0
        
        for pb in selected_bones:
            # Report what we see (Visible to User)
            self.report({'INFO'}, f"Checking Bone {pb.name}: Found {len(pb.constraints)} constraints")
            
            constraints_to_remove = []
            
            for const in pb.constraints:
                # Check 1: Must be ACTION constraint
                if const.type != 'ACTION':
                     continue
                     
                # Check 2: Name prefix
                # Note: Prefix might be SDK_ or just SDK if ID is empty? 
                # Also handling older naming conventions just in case
                is_sdk = const.name.startswith("SDK") 
                
                if is_sdk:
                    # Targeted Removal Logic
                    # Priority: Operator Arg > Props Text Field > All
                    
                    target_suffix = self.target_name.strip()
                    if not target_suffix:
                         target_suffix = props.pose_action_name.strip() if hasattr(props, "pose_action_name") else ""
                    
                    if target_suffix:
                        # Only remove exact match
                        target_full_name = f"SDK_{target_suffix}"
                        if const.name == target_full_name:
                            constraints_to_remove.append(const)
                    else:
                        # Remove ALL SDK constraints (Default/Legacy)
                        constraints_to_remove.append(const)
                    
                    # NOTE: We skip the channel check because it seems to be fragile 
                    # and the user just wants the SDK gone.
            
            for const in constraints_to_remove:
                # Also try to remove the assigned Action
                action = const.action
                if action:
                    action.use_fake_user = False
                    # Force remove if it's an SDK action
                    if action.name.startswith("SDK"):
                        bpy.data.actions.remove(action)
                        actions_removed += 1
                
                pb.constraints.remove(const)
                count += 1
                        
        self.report({'INFO'}, f"Removed {count} SDK Constraints and {actions_removed} Actions")
        return {'FINISHED'}


class BSETUP_OT_SelectDrivenBones(bpy.types.Operator):
    """Select bones that have the specific SDK Action assigned"""
    bl_idname = "bsetup.select_driven_bones"
    bl_label = "Select Driven Bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    target_name: bpy.props.StringProperty(name="Target Name", default="")
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        
        # Check if Pose Mode
        if props.driven_type != 'POSE':
             self.report({'WARNING'}, "Not in Pose Mode")
             return {'CANCELLED'}
             
        # Find Armature
        arm_obj = None
        if props.driven_object and props.driven_object.type == 'ARMATURE':
            arm_obj = props.driven_object
        elif context.active_object and context.active_object.type == 'ARMATURE':
            arm_obj = context.active_object
            
        if not arm_obj:
             self.report({'WARNING'}, "No Armature found")
             return {'CANCELLED'}
             
        if not self.target_name:
             self.report({'WARNING'}, "No Action Name specified")
             return {'CANCELLED'}
             
        target_full_name = f"SDK_{self.target_name}"
        count = 0
        
        # Iterate all bones
        if arm_obj.mode == 'POSE':
             for pb in arm_obj.pose.bones:
                found = False
                for const in pb.constraints:
                    if const.type == 'ACTION' and const.name == target_full_name:
                        found = True
                        break
                
                if found:
                    pb.bone.select = True
                    count += 1
        
        if count > 0:
            self.report({'INFO'}, f"Selected {count} bones with action '{self.target_name}'")
        else:
            self.report({'WARNING'}, f"No bones found with action '{self.target_name}'")
            
        return {'FINISHED'}
