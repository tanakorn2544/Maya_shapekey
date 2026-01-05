import bpy

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
        
        if driver_obj and driver_obj.type == 'ARMATURE' and props.driver_bone:
             if props.driver_bone not in driver_obj.pose.bones:
                 self.report({'ERROR'}, f"Bone '{props.driver_bone}' not found")
                 return {'CANCELLED'}
        
        if not driver_obj or not driven_obj:
            self.report({'ERROR'}, "Driver or Driven object missing")
            return {'CANCELLED'}
            
        if not props.driven_key:
             self.report({'ERROR'}, "No Driven Shape Key selected")
             return {'CANCELLED'}

        raw_path = props.driver_data_path
        if not raw_path:
             self.report({'ERROR'}, "Driver Data Path is empty")
             return {'CANCELLED'}

        # --- SMART TRANSFORM DETECTION ---
        # Detect if we are targeting a standard transform channel (Loc/Rot/Scale)
        # to use the robust 'TRANSFORMS' variable type (handles Quaternions etc).
        
        target_transform_type = None # 'LOC_X', 'ROT_Z', etc.
        target_component = 0 # 0, 1, 2
        is_transform = False
        
        # Simple parsing of standard paths set by our buttons
        if raw_path.startswith("location"):
            is_transform = True
            if "[0]" in raw_path: target_transform_type = 'LOC_X'; target_component = 0
            elif "[1]" in raw_path: target_transform_type = 'LOC_Y'; target_component = 1
            elif "[2]" in raw_path: target_transform_type = 'LOC_Z'; target_component = 2
            
        elif raw_path.startswith("rotation"): # rotation_euler / rotation_quaternion checking
            is_transform = True
            # We map any rotation path request to Euler decomposition for the driver
            if "[0]" in raw_path: target_transform_type = 'ROT_X'; target_component = 0
            elif "[1]" in raw_path: target_transform_type = 'ROT_Y'; target_component = 1
            elif "[2]" in raw_path: target_transform_type = 'ROT_Z'; target_component = 2
            
        elif raw_path.startswith("scale"):
            is_transform = True
            if "[0]" in raw_path: target_transform_type = 'SCALE_X'; target_component = 0
            elif "[1]" in raw_path: target_transform_type = 'SCALE_Y'; target_component = 1
            elif "[2]" in raw_path: target_transform_type = 'SCALE_Z'; target_component = 2

        # --- 1. FETCH DRIVER VALUE ---
        current_driver_val = 0.0
        
        if is_transform and target_transform_type:
            # Calculate from Matrix (Handles Quaternions, Constraints, etc correctly for LOCAL space)
            # We want LOCAL value to match 'Structure' / 'Maya SDK' feel.
            
            matrix = None
            rot_mode = 'XYZ' # Default
            
            if driver_obj.type == 'ARMATURE' and props.driver_bone:
                pb = driver_obj.pose.bones.get(props.driver_bone)
                if pb:
                    matrix = pb.matrix_basis # Local to parent
                    rot_mode = pb.rotation_mode
            else:
                matrix = driver_obj.matrix_basis # Local to parent
                rot_mode = driver_obj.rotation_mode
            
            if matrix:
                if "LOC" in target_transform_type:
                    current_driver_val = matrix.to_translation()[target_component]
                elif "ROT" in target_transform_type:
                    # Driver 'ROT_X/Y/Z' usually uses Euler representation
                    # We convert the matrix to Euler
                    safe_mode = rot_mode if rot_mode in {'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX'} else 'XYZ'
                    euls = matrix.to_euler(safe_mode)
                    current_driver_val = euls[target_component]
                elif "SCALE" in target_transform_type:
                    current_driver_val = matrix.to_scale()[target_component]
        else:
            # Fallback to Raw Property Path (Custom Props)
            try:
                if driver_obj.type == 'ARMATURE' and props.driver_bone:
                    # Try bone first
                    pb = driver_obj.pose.bones.get(props.driver_bone)
                    found_on_bone = False
                    if pb:
                        try:
                            current_driver_val = pb.path_resolve(raw_path)
                            found_on_bone = True
                        except:
                            pass

                    if not found_on_bone:
                        current_driver_val = driver_obj.path_resolve(raw_path)
                else:
                    current_driver_val = driver_obj.path_resolve(raw_path)
            except:
                 self.report({'ERROR'}, f"Could not resolve path: {raw_path}")
                 return {'CANCELLED'}

        # --- 2. FETCH DRIVEN VALUE ---
        key_block = driven_obj.data.shape_keys.key_blocks.get(props.driven_key)
        if not key_block:
             self.report({'ERROR'}, "Shape Key not found")
             return {'CANCELLED'}
        current_driven_val = key_block.value
        
        # Update UI props
        props.driver_value = float(current_driver_val)
        props.driven_value = float(current_driven_val)
        
        # --- 3. CREATE/UPDATE DRIVER ---
        key_data = driven_obj.data.shape_keys
        data_path = f'key_blocks["{props.driven_key}"].value'
        
        if not key_data.animation_data:
            key_data.animation_data_create()
            
        fcurve = None
        for fc in key_data.animation_data.drivers:
            if fc.data_path == data_path:
                fcurve = fc
                break
                
        if not fcurve:
            # Create new driver
            fcurve = key_data.driver_add(data_path)
            drv = fcurve.driver
            drv.type = 'SCRIPTED'
            drv.expression = "var"
            
            # Setup Variable
            var = drv.variables.new()
            var.name = "var"
            
            # Determine Default/Rest Value for Auto-Keying
            # Loc/Rot defaults to 0. Scale defaults to 1.
            default_rest_val = 1.0 if (target_transform_type and "SCALE" in target_transform_type) else 0.0
            
            if is_transform and target_transform_type:
                # Use TRANSFORMS type
                var.type = 'TRANSFORMS'
                target = var.targets[0]
                target.id = driver_obj
                if driver_obj.type == 'ARMATURE' and props.driver_bone:
                    target.bone_target = props.driver_bone
                
                target.transform_type = target_transform_type
                target.transform_space = 'LOCAL_SPACE' # Crucial for rig-like behavior
                
            else:
                # Use SINGLE_PROP type
                var.type = 'SINGLE_PROP'
                target = var.targets[0]
                target.id = driver_obj
                if driver_obj.type == 'ARMATURE' and props.driver_bone:
                     target.bone_target = props.driver_bone
                     target.data_path = raw_path
                else:
                     target.data_path = raw_path
            
            # Auto-insert Rest Key (0,0) or (1,0) if this is a NEW driver
            # This ensures that if the user keys the Active pose (e.g. 1.0), 
            # we implicitly have a start point at Rest.
            # Only do this if the current key being added is NOT the rest pose itself.
            if abs(current_driver_val - default_rest_val) > 0.001:
                 fcurve.keyframe_points.insert(default_rest_val, 0.0)
            
        # Remove Modifiers & Key
        for mod in fcurve.modifiers:
            fcurve.modifiers.remove(mod)
            
        # Create key
        kp_driver = fcurve.keyframe_points.insert(current_driver_val, current_driven_val)
        
        # Apply Interpolation
        kp_driver.interpolation = props.driver_interpolation
        if props.driver_interpolation == 'BEZIER':
            kp_driver.handle_left_type = 'AUTO_CLAMPED'
            kp_driver.handle_right_type = 'AUTO_CLAMPED'
            
        fcurve.update()

        self.report({'INFO'}, f"Keyed {props.driven_key} at {current_driven_val:.2f} (Driver: {current_driver_val:.2f}) [{props.driver_interpolation}]")
        return {'FINISHED'}

class BSETUP_OT_AddComboShape(bpy.types.Operator):
    """Create a new shape key driven by the product of two other keys"""
    bl_idname = "bsetup.add_combo_shape"
    bl_label = "Create Combo Shape"
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        obj = context.active_object
        
        if not obj or not obj.data.shape_keys:
             self.report({'ERROR'}, "Object has no shape keys")
             return {'CANCELLED'}
             
        kb = obj.data.shape_keys.key_blocks
        if props.combo_shape_a not in kb or props.combo_shape_b not in kb:
             self.report({'ERROR'}, "Invalid Input Shapes")
             return {'CANCELLED'}
             
        # Create new shape
        new_shape = obj.shape_key_add(name=props.combo_name, from_mix=False)
        
        # Add Driver
        # Path: key_blocks["Name"].value
        fcurve = obj.data.shape_keys.driver_add(f'key_blocks["{new_shape.name}"].value')
        drv = fcurve.driver
        drv.type = 'SCRIPTED'
        drv.expression = "A * B"
        
        # Var A
        varA = drv.variables.new()
        varA.name = "A"
        varA.type = 'SINGLE_PROP'
        varA.targets[0].id_type = 'KEY'
        varA.targets[0].id = obj.data.shape_keys
        varA.targets[0].data_path = f'key_blocks["{props.combo_shape_a}"].value'
        
        # Var B
        varB = drv.variables.new()
        varB.name = "B"
        varB.type = 'SINGLE_PROP'
        varB.targets[0].id_type = 'KEY'
        varB.targets[0].id = obj.data.shape_keys
        varB.targets[0].data_path = f'key_blocks["{props.combo_shape_b}"].value'
        
        return {'FINISHED'}

class BSETUP_OT_CreateNamedShape(bpy.types.Operator):
    """Create a new named shape key (and Basis if needed)"""
    bl_idname = "bsetup.create_named_shape"
    bl_label = "Create Shape"
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
             self.report({'ERROR'}, "Select a Mesh Object")
             return {'CANCELLED'}
             
        # Ensure Basis exists
        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis")
            
        # Create new key
        name = props.new_shape_name if props.new_shape_name else "Key"
        key = obj.shape_key_add(name=name, from_mix=False)
        
        # Select it
        obj.active_shape_key_index = obj.data.shape_keys.key_blocks.find(key.name)
        
        # Clear name for next use
        props.new_shape_name = ""
        
        return {'FINISHED'}

class BSETUP_OT_CreateInBetween(bpy.types.Operator):
    """Create a corrective shape that activates at a specific value of the parent shape"""
    bl_idname = "bsetup.create_in_between"
    bl_label = "Create In-Between"
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        obj = context.active_object
        
        if not obj or not obj.data.shape_keys:
             return {'CANCELLED'}
             
        kb = obj.data.shape_keys.key_blocks
        if props.ib_source not in kb:
             self.report({'ERROR'}, "Parent Shape not found")
             return {'CANCELLED'}
             
        parent_name = props.ib_source
        trigger_val = props.ib_value
        
        # Create new shape
        new_name = f"{parent_name}_{trigger_val:.2f}"
        new_shape = obj.shape_key_add(name=new_name, from_mix=False)
        
        # Add Driver
        fcurve = obj.data.shape_keys.driver_add(f'key_blocks["{new_shape.name}"].value')
        drv = fcurve.driver
        drv.type = 'SUM' # Use Mapping Curve
        
        # Var
        var = drv.variables.new()
        var.name = "var"
        var.type = 'SINGLE_PROP'
        var.targets[0].id_type = 'KEY'
        var.targets[0].id = obj.data.shape_keys
        var.targets[0].data_path = f'key_blocks["{parent_name}"].value'
        
        # Curve Points
        # 0 -> 0
        # trigger -> 1
        # 0 or 1 -> 0 (depending on trigger)
        
        # Clean modifiers
        for mod in fcurve.modifiers:
            fcurve.modifiers.remove(mod)
            
        # Logic: Triangle with peak at trigger_val
        # If trigger is 0.5:
        # 0.0 -> 0
        # 0.5 -> 1
        # 1.0 -> 0
        
        fcurve.keyframe_points.insert(0.0, 0.0)
        fcurve.keyframe_points.insert(trigger_val, 1.0)
        
        # We need to clamp it back to 0 at the ends.
        # If trigger < 1, key at 1 is 0.
        if trigger_val < 1.0:
            fcurve.keyframe_points.insert(1.0, 0.0)
        
        # If trigger > 0, key at 0 is 0 (Already added).
        
        # Set interpolation to linear for the "triangle"
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'LINEAR'
            
        return {'FINISHED'}


class BSETUP_OT_SetChannel(bpy.types.Operator):
    """Set the driver data path to a specific channel"""
    bl_idname = "bsetup.set_channel"
    bl_label = "Set Channel"
    
    path: bpy.props.StringProperty()
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        props.driver_data_path = self.path
        return {'FINISHED'}


def flip_name(name):
    """Flip .L/.R or _L/_R naming convention"""
    if name.endswith('.L'): return name[:-2] + '.R'
    if name.endswith('.R'): return name[:-2] + '.L'
    if name.endswith('.l'): return name[:-2] + '.r'
    if name.endswith('.r'): return name[:-2] + '.l'
    
    if name.endswith('_L'): return name[:-2] + '_R'
    if name.endswith('_R'): return name[:-2] + '_L'
    if name.endswith('_l'): return name[:-2] + '_r'
    if name.endswith('_r'): return name[:-2] + '_l'
    
    if '.L.' in name: return name.replace('.L.', '.R.')
    if '.R.' in name: return name.replace('.R.', '.L.')
    if '.l.' in name: return name.replace('.l.', '.r.')
    if '.r.' in name: return name.replace('.r.', '.l.')
    
    if '_L_' in name: return name.replace('_L_', '_R_')
    if '_R_' in name: return name.replace('_R_', '_L_')
    if '_l_' in name: return name.replace('_l_', '_r_')
    if '_r_' in name: return name.replace('_r_', '_l_')
    
    return None  # No flip found


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

        success, msg = mirror_driver_logic(self, context, driver_obj, driven_obj, props.driven_key, flipped_key, self.invert_values)
        
        if not success:
             self.report({'ERROR'}, msg)
             return {'CANCELLED'}
        
        self.report({'INFO'}, f"Mirrored driver to '{flipped_key}'")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def mirror_driver_logic(self, context, driver_obj, driven_obj, source_key_name, target_key_name, invert_values=False):
    """Shared logic for mirroring drivers"""
    key_data = driven_obj.data.shape_keys
    if not key_data or not key_data.animation_data:
        return False, "No driver found on current shape key"
        
    source_path = f'key_blocks["{source_key_name}"].value'
    source_fcurve = None
    for fc in key_data.animation_data.drivers:
        if fc.data_path == source_path:
            source_fcurve = fc
            break
            
    if not source_fcurve:
        return False, f"No driver on {source_key_name}"
    
    # Create new driver on target key
    target_path = f'key_blocks["{target_key_name}"].value'
    
    # Remove existing driver if any
    try:
        key_data.driver_remove(target_path)
    except:
        pass
        
    target_fcurve = key_data.driver_add(target_path)
    target_drv = target_fcurve.driver
    
    # Copy driver settings
    source_drv = source_fcurve.driver
    target_drv.type = source_drv.type
    target_drv.expression = source_drv.expression
    
    # Copy variables
    for src_var in source_drv.variables:
        new_var = target_drv.variables.new()
        new_var.name = src_var.name
        new_var.type = src_var.type
        
        for i, src_tgt in enumerate(src_var.targets):
            tgt = new_var.targets[i]
            tgt.id = src_tgt.id
            
            if src_var.type == 'TRANSFORMS':
                tgt.transform_type = src_tgt.transform_type
                tgt.transform_space = src_tgt.transform_space
                # Flip bone target
                if src_tgt.bone_target:
                    tgt.bone_target = flip_name(src_tgt.bone_target) or src_tgt.bone_target
            else:
                tgt.data_path = src_tgt.data_path
                if src_tgt.bone_target:
                    tgt.bone_target = flip_name(src_tgt.bone_target) or src_tgt.bone_target
    
    # Remove modifiers
    for mod in target_fcurve.modifiers:
        target_fcurve.modifiers.remove(mod)
        
    # Copy keyframes
    # Flip X values if inverted (e.g. Rotate Z -> -Rotate Z)
    for kp in source_fcurve.keyframe_points:
        x_val = -kp.co[0] if invert_values else kp.co[0]
        target_fcurve.keyframe_points.insert(x_val, kp.co[1])
        
    # Set interpolation
    for i, kp in enumerate(target_fcurve.keyframe_points):
        if i < len(source_fcurve.keyframe_points):
            kp.interpolation = source_fcurve.keyframe_points[i].interpolation
            
    target_fcurve.update()
    return True, "Success"


class BSETUP_OT_MirrorShapeAndDriver(bpy.types.Operator):
    """Mirror the Shape Key Geometry (Topology) AND the Driver"""
    bl_idname = "bsetup.mirror_shape_and_driver"
    bl_label = "Mirror Shape & Driver"
    bl_options = {'REGISTER', 'UNDO'}
    
    invert_driver_values: bpy.props.BoolProperty(
        name="Invert Driver Values",
        description="Negate the X-axis values for the driver (e.g. for symmetrized bones)",
        default=False
    )
    

    
    use_topology: bpy.props.BoolProperty(
        name="Topology Mirror",
        description="Use topology based mirroring (for meshes that are not strictly symmetrical in space)",
        default=False
    )
    
    def execute(self, context):
        props = context.scene.maya_shape_keys
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a Mesh Object")
            return {'CANCELLED'}
            
        driver_obj = props.driver_target
        if not driver_obj:
             self.report({'ERROR'}, "No Driver Object Set")
             return {'CANCELLED'}
             
        # Source is active key? Or Driven Key prop?
        # Let's use the Driven Key prop which is usually the 'current' one we are working on.
        source_key_name = props.driven_key
        if not source_key_name or source_key_name not in obj.data.shape_keys.key_blocks:
             # Fallback to active
             if obj.active_shape_key:
                 source_key_name = obj.active_shape_key.name
             else:
                 self.report({'ERROR'}, "No Shape Key selected")
                 return {'CANCELLED'}
        
        target_key_name = flip_name(source_key_name)
        if not target_key_name:
             self.report({'ERROR'}, f"Cannot determine mirror name for '{source_key_name}'")
             return {'CANCELLED'}
             
        # 1. MIRROR GEOMETRY
        # If target exists, we update it. If not, create new.
        
        # To mirror geometry reliably using 'New Shape From Mix', we need to isolate the source shape.
        # Store current values
        key_blocks = obj.data.shape_keys.key_blocks
        stored_values = {kb.name: kb.value for kb in key_blocks}
        
        # Mute all but source
        for kb in key_blocks:
            kb.value = 0.0
            
        key_blocks[source_key_name].value = 1.0
        
        # Create temp mix
        # To make sure we don't mess up, we can use shape_key_add(from_mix=True)
        # But wait, from_mix mixes EVERYTHING visible. 
        # So setting others to 0 is correct.
        
        # Create new key
        obj.shape_key_add(name=target_key_name, from_mix=True)
        # The new key is added at the end, usually active index updates to it? NO.
        new_key_block = key_blocks[len(key_blocks)-1]
        new_key_block.name = target_key_name # Renaming might fail if exists, handled by Blender usually (Name.001)
        
        # If it was duplicate, we might want to replace the old one?
        # If 'target_key_name' already existed, 'new_key_block.name' will be 'target_key_name.001'
        if new_key_block.name != target_key_name:
            # Reconstruct: delete old if exists?
            # User might have done work, safer to NOT delete automatically, but for now let's assume 'overwrite' behavior is desired or manual cleanup.
            # But the user renamed to .001. Let's just Mirror the .001 one.
            pass

        # Mirror it
        obj.active_shape_key_index = key_blocks.find(new_key_block.name)
        bpy.ops.object.shape_key_mirror(use_topology=self.use_topology)
        
        # Reset values
        for k, v in stored_values.items():
            key_blocks[k].value = v
            
        # 2. MIRROR DRIVER
        # Check if driver exists on source
        success, msg = mirror_driver_logic(self, context, driver_obj, obj, source_key_name, new_key_block.name, self.invert_driver_values)
        
        if success:
            self.report({'INFO'}, f"Created & Mirrored '{new_key_block.name}'")
        else:
            self.report({'WARNING'}, f"Mirrored Shape created, but Driver issue: {msg}")
            
        return {'FINISHED'}

class BSETUP_OT_SplitShape(bpy.types.Operator):
    """Split the current shape key into Left and Right sides using an auto-generated Vertex Group mask"""
    bl_idname = "bsetup.split_shape"
    bl_label = "Split Shape L/R"
    bl_options = {'REGISTER', 'UNDO'}
    
    threshold: bpy.props.FloatProperty(
        name="Center Threshold",
        default=0.001,
        description="Threshold for center vertices (X-axis)"
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a Mesh Object")
            return {'CANCELLED'}
        
        if not obj.data.shape_keys or not obj.active_shape_key:
            self.report({'ERROR'}, "No Active Shape Key")
            return {'CANCELLED'}
            
        source_key = obj.active_shape_key
        source_name = source_key.name
        
        # 1. GENERATE MASKS
        # Naming: Split_Mask_L (X >= 0), Split_Mask_R (X < 0)
        # Using standard conventions: +X is Left (Character Left), -X is Right.
        
        group_l_name = "Split_Mask_L"
        group_r_name = "Split_Mask_R"
        
        # Get or Create Groups
        vg_l = obj.vertex_groups.get(group_l_name)
        if not vg_l: vg_l = obj.vertex_groups.new(name=group_l_name)
        
        vg_r = obj.vertex_groups.get(group_r_name)
        if not vg_r: vg_r = obj.vertex_groups.new(name=group_r_name)
        
        # Determine indices
        # We perform this in Object Mode (implied) to access data safely
        mesh = obj.data
        
        # Prepare lists
        indices_l = []
        indices_r = []
        
        # Simple threshold check
        t = self.threshold
        for v in mesh.vertices:
            if v.co.x >= -t: # Include 0 or near 0 in Left
                indices_l.append(v.index)
            else:
                indices_r.append(v.index)
                
        # Clear existing weights in these groups to be safe
        obj.vertex_groups[group_l_name].remove([v.index for v in mesh.vertices])
        obj.vertex_groups[group_r_name].remove([v.index for v in mesh.vertices])
        
        # Assign new weights
        if indices_l: vg_l.add(indices_l, 1.0, 'REPLACE')
        if indices_r: vg_r.add(indices_r, 1.0, 'REPLACE')
        
        # 2. CREATE SPLIT KEYS
        key_blocks = obj.data.shape_keys.key_blocks
        stored_values = {kb.name: kb.value for kb in key_blocks} # Backup
        
        # Reset all to 0
        for kb in key_blocks: kb.value = 0.0
        # Set source to 1.0
        key_blocks[source_name].value = 1.0
        
        # Create Left
        name_l = f"{source_name}_L"
        obj.shape_key_add(name=name_l, from_mix=True)
        kb_l = key_blocks[len(key_blocks)-1]
        kb_l.name = name_l 
        kb_l.vertex_group = group_l_name
        kb_l.value = 0.0 
        
        # Create Right
        name_r = f"{source_name}_R"
        obj.shape_key_add(name=name_r, from_mix=True)
        kb_r = key_blocks[len(key_blocks)-1]
        kb_r.name = name_r
        kb_r.vertex_group = group_r_name
        kb_r.value = 0.0
        
        # Restore original values
        for k, v in stored_values.items():
            key_blocks[k].value = v
            
        self.report({'INFO'}, f"Split '{source_name}' into L/R")
        return {'FINISHED'}


class BSETUP_OT_CreateAsymShape(bpy.types.Operator):
    """Create a new shape key and enable Topology Mirroring for asymmetrical sculpting"""
    bl_idname = "bsetup.create_asym_shape"
    bl_label = "Create Asym Shape"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a Mesh Object")
            return {'CANCELLED'}
        
        # Ensure Basis exists
        if not obj.data.shape_keys:
            obj.shape_key_add(name="Basis")
            
        # Create new key
        props = context.scene.maya_shape_keys
        name = props.asym_shape_name if props.asym_shape_name else "AsymShape"
        
        key = obj.shape_key_add(name=name, from_mix=False)
        key.value = 0.0
        
        # Clear name
        props.asym_shape_name = ""
        
        # Select it
        obj.active_shape_key_index = obj.data.shape_keys.key_blocks.find(key.name)
        
        # Enable Mirroring options
        obj.data.use_mirror_x = True
        obj.data.use_mirror_topology = True
        
        self.report({'INFO'}, "Created Shape & Enabled Topology Mirror")
        return {'FINISHED'}


classes = (
    BSETUP_OT_LoadDriver,
    BSETUP_OT_UpdateDriverValue,
    BSETUP_OT_SnapDriverToValue,
    BSETUP_OT_LoadDriven,
    BSETUP_OT_AddDriverKey,
    BSETUP_OT_AddComboShape,
    BSETUP_OT_CreateNamedShape,
    BSETUP_OT_CreateInBetween,
    BSETUP_OT_SetChannel,
    BSETUP_OT_MirrorDriver,
    BSETUP_OT_MirrorShapeAndDriver,

    BSETUP_OT_SplitShape,
    BSETUP_OT_CreateAsymShape,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
