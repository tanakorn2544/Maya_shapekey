bl_info = {
    "name": "Maya-Style Shape Key System",
    "author": "Korn Sensei",
    "version": (2, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Maya Shape Keys",
    "description": "Enhanced Shape Key system with Maya-like Set Driven Key functionality",
    "warning": "",
    "doc_url": "",
    "category": "Animation",
}

# Reload handling
if "bpy" in locals():
    import importlib    
    if "properties" in locals():
        importlib.reload(properties)
    if "operators" in locals():
        importlib.reload(operators)
        importlib.reload(operators.utils)
        importlib.reload(operators.driver_ops)
        importlib.reload(operators.pose_ops)
        importlib.reload(operators.driver_ops)
        importlib.reload(operators.pose_ops)
        importlib.reload(operators.shape_ops)
        importlib.reload(operators.update_ops)
    if "ui" in locals():
        importlib.reload(ui)
    if "hud" in locals():
        # Clean up existing handler before reload to avoid duplicates
        try:
            hud.remove_handler()
        except:
            pass
        importlib.reload(hud)
else:
    from . import properties
    from . import operators
    from . import ui
    from . import hud

import bpy
import bpy.utils.previews
import os

preview_collections = {}

# --- ADDON PREFERENCES ---
class BSETUP_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    # State Props
    latest_version_str: bpy.props.StringProperty(
        name="Latest Version",
        default="Unknown"
    )
    
    download_url: bpy.props.StringProperty(
        name="Download URL",
        default=""
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Header Info
        box = layout.box()
        row = box.row()
        row.label(text="Maya-Style Shape Key System", icon="SHAPEKEY_DATA")
        row.label(text=f"Current Version: {bl_info['version']}")
        
        # Check Update Section
        row = box.row()
        row.scale_y = 1.2
        row.operator("bsetup.check_for_updates", icon="FILE_REFRESH")
        
        # If we have a version string and it differs? 
        # For simplicity, we just show what we found.
        if self.latest_version_str != "Unknown":
            box.label(text=f"Latest Release: {self.latest_version_str}")
            
            if self.download_url:
                row = box.row()
                row.scale_y = 1.5
                row.alert = True 
                row.operator("bsetup.update_addon", text="Install Update (Restart Required)", icon="IMPORT")

def register():
    bpy.utils.register_class(BSETUP_AddonPreferences) # Register Prefs First
    properties.register()
    operators.register()
    ui.register()
    
    # Load Icons
    pcoll = bpy.utils.previews.new()
    my_icons_dir = os.path.join(os.path.dirname(__file__), "Icons")
    
    # Load the specific file
    # We map it to a shorter name "MAIN_ICON" for easy access
    try:
        pcoll.load("MAIN_ICON", os.path.join(my_icons_dir, "f30c933f-c41f-4a8b-8848-007cecc58b39.png"), 'IMAGE')
    except Exception as e:
        print(f"BSETUP Warning: Could not load icon: {e}")
        
    preview_collections["main"] = pcoll

def unregister():
    # Remove icons first
    hud.remove_handler()
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    
    ui.unregister()
    operators.unregister()
    operators.unregister()
    properties.unregister()
    
    bpy.utils.unregister_class(BSETUP_AddonPreferences)

if __name__ == "__main__":
    register()
