import bpy
from .utils import flip_name, mirror_shape_driver_logic

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
        create_l = False
        if not vg_l: 
            vg_l = obj.vertex_groups.new(name=group_l_name)
            create_l = True
        
        vg_r = obj.vertex_groups.get(group_r_name)
        create_r = False
        if not vg_r: 
            vg_r = obj.vertex_groups.new(name=group_r_name)
            create_r = True
        
        # Only calculate if we created a new group (presumably empty)
        if create_l or create_r:
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
                    if create_l: indices_l.append(v.index)
                else:
                    if create_r: indices_r.append(v.index)
                    
            # Assign new weights
            if create_l and indices_l: vg_l.add(indices_l, 1.0, 'REPLACE')
            if create_r and indices_r: vg_r.add(indices_r, 1.0, 'REPLACE')
        
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
        success, msg = mirror_shape_driver_logic(self, context, driver_obj, obj, source_key_name, new_key_block.name, self.invert_driver_values)
        
        if success:
            self.report({'INFO'}, f"Created & Mirrored '{new_key_block.name}'")
        else:
            self.report({'WARNING'}, f"Mirrored Shape created, but Driver issue: {msg}")
            
        return {'FINISHED'}
