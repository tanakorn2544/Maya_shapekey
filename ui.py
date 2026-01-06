import bpy

# --- UI List for Shape Keys ---
class BSETUP_UL_ShapeKeyList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Force properties to be inline / standard
            layout.use_property_split = False
            layout.use_property_decorate = False
            
            # Use split to guarantee space: 65% Name, 35% Value/Button
            split = layout.split(factor=0.65)
            
            # --- Left Side: Name ---
            # Check Driver Status
            icon = 'SHAPEKEY_DATA'
            if data.animation_data and data.animation_data.drivers:
                for d in data.animation_data.drivers:
                    if f'key_blocks["{item.name}"].value' in d.data_path:
                        icon = 'DRIVER'
                        break
            
            split.prop(item, "name", text="", icon=icon, emboss=False)
            
            # --- Right Side: Value & Button ---
            row = split.row(align=True)
            row.prop(item, "value", text="")
            
            # Button
            op = row.operator("bsetup.load_driven", text="", icon='DECORATE_KEYFRAME')
            op.key_name = item.name
            
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='SHAPEKEY_DATA')


class BSETUP_PT_DriverTool(bpy.types.Panel):
    bl_label = "Set Driven Key"
    bl_idname = "BSETUP_PT_DriverTool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Maya Shape Keys"
    bl_order = 0

    def draw_header(self, context):
        layout = self.layout
        layout.prop(context.scene.maya_shape_keys, "show_hud", text="", icon='INFO', emboss=False)
        layout.popover(panel="BSETUP_PT_ColorSettings", text="", icon='PREFERENCES')
        
        try:
            from . import preview_collections
            pcoll = preview_collections.get("main")
            if pcoll:
                icon = pcoll.get("MAIN_ICON")
                if icon:
                    layout.label(text="", icon_value=icon.icon_id)
        except:
            pass

    def draw(self, context):
        layout = self.layout
        layout.use_property_split= True
        layout.use_property_decorate = False  # Cleaner
        
        scene = context.scene
        props = scene.maya_shape_keys

        # --- DRIVER SECTION ---
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Driver", icon='DRIVER')
        col.separator()
        
        row = col.row(align=True)
        row.prop(props, "driver_target", text="Object")
        row.operator("bsetup.load_driver", text="", icon='EYEDROPPER')
        if props.driver_target:
            if props.driver_target.type == 'ARMATURE':
                col.prop_search(props, "driver_bone", props.driver_target.data, "bones", text="Bone")
            
            col.separator()
            col.prop(props, "driver_data_path", text="Path") 
            
            # Helper Grid for standard transforms
            sub = col.column(align=True)
            row = sub.row(align=True)
            row.label(text="Quick Channels:")
            
            row = sub.row(align=True)
            row.operator("bsetup.set_channel", text="Loc X").path = "location[0]"
            row.operator("bsetup.set_channel", text="Loc Y").path = "location[1]"
            row.operator("bsetup.set_channel", text="Loc Z").path = "location[2]"
            
            row = sub.row(align=True)
            row.operator("bsetup.set_channel", text="Rot X").path = "rotation_euler[0]"
            row.operator("bsetup.set_channel", text="Rot Y").path = "rotation_euler[1]"
            row.operator("bsetup.set_channel", text="Rot Z").path = "rotation_euler[2]"
            
            row = sub.row(align=True)
            row.operator("bsetup.set_channel", text="Scl X").path = "scale[0]"
            row.operator("bsetup.set_channel", text="Scl Y").path = "scale[1]"
            row.operator("bsetup.set_channel", text="Scl Z").path = "scale[2]"

            col.separator()
            row = col.row(align=True)
            row.prop(props, "driver_value", text="Current Val")
            row.operator("bsetup.update_driver_val", text="", icon='FILE_REFRESH')
            row.operator("bsetup.snap_driver_val", text="", icon='IMPORT')


        # --- DRIVEN SECTION ---
        layout.separator()
        box = layout.box()
        col = box.column(align=True)
        
        row = col.row(align=True)
        row.label(text="Driven", icon='SHAPEKEY_DATA')
        row.prop(props, "driven_type", expand=True)
        
        col.separator()
        
        col.prop(props, "driven_object", text="Object")

        if props.driven_type == 'KEY':
            if props.driven_object:
                if props.driven_object.data and hasattr(props.driven_object.data, "shape_keys") and props.driven_object.data.shape_keys:
                     col.prop_search(props, "driven_key", props.driven_object.data.shape_keys, "key_blocks", text="Shape Key")
                else:
                    col.label(text="No Shape Keys found", icon='ERROR')
                
                col.prop(props, "driven_value", text="Value")
                
        elif props.driven_type == 'POSE':
             col.label(text="Include Channels:", icon='CON_TRANSFORM')
             row = col.row(align=True)
             row.prop(props, "drive_location", toggle=True, text="Loc")
             row.prop(props, "drive_rotation", toggle=True, text="Rot")
             row.prop(props, "drive_scale", toggle=True, text="Scale")
             
             col.label(text="Select Bones to Drive", icon='BONE_DATA')
             
             row = col.row()
             row.operator("bsetup.remove_pose_driver", text="Remove", icon='X')
             row.operator("bsetup.mirror_pose_driver", text="Mirror", icon='MOD_MIRROR')

        # --- ACTION SECTION ---
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.4
        row.operator("bsetup.add_driver_key", text="Key Driver", icon='KEY_HLT')
        row.operator("bsetup.mirror_driver", text="Mirror", icon='MOD_MIRROR')
        
        layout.separator()
        row = layout.row()
        row.prop(props, "driver_interpolation", expand=True)


class BSETUP_PT_ShapeEditor(bpy.types.Panel):
    bl_label = "Shape Editor"
    bl_idname = "BSETUP_PT_ShapeEditor"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Maya Shape Keys"
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            layout.label(text="Select a Mesh Object", icon='INFO')
            return
            
        props = context.scene.maya_shape_keys
        
        # --- LIST VIEW ---
        if obj.data.shape_keys:
            rows = 5
            row = layout.row()
            row.template_list("BSETUP_UL_ShapeKeyList", "", obj.data.shape_keys, "key_blocks", obj, "active_shape_key_index", rows=rows)
        else:
            layout.box().label(text="No Shape Keys")
            
        # --- TOOLS ---
        layout.separator()
        
        # New Shape
        box = layout.box()
        box.use_property_split = True # Apply locally
        col = box.column(align=True)
        col.label(text="Create New", icon='ADD')
        row = col.row(align=True)
        row.prop(props, "new_shape_name", text="")
        row.operator("bsetup.create_named_shape", text="Create")
        
        col.separator()
        col.operator("bsetup.mirror_shape_and_driver", text="Mirror Shape & Driver", icon='MOD_MIRROR')
        
        # Asymmetry
        box = layout.box()
        box.use_property_split = True
        col = box.column(align=True)
        col.label(text="Asymmetry / Split", icon='MESH_DATA')
        row = col.row(align=True)
        row.prop(props, "asym_shape_name", text="")
        row.operator("bsetup.create_asym_shape", text="Create Asym Shape", icon='ADD')
        col.operator("bsetup.split_shape", text="Split Active Shape L/R")
        
        # Combo
        box = layout.box()
        box.use_property_split = True # Apply locally
        col = box.column(align=True)
        col.label(text="Combo / Corrective", icon='DRIVER')
        
        if obj.data.shape_keys:
             col.prop_search(props, "combo_shape_a", obj.data.shape_keys, "key_blocks", text="Shape A")
             col.prop_search(props, "combo_shape_b", obj.data.shape_keys, "key_blocks", text="Shape B")
             col.separator()
             col.prop(props, "combo_name", text="Name")
             col.operator("bsetup.add_combo_shape", text="Create Combo")
        else:
            col.label(text="Need Shape Keys", icon='INFO')

        # In-Between
        box = layout.box()
        box.use_property_split = True # Apply locally
        col = box.column(align=True)
        col.label(text="In-Between", icon='GRAPH')
        
        if obj.data.shape_keys:
             col.prop_search(props, "ib_source", obj.data.shape_keys, "key_blocks", text="Parent")
             col.prop(props, "ib_value", text="Trigger At")
             col.operator("bsetup.create_in_between", text="Create")
        else:
            col.label(text="Need Shape Keys", icon='INFO')



class BSETUP_PT_ColorSettings(bpy.types.Panel):
    bl_label = "Highlight Colors"
    bl_idname = "BSETUP_PT_ColorSettings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        props = context.scene.maya_shape_keys
        layout.label(text="Driver Highlight")
        layout.prop(props, "highlight_color_driver", text="")
        layout.separator()
        layout.label(text="Driven Highlight")
        layout.prop(props, "highlight_color_driven", text="")

classes = (
    BSETUP_UL_ShapeKeyList,
    BSETUP_PT_DriverTool,
    BSETUP_PT_ShapeEditor,
    BSETUP_PT_ColorSettings,
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
